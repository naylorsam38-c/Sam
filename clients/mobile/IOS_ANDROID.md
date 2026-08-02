# Native iOS & Android integration (thin client)

Both platforms use the official LiveKit SDKs and follow the **same 6-step
contract** as the browser and Flutter clients. The backend is identical; only the
client language differs.

The client must only: (1) authenticate, (2) join the avatar session, (3) send mic
audio or typed text, (4) receive avatar audio+video, (5) receive transcript +
state events, (6) send controls (interrupt/mute/set_avatar/end).

## Shared flow
1. `POST {GATEWAY}/v1/session` with header `x-user-id` → `{token, room,
   transport_url}`.
2. Connect to LiveKit with `transport_url` + `token`.
3. Publish the microphone track.
4. Subscribe to the remote **video** track (the avatar) + its audio.
5. Parse JSON **data-channel** messages: `{type, session_id, turn_id, data, ts}`
   where `type ∈ {state, partial_transcript, final_transcript, response_text,
   timing, drift, quality, interrupted, error}`.
6. Send controls as JSON on the data channel: `{ "type": "interrupt" }`,
   `{ "type": "text_input", "text": "…" }`, `{ "type": "set_avatar", "avatar":
   "nova" }`, `mute`/`unmute`/`end_session`.

## iOS (Swift) — LiveKit Swift SDK
```swift
// Package: https://github.com/livekit/client-sdk-swift  (Apache-2.0)
let resp = try await URLSession.shared.data(for: sessionRequest) // POST /v1/session
let (token, url) = decode(resp)
let room = Room()
room.add(delegate: self)
try await room.connect(url, token)
try await room.localParticipant.setMicrophone(enabled: true)

// RoomDelegate:
func room(_ r: Room, participant: RemoteParticipant, didSubscribe track: Track) {
  if let v = track as? VideoTrack { attach(v, to: avatarView) }
}
func room(_ r: Room, didReceiveData data: Data, participant: RemoteParticipant?) {
  let env = try? JSONDecoder().decode(Envelope.self, from: data)  // state/transcript
}
// control:
try await room.localParticipant.publishData(
  Data(#"{"type":"interrupt"}"#.utf8), reliability: .reliable)
```
Info.plist: `NSMicrophoneUsageDescription`. Handle app background/lock: mute mic +
pause publish; end the session if not resumed (see FAILURE_HANDLING).

## Android (Kotlin) — LiveKit Android SDK
```kotlin
// Dependency: io.livekit:livekit-android  (Apache-2.0)
val (token, url) = api.createSession(userId)   // POST /v1/session
val room = LiveKit.create(appContext)
room.connect(url, token)
room.localParticipant.setMicrophoneEnabled(true)

room.events.collect { e ->
  when (e) {
    is RoomEvent.TrackSubscribed ->
      (e.track as? VideoTrack)?.let { attachToRenderer(it) }
    is RoomEvent.DataReceived ->
      parseEnvelope(e.data)      // state / transcript / response
    else -> {}
  }
}
// control:
room.localParticipant.publishData("""{"type":"interrupt"}""".toByteArray(),
  DataPublishReliability.RELIABLE)
```
Manifest: `RECORD_AUDIO` permission. Handle lifecycle (onStop → mute/pause). Only
the gateway + LiveKit media endpoints are public; never embed model/Command Desk
URLs in the app.
