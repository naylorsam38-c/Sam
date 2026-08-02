# Aura Flutter reference client (thin)

A minimal, reusable client. It only: authenticates, joins the avatar session,
sends mic audio / typed text, renders the avatar video, and surfaces state +
transcript events. All intelligence and rendering stay on the server.

## Run
```bash
flutter pub get
flutter run \
  --dart-define=AURA_GATEWAY=https://your-gateway \
  --dart-define=AURA_USER=demo-user
```
Grant microphone permission when prompted. `lib/aura_client.dart` is the reusable
piece (Streams for state/transcript/response/video + connect/enableMic/sendText/
interrupt/mute); `lib/main.dart` is a tiny demo UI over it.

Contract: `POST {AURA_GATEWAY}/v1/session` with header `x-user-id` → `{token,
room, transport_url}` → join LiveKit → publish mic, receive video + data-channel
events, send controls. Same backend serves web, iOS and Android.
