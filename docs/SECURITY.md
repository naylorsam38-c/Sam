# Security Controls (spec §17–§18)

- **Short-lived signed tokens.** Gateway issues HMAC-signed, TTL-bounded tokens
  scoped to one room + one user (`aura/gateway/auth.py`). No long-lived secrets on
  the client.
- **No exposed internals.** Only the gateway (and the LiveKit media port) are
  public. Model/render/STT/TTS workers and the Command Desk endpoint stay on the
  internal network. Terminate TLS in front of the gateway; media is DTLS-SRTP.
- **Per-user session isolation.** `SessionRegistry` binds a room to its owner; a
  different user cannot join another user's room (tested). One active session per
  user; global cap `AURA_MAX_SESSIONS` (default 1).
- **Rate limiting.** Token-bucket per user/IP on session creation.
- **Upload validation.** Avatar images checked for type, byte size (≤12 MB),
  dimensions (≤4096), and decodability (`gateway/security.validate_upload`).
- **Temp-file & media hygiene.** Per-turn audio/frame temp files are cleaned on a
  timer (`cleanup_temp`); frames/audio are not persisted beyond the turn.
- **AuthN/AuthZ & audit.** App authenticates the user (x-user-id → your IdP in
  prod); every session issue/verify/interrupt is a structured audit log line.
- **Consent.** Avatar identity ownership + consent recorded per source image
  (spec §21) before an avatar may be used.
