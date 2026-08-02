// Minimal Flutter reference client for Aura (thin — spec §16).
// Authenticates, joins the avatar session, shows the talking-avatar video,
// live transcript + state, a mic toggle, a text field, and an interrupt button.
//
// Configure GATEWAY_URL / USER_ID for your deployment.
import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart';

import 'aura_client.dart';

const gatewayUrl = String.fromEnvironment('AURA_GATEWAY',
    defaultValue: 'http://localhost:8080');
const userId = String.fromEnvironment('AURA_USER', defaultValue: 'demo-user');

void main() => runApp(const AuraApp());

class AuraApp extends StatelessWidget {
  const AuraApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Aura',
        theme: ThemeData.dark(useMaterial3: true),
        home: const AuraScreen(),
      );
}

class AuraScreen extends StatefulWidget {
  const AuraScreen({super.key});
  @override
  State<AuraScreen> createState() => _AuraScreenState();
}

class _AuraScreenState extends State<AuraScreen> {
  final _client = AuraClient(gatewayUrl: gatewayUrl, userId: userId);
  final _textCtrl = TextEditingController();
  VideoTrack? _track;
  AuraState _state = AuraState.idle;
  String _transcript = '';
  bool _mic = false;

  @override
  void initState() {
    super.initState();
    _client.stateStream.listen((s) => setState(() => _state = s));
    _client.transcriptStream
        .listen((t) => setState(() => _transcript = t.text));
    _client.videoTrackStream.listen((v) => setState(() => _track = v));
    _client.connect();
  }

  @override
  void dispose() {
    _client.disconnect();
    _textCtrl.dispose();
    super.dispose();
  }

  Future<void> _toggleMic() async {
    _mic ? await _client.disableMic() : await _client.enableMic();
    setState(() => _mic = !_mic);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Aura · ${_state.name}')),
      body: Column(children: [
        Expanded(
          child: Container(
            color: Colors.black,
            child: _track != null
                ? VideoTrackRenderer(_track!)
                : const Center(child: Text('Connecting…')),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Text(_transcript, style: const TextStyle(color: Colors.amber)),
        ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(children: [
            IconButton(
              icon: Icon(_mic ? Icons.mic : Icons.mic_off),
              onPressed: _toggleMic,
            ),
            Expanded(
              child: TextField(
                controller: _textCtrl,
                decoration: const InputDecoration(hintText: 'Type to Aura…'),
                onSubmitted: (t) {
                  _client.sendText(t);
                  _textCtrl.clear();
                },
              ),
            ),
            IconButton(
              icon: const Icon(Icons.stop_circle),
              tooltip: 'Interrupt',
              onPressed: _client.interrupt,
            ),
          ]),
        ),
      ]),
    );
  }
}
