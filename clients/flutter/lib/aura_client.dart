/// AuraClient — thin Flutter/Dart reference client for the Aura avatar service.
///
/// Framework-agnostic (no widgets here). Wraps the `livekit_client` package and
/// the Aura gateway HTTP contract. The client only:
///   (a) authenticates + gets a token   -> POST GATEWAY/v1/session (x-user-id)
///   (b) joins the avatar room           -> Room.connect(transportUrl, token)
///   (c) sends mic audio OR typed text   -> publish mic / text_input control
///   (d) receives avatar audio+video     -> exposes the remote VideoTrack
///   (e) receives transcript + state     -> parses data-channel Envelope JSON
///   (f) sends controls                  -> localParticipant.publishData(JSON)
///
/// Wire contract (matches aura/protocol.py):
///   Inbound  : Envelope {type, session_id, turn_id, data, ts}
///              type in {state, partial_transcript, final_transcript,
///                       response_text, timing, drift, quality,
///                       interrupted, error}
///   Outbound : {type, ...} where type in {interrupt, mute, unmute,
///                       set_avatar, text_input, end_session}
library aura_client;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:livekit_client/livekit_client.dart';

/// Deterministic session states pushed by the server (mirror of protocol.State).
enum AuraState {
  idle,
  listening,
  userSpeaking,
  thinking,
  startingSpeech,
  speaking,
  interrupted,
  recovering,
  error,
  unknown;

  static AuraState parse(String? raw) {
    switch (raw) {
      case 'IDLE':
        return AuraState.idle;
      case 'LISTENING':
        return AuraState.listening;
      case 'USER_SPEAKING':
        return AuraState.userSpeaking;
      case 'THINKING':
        return AuraState.thinking;
      case 'STARTING_SPEECH':
        return AuraState.startingSpeech;
      case 'SPEAKING':
        return AuraState.speaking;
      case 'INTERRUPTED':
        return AuraState.interrupted;
      case 'RECOVERING':
        return AuraState.recovering;
      case 'ERROR':
        return AuraState.error;
      default:
        return AuraState.unknown;
    }
  }

  /// The wire label (e.g. "USER_SPEAKING"), useful for UI.
  String get label {
    switch (this) {
      case AuraState.userSpeaking:
        return 'USER_SPEAKING';
      case AuraState.startingSpeech:
        return 'STARTING_SPEECH';
      default:
        return name.toUpperCase();
    }
  }
}

/// One transcript line surfaced to the UI.
class TranscriptLine {
  TranscriptLine({
    required this.text,
    required this.isUser,
    required this.isFinal,
  });

  final String text;
  final bool isUser; // true = user speech, false = avatar response
  final bool isFinal; // false = partial (in-progress)
}

/// Decoded data-channel envelope.
class AuraEvent {
  AuraEvent({
    required this.type,
    required this.sessionId,
    this.turnId,
    this.data = const {},
    this.ts = 0,
  });

  final String type;
  final String sessionId;
  final String? turnId;
  final Map<String, dynamic> data;
  final double ts;

  factory AuraEvent.fromJson(Map<String, dynamic> j) => AuraEvent(
        type: j['type'] as String? ?? 'error',
        sessionId: j['session_id'] as String? ?? '',
        turnId: j['turn_id'] as String?,
        data: (j['data'] as Map?)?.cast<String, dynamic>() ?? const {},
        ts: (j['ts'] as num?)?.toDouble() ?? 0,
      );
}

/// The gateway `/v1/session` response.
class _Session {
  _Session(this.token, this.room, this.transportUrl, this.expiresAt);
  final String token;
  final String room;
  final String transportUrl;
  final dynamic expiresAt;
}

/// Thin Aura client. Create once, `connect()`, then drive the UI from the
/// exposed streams and call the control methods.
class AuraClient {
  AuraClient({required this.gatewayUrl, required this.userId})
      : assert(gatewayUrl.length > 0),
        assert(userId.length > 0);

  /// Base URL of the Aura gateway, e.g. `http://localhost:8080`.
  final String gatewayUrl;

  /// App user identity, sent as the `x-user-id` header.
  final String userId;

  // ── Reactive outputs for the UI ──────────────────────────────────────────
  final _stateCtrl = StreamController<AuraState>.broadcast();
  final _transcriptCtrl = StreamController<TranscriptLine>.broadcast();
  final _responseCtrl = StreamController<String>.broadcast();
  final _eventCtrl = StreamController<AuraEvent>.broadcast();
  final _errorCtrl = StreamController<String>.broadcast();
  final _videoTrackCtrl = StreamController<VideoTrack?>.broadcast();

  /// Session state transitions (LISTENING, THINKING, SPEAKING, ...).
  Stream<AuraState> get stateStream => _stateCtrl.stream;

  /// User + avatar transcript lines (partial and final).
  Stream<TranscriptLine> get transcriptStream => _transcriptCtrl.stream;

  /// The text the avatar is about to speak (`response_text`).
  Stream<String> get responseStream => _responseCtrl.stream;

  /// Every decoded envelope (timing/drift/quality live here too).
  Stream<AuraEvent> get eventStream => _eventCtrl.stream;

  /// Error messages (transport or `error` envelopes).
  Stream<String> get errorStream => _errorCtrl.stream;

  /// The remote avatar video track (null while none is subscribed).
  Stream<VideoTrack?> get videoTrackStream => _videoTrackCtrl.stream;

  AuraState _state = AuraState.idle;
  AuraState get state => _state;

  VideoTrack? _videoTrack;
  VideoTrack? get videoTrack => _videoTrack;

  String? _sessionId;
  String? get sessionId => _sessionId;

  // ── LiveKit internals ────────────────────────────────────────────────────
  Room? _room;
  EventsListener<RoomEvent>? _listener;
  LocalAudioTrack? _micTrack;
  bool _muted = false;
  bool get isMuted => _muted;

  Room? get room => _room;

  // ── (a) auth + (b) join ──────────────────────────────────────────────────
  /// Authenticate with the gateway then join the LiveKit avatar room.
  Future<void> connect() async {
    final session = await _authenticate();
    _sessionId = session.room;

    final room = Room();
    _room = room;

    final listener = room.createListener();
    _listener = listener;

    listener
      ..on<TrackSubscribedEvent>(_onTrackSubscribed)
      ..on<TrackUnsubscribedEvent>(_onTrackUnsubscribed)
      ..on<DataReceivedEvent>(_onData)
      ..on<RoomDisconnectedEvent>((e) {
        _emitState(AuraState.idle);
      });

    await room.connect(
      session.transportUrl,
      session.token,
      roomOptions: const RoomOptions(
        adaptiveStream: true,
        dynacast: true,
      ),
    );
  }

  Future<_Session> _authenticate() async {
    final uri = Uri.parse('${_base()}/v1/session');
    final resp = await http.post(
      uri,
      headers: {
        'x-user-id': userId,
        'content-type': 'application/json',
      },
    );
    if (resp.statusCode != 200) {
      throw Exception(
          'session request failed: ${resp.statusCode} ${resp.body}');
    }
    final j = jsonDecode(resp.body) as Map<String, dynamic>;
    final token = j['token'] as String?;
    final transportUrl = j['transport_url'] as String?;
    if (token == null || transportUrl == null) {
      throw Exception('gateway response missing token/transport_url');
    }
    return _Session(
      token,
      j['room'] as String? ?? '',
      transportUrl,
      j['expires_at'],
    );
  }

  String _base() => gatewayUrl.replaceAll(RegExp(r'/+$'), '');

  // ── (d) receive avatar audio + video ─────────────────────────────────────
  void _onTrackSubscribed(TrackSubscribedEvent e) {
    final track = e.track;
    if (track is VideoTrack) {
      _videoTrack = track;
      _videoTrackCtrl.add(track);
    }
    // Audio tracks are auto-played by the LiveKit engine; nothing to do.
  }

  void _onTrackUnsubscribed(TrackUnsubscribedEvent e) {
    if (identical(e.track, _videoTrack)) {
      _videoTrack = null;
      _videoTrackCtrl.add(null);
    }
  }

  // ── (e) receive transcript + state events ────────────────────────────────
  void _onData(DataReceivedEvent e) {
    late final AuraEvent env;
    try {
      final map = jsonDecode(utf8.decode(e.data)) as Map<String, dynamic>;
      env = AuraEvent.fromJson(map);
    } catch (err) {
      _errorCtrl.add('bad data-channel payload: $err');
      return;
    }

    if (env.sessionId.isNotEmpty) _sessionId = env.sessionId;
    _eventCtrl.add(env);

    switch (env.type) {
      case 'state':
        _emitState(AuraState.parse(env.data['state'] as String?));
        break;
      case 'partial_transcript':
        _transcriptCtrl.add(TranscriptLine(
          text: env.data['text'] as String? ?? '',
          isUser: true,
          isFinal: false,
        ));
        break;
      case 'final_transcript':
        _transcriptCtrl.add(TranscriptLine(
          text: env.data['text'] as String? ?? '',
          isUser: true,
          isFinal: true,
        ));
        break;
      case 'response_text':
        final text = env.data['text'] as String? ?? '';
        _responseCtrl.add(text);
        _transcriptCtrl.add(TranscriptLine(
          text: text,
          isUser: false,
          isFinal: true,
        ));
        break;
      case 'interrupted':
        _emitState(AuraState.interrupted);
        break;
      case 'error':
        _errorCtrl.add(
            (env.data['message'] ?? env.data['error'] ?? 'avatar error')
                .toString());
        break;
      default:
        // timing / drift / quality flow through eventStream only.
        break;
    }
  }

  void _emitState(AuraState s) {
    _state = s;
    _stateCtrl.add(s);
  }

  // ── (c) send microphone audio ────────────────────────────────────────────
  /// Capture and publish the microphone.
  Future<void> enableMic() async {
    _requireRoom();
    if (_micTrack == null) {
      _micTrack = await LocalAudioTrack.create();
      await _room!.localParticipant!.publishAudioTrack(_micTrack!);
    }
    await _micTrack!.unmute();
    _muted = false;
    _sendControl({'type': 'unmute'});
  }

  /// Stop publishing the microphone entirely.
  Future<void> disableMic() async {
    final track = _micTrack;
    if (track != null) {
      await _room?.localParticipant?.unpublishTrack(track.sid);
      await track.stop();
      _micTrack = null;
    }
  }

  // ── (c) send typed text ──────────────────────────────────────────────────
  /// Send a typed utterance instead of speaking.
  void sendText(String text) {
    if (text.isEmpty) return;
    _sendControl({
      'type': 'text_input',
      'data': {'text': text},
    });
  }

  // ── (f) controls ─────────────────────────────────────────────────────────
  /// Barge-in: stop the avatar speaking now.
  void interrupt() => _sendControl({'type': 'interrupt'});

  /// Mute the mic locally and notify the backend.
  Future<void> mute() async {
    await _micTrack?.mute();
    _muted = true;
    _sendControl({'type': 'mute'});
  }

  /// Unmute the mic locally and notify the backend.
  Future<void> unmute() async {
    await _micTrack?.unmute();
    _muted = false;
    _sendControl({'type': 'unmute'});
  }

  /// Switch the avatar persona (nova | halo | gaia).
  void setAvatar(String avatar) => _sendControl({
        'type': 'set_avatar',
        'data': {'avatar': avatar},
      });

  /// End the session cleanly and leave the room.
  Future<void> endSession() async {
    try {
      _sendControl({'type': 'end_session'});
    } catch (_) {
      /* best effort */
    }
    await disconnect();
  }

  /// Disconnect from LiveKit without sending end_session.
  Future<void> disconnect() async {
    await disableMic();
    await _listener?.dispose();
    _listener = null;
    await _room?.disconnect();
    _room = null;
    _videoTrack = null;
    _videoTrackCtrl.add(null);
  }

  /// Release all resources and close the streams.
  Future<void> dispose() async {
    await disconnect();
    await _stateCtrl.close();
    await _transcriptCtrl.close();
    await _responseCtrl.close();
    await _eventCtrl.close();
    await _errorCtrl.close();
    await _videoTrackCtrl.close();
  }

  // ── internals ────────────────────────────────────────────────────────────
  void _sendControl(Map<String, dynamic> obj) {
    _requireRoom();
    final bytes = utf8.encode(jsonEncode(obj));
    // Reliable delivery — controls must not be dropped.
    _room!.localParticipant!.publishData(bytes, reliable: true);
  }

  void _requireRoom() {
    if (_room == null || _room!.localParticipant == null) {
      throw StateError('not connected — call connect() first');
    }
  }
}
