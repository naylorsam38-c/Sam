# Walkthrough — Youtarr for Video streaming

Repo https://github.com/DialmasterOrg/Youtarr @ `636a2b0d5aff157621a7c0ecddc6a9e1a8853acb`  
Started 2026-09-19T05:51:34, finished 2026-09-19T05:56:07

## Boot: **BOOTED**

- recipe: docker-compose.yml
- url: http://127.0.0.1:3087/
- detail: UI answered at http://127.0.0.1:3087/ (youtarr published 3087->3011)
- notes: ['copied .env.example -> .env']

## Getting in: **STUCK**

- landing: `http://127.0.0.1:3087/setup` → screenshots/01_landing.png
- filled 4 fields → http://127.0.0.1:3087/setup → screenshots/02_gate_step_1.png
- filled 4 fields → http://127.0.0.1:3087/setup → screenshots/03_gate_step_2.png
- filled 4 fields → http://127.0.0.1:3087/setup → screenshots/04_gate_step_3.png
- filled 4 fields → http://127.0.0.1:3087/setup → screenshots/05_gate_step_4.png
- filled 4 fields → http://127.0.0.1:3087/setup → screenshots/06_gate_step_5.png
- filled 4 fields → http://127.0.0.1:3087/setup → screenshots/07_gate_step_6.png
- after: `http://127.0.0.1:3087/setup` → screenshots/08_after_gate.png

## Capabilities

| Capability | Verdict | Evidence | Screenshot |
|---|---|---|---|
| Upload | **ABSENT** |  |  |
| transcoding | **ABSENT** |  |  |
| channels | **ABSENT** |  |  |
| subscriptions | **ABSENT** |  |  |
| recommendations | **ABSENT** |  |  |
| search | **ABSENT** |  |  |
| playlists | **ABSENT** |  |  |
| comments | **ABSENT** |  |  |
| likes | **ABSENT** |  |  |
| live streaming | **ABSENT** |  |  |
| captions | **ABSENT** |  |  |
| analytics | **ABSENT** |  |  |
| monetisation | **ABSENT** |  |  |

## Summary: booted=True gate=STUCK reached 0/13, seen 0, absent 13

Gaps (to be filled by capability services): Upload, transcoding, channels, subscriptions, recommendations, search, playlists, comments, likes, live streaming, captions, analytics, monetisation
