/*
 * AuraClient — thin browser reference client for the Aura avatar service.
 *
 * Framework-agnostic vanilla JS. Depends only on the LiveKit web SDK being
 * loaded on the page (window.LivekitClient / window.LiveKitClient), e.g.:
 *   <script src="https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js"></script>
 *
 * Responsibilities (and nothing more — the backend does the real work):
 *   (a) authenticate + get a token   -> POST GATEWAY/v1/session (x-user-id header)
 *   (b) join the avatar room         -> Room.connect(transport_url, token)
 *   (c) send mic audio OR typed text -> publish mic track / text_input control
 *   (d) receive avatar audio+video   -> attach remote tracks
 *   (e) receive transcript + state   -> parse data-channel Envelope JSON
 *   (f) send controls                -> publishData JSON control messages
 *
 * Wire contract (matches aura/protocol.py):
 *   Inbound events  : Envelope {type, session_id, turn_id, data, ts}
 *                     type in {state, partial_transcript, final_transcript,
 *                              response_text, timing, drift, quality,
 *                              interrupted, error}
 *   Outbound control: {type, ...} where type in {interrupt, mute, unmute,
 *                              set_avatar, text_input, end_session}
 *                     text_input carries {text}; set_avatar carries {avatar}
 */
(function (global) {
  "use strict";

  // The UMD bundle exposes itself as LivekitClient (older builds: LiveKitClient).
  function lk() {
    const L = global.LivekitClient || global.LiveKitClient;
    if (!L) {
      throw new Error(
        "LiveKit web SDK not found on window. Load livekit-client.umd.min.js first."
      );
    }
    return L;
  }

  const noop = function () {};

  class AuraClient {
    /**
     * @param {Object} opts
     * @param {string} opts.gatewayUrl  Base URL of the Aura gateway, e.g. http://localhost:8080
     * @param {string} opts.userId      App user identity (sent as x-user-id).
     * @param {Object} [opts.callbacks] onState/onPartial/onFinal/onResponse/onError/...
     */
    constructor(opts) {
      opts = opts || {};
      if (!opts.gatewayUrl) throw new Error("gatewayUrl required");
      if (!opts.userId) throw new Error("userId required");

      this.gatewayUrl = opts.gatewayUrl.replace(/\/+$/, "");
      this.userId = opts.userId;

      // Session data returned by the gateway.
      this.token = null;
      this.room = null; // LiveKit room name
      this.transportUrl = null;
      this.expiresAt = null;
      this.sessionId = null; // learned from inbound envelopes
      this.state = "IDLE";

      // LiveKit objects.
      this._room = null;
      this._micTrack = null;
      this._muted = false;

      // Callbacks (all optional).
      const cb = opts.callbacks || {};
      this.onState = cb.onState || noop; // (stateString, envelope)
      this.onPartial = cb.onPartial || noop; // (text, envelope)
      this.onFinal = cb.onFinal || noop; // (text, envelope)
      this.onResponse = cb.onResponse || noop; // (text, envelope)  avatar reply text
      this.onError = cb.onError || noop; // (Error|string, envelope?)
      this.onEvent = cb.onEvent || noop; // (envelope) — raw, every event
      this.onVideoTrack = cb.onVideoTrack || noop; // (HTMLMediaElement)
      this.onAudioTrack = cb.onAudioTrack || noop; // (HTMLMediaElement)
      this.onConnected = cb.onConnected || noop; // ()
      this.onDisconnected = cb.onDisconnected || noop; // (reason)
    }

    // ── (a) auth + (b) join ──────────────────────────────────────────────
    /**
     * Authenticate with the gateway and join the LiveKit avatar room.
     * @returns {Promise<void>}
     */
    async connect() {
      await this._authenticate();

      const L = lk();
      const room = new L.Room({
        adaptiveStream: true,
        dynacast: true,
      });
      this._room = room;

      room.on(L.RoomEvent.TrackSubscribed, (track, pub, participant) =>
        this._onTrackSubscribed(track, pub, participant)
      );
      room.on(L.RoomEvent.DataReceived, (payload, participant, kind, topic) =>
        this._onData(payload, participant, topic)
      );
      room.on(L.RoomEvent.Disconnected, (reason) => {
        this.onDisconnected(reason);
      });

      await room.connect(this.transportUrl, this.token);
      this.onConnected();
    }

    async _authenticate() {
      const resp = await fetch(this.gatewayUrl + "/v1/session", {
        method: "POST",
        headers: {
          "x-user-id": this.userId,
          "content-type": "application/json",
        },
      });
      if (!resp.ok) {
        const body = await resp.text().catch(() => "");
        throw new Error(
          "session request failed: " + resp.status + " " + body
        );
      }
      const data = await resp.json();
      this.token = data.token;
      this.room = data.room;
      this.transportUrl = data.transport_url;
      this.expiresAt = data.expires_at;
      if (!this.token || !this.transportUrl) {
        throw new Error("gateway response missing token/transport_url");
      }
      return data;
    }

    // ── (d) receive avatar audio + video ─────────────────────────────────
    _onTrackSubscribed(track, _pub, _participant) {
      const L = lk();
      if (track.kind === L.Track.Kind.Video) {
        const el = track.attach();
        el.autoplay = true;
        el.playsInline = true;
        this.onVideoTrack(el);
      } else if (track.kind === L.Track.Kind.Audio) {
        const el = track.attach();
        el.autoplay = true;
        this.onAudioTrack(el);
      }
    }

    // ── (e) receive transcript + state events ────────────────────────────
    _onData(payload, _participant, _topic) {
      let env;
      try {
        const text = new TextDecoder().decode(payload);
        env = JSON.parse(text);
      } catch (e) {
        this.onError(new Error("bad data-channel payload: " + e.message));
        return;
      }
      if (env && env.session_id) this.sessionId = env.session_id;
      this.onEvent(env);

      const d = env.data || {};
      switch (env.type) {
        case "state":
          this.state = d.state || env.state || this.state;
          this.onState(this.state, env);
          break;
        case "partial_transcript":
          this.onPartial(d.text || "", env);
          break;
        case "final_transcript":
          this.onFinal(d.text || "", env);
          break;
        case "response_text":
          this.onResponse(d.text || "", env);
          break;
        case "interrupted":
          this.onState("INTERRUPTED", env);
          break;
        case "error":
          this.onError(d.message || d.error || "avatar error", env);
          break;
        // timing / drift / quality are surfaced through onEvent only.
        default:
          break;
      }
    }

    // ── (c) send microphone audio ────────────────────────────────────────
    /**
     * Capture the microphone and publish it to the room.
     * @returns {Promise<void>}
     */
    async enableMic() {
      this._requireRoom();
      const L = lk();
      if (!this._micTrack) {
        this._micTrack = await L.createLocalAudioTrack({
          echoCancellation: true,   // remove the avatar's own audio from the mic
          noiseSuppression: true,
          autoGainControl: true,
        });
        await this._room.localParticipant.publishTrack(this._micTrack);
      }
      await this._micTrack.unmute();
      this._muted = false;
      this._sendControl({ type: "unmute" });
    }

    /** Stop publishing the mic entirely. */
    async disableMic() {
      if (this._micTrack) {
        this._room.localParticipant.unpublishTrack(this._micTrack);
        this._micTrack.stop();
        this._micTrack = null;
      }
    }

    // ── (c) send typed text ──────────────────────────────────────────────
    /** Send a typed utterance instead of speaking. */
    sendText(text) {
      if (!text) return;
      this._sendControl({ type: "text_input", data: { text: String(text) } });
    }

    // ── (f) controls ─────────────────────────────────────────────────────
    /** Barge-in: stop the avatar speaking now. */
    interrupt() {
      this._sendControl({ type: "interrupt" });
    }

    /** Mute the mic locally and tell the backend. */
    async mute() {
      if (this._micTrack) await this._micTrack.mute();
      this._muted = true;
      this._sendControl({ type: "mute" });
    }

    /** Unmute the mic locally and tell the backend. */
    async unmute() {
      if (this._micTrack) await this._micTrack.unmute();
      this._muted = false;
      this._sendControl({ type: "unmute" });
    }

    /** Switch the avatar persona (nova | halo | gaia). */
    setAvatar(avatar) {
      this._sendControl({ type: "set_avatar", data: { avatar: String(avatar) } });
    }

    /** End the session cleanly and leave the room. */
    async endSession() {
      try {
        this._sendControl({ type: "end_session" });
      } catch (_) {
        /* best effort */
      }
      await this.disconnect();
    }

    /** Disconnect from LiveKit without sending end_session. */
    async disconnect() {
      await this.disableMic();
      if (this._room) {
        await this._room.disconnect();
        this._room = null;
      }
    }

    get muted() {
      return this._muted;
    }

    // ── internals ────────────────────────────────────────────────────────
    _sendControl(obj) {
      this._requireRoom();
      const L = lk();
      const payload = new TextEncoder().encode(JSON.stringify(obj));
      // Reliable delivery for controls (they must not be dropped).
      this._room.localParticipant.publishData(payload, {
        reliable: true,
      });
      // Back-compat with older SDKs that used a positional kind arg.
      void L;
    }

    _requireRoom() {
      if (!this._room) throw new Error("not connected — call connect() first");
    }
  }

  // Export for browser globals and (optionally) CommonJS.
  global.AuraClient = AuraClient;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = AuraClient;
  }
})(typeof window !== "undefined" ? window : this);
