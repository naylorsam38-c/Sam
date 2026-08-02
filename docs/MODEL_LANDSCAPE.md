# Open-model landscape — August 2026

Researched live, not from memory. Every licence below was checked against the
project's own LICENSE file or model card where reachable; where it could not be
verified that is stated rather than guessed.

**The one rule that matters:** a repository's LICENSE file does not govern its
model weights. Permissive code wrapped around restricted weights is the single
most common trap in this space, and it is invisible until someone's lawyer finds
it. Every table below separates the two.

---

## 1. The projects that already did the integration work

You were right that this is mostly assembled already.

| Project | Code | Weights | Real-time? | Notes |
|---|---|---|---|---|
| **[OpenAvatarChat](https://github.com/HumanAIGC-Engineering/OpenAvatarChat)** | Apache-2.0 | mixed by backend | Yes, ~2.2s avg | Modular ASR/LLM/TTS/avatar. v0.6.0 Apr 2026, 3.7k★. The closest thing to "done". |
| **[LiveTalking](https://github.com/lipku/LiveTalking)** | Apache-2.0 | by backend | **Yes** — WebRTC, full-duplex, barge-in | 8.6k★. MuseTalk at **72fps on a 4090**. Watermark required only for Bilibili/WeChat/Douyin publishing. |
| **[LiteAvatar](https://github.com/HumanAIGC/lite-avatar)** | MIT | MIT | Yes — **30fps on CPU alone** | ~3GB VRAM/session if GPU used. Cheapest concurrency by far. |
| **[SoulX-FlashHead](https://github.com/Soul-AILab/SoulX-FlashHead)** | Apache-2.0 | Apache-2.0 | Yes — **96fps, or 3 concurrent real-time sessions on one 4090** | Released Mar 2026, 1.3B. Newest and fastest. Young — evaluate stability yourself. |
| **[Duix.Avatar / HeyGem](https://github.com/duixcom/Duix-Avatar)** | Apache-2.0 | **custom** | **No — offline batch only** | 14.3k★ and widely miscalled a real-time HeyGen clone. Free commercial use only **below 100k users AND $10M revenue**. Real-time is their paid hosted product. |
| **LiveKit Agents / Pipecat** | Apache-2.0 / BSD-2 | n/a | Framework only | Their avatar plugins (Tavus, Simli, Anam, HeyGen, D-ID, Beyond Presence, bitHuman) are **closed hosted APIs** — they fail your "no fees but usage" rule. The orchestration is genuinely open. |

**Verdict:** LiveTalking is the closest working reference for real-time, and
SoulX-FlashHead is the fastest renderer. Both Apache-2.0. Neither is a product —
they're demos with a pipeline attached, which is exactly where this repo's
session/state/barge-in/drift layer earns its place.

---

## 2. Lip-sync renderers

| Model | Code | Weights | Real-time | Notes |
|---|---|---|---|---|
| **MuseTalk v1.5** | MIT | **MIT, commercial explicitly allowed** | 30fps+ V100, **72fps 4090** | 256×256 face region; some jitter and identity loss (moustache, lip colour). Still the safest real-time pick. |
| **SoulX-FlashHead** | Apache-2.0 | Apache-2.0 | 96fps 4090 (Lite) | Pro variant: 10.8fps on one 4090, real-time needs 2×5090. |
| **[LatentSync](https://github.com/bytedance/LatentSync) 1.6** | Apache-2.0 | Apache-2.0 | **No** — diffusion, 20–50 steps | 512×512, better quality than MuseTalk. 18GB VRAM. Needs a driving **video**. Good for offline marketing renders, not live. |
| **Ditto-talkinghead** | Apache-2.0 | Apache-2.0 | Claims streaming | Needs TensorRT. No independent fps benchmark found. |
| **EchoMimic v3** | Apache-2.0 | Apache-2.0* | No | *Built on Wan2.1-Fun — base model terms still apply. |
| **Sonic** | — | **non-commercial** | — | Repo directs commercial users to Tencent Cloud's paid product. Excluded. |
| **FLOAT** | CC-BY-NC-ND | same | — | No commercial, no derivatives. Excluded. |
| **JoyVASA / LivePortrait** | MIT | **trap** | No | Pulls InsightFace `buffalo_l` at inference — non-commercial. Inherited by anything built on LivePortrait unless you swap the detector. |
| **Wav2Lip** | — | ambiguous | Fast | Original weights research-licensed; every fork restates it differently. Excluded on principle. |

**Concurrency reality:** nobody publishes trustworthy numbers except SoulX
(3 concurrent on a 4090) and LiteAvatar (~3GB/session). The avatar-serving world
has no vLLM-equivalent benchmark suite yet. **Budget for load-testing this
yourself** — quoted numbers elsewhere are estimates.

---

## 3. Voice — and a correction to what I told you earlier

**I was wrong about Kokoro for your use case.** It is Apache-2.0 and excellent,
but it has **no voice cloning at all** — 54 fixed preset voices. If you want one
consistent brand voice that is *yours*, Kokoro cannot do it.

### Cleanly licensed, cloning-capable, self-hosted

| Model | Code | Weights | Cloning | Latency | VRAM |
|---|---|---|---|---|---|
| **Chatterbox** (Resemble) | MIT | **MIT** | Yes, commercial-clear | ~470ms first chunk (4090, streaming fork) | 2–8GB |
| **Orpheus** (Canopy) | Apache-2.0 | Apache-2.0 | Yes | ~200ms streaming | ~8GB |
| **Kani-TTS-2** | Apache-2.0 | Apache-2.0 | Yes | RTF ~0.2 | **~3GB** — smallest |
| **ZONOS2** (Zyphra) | MIT | MIT | Yes | real-time | — |
| **Qwen3-TTS / Qwen3.5-Omni** | Apache-2.0 | Apache-2.0 | Yes, 3s reference | ~97ms claimed | 6GB+ |
| **Kokoro-82M** | Apache-2.0 | Apache-2.0 | **No — presets only** | ~100–300ms | <2GB |

**Chatterbox** is now the self-hosted default in this repo. It embeds a PerTh
watermark by default, which is a compliance feature — see §6.

### Speech traps — permissive code, restricted weights

- **F5-TTS** — MIT code, **CC-BY-NC-4.0 weights** (Emilia dataset).
- **Fish Speech / OpenAudio** — Apache code, **CC-BY-NC-SA weights**. Fish Audio S2 needs a paid licence.
- **XTTS-v2** — MPL code, **CPML weights**. Coqui shut down in Jan 2024, so **there is nobody left to sell you a commercial licence**. Permanently non-commercial.
- **IndexTTS-2** — Apache code, **custom bilibili licence** requiring prior *written* authorisation.
- **Higgs Audio** — v2 Apache-2.0 and fine; **v3 flips to research/non-commercial**.
- **VibeVoice** (Microsoft) — MIT-labelled, but Microsoft disclaims commercial use and pulled the inference code after misuse.
- **Voxtral TTS** (Mistral) — **CC-BY-NC-4.0**, despite Mistral's other 2026 releases being Apache.
- **MiniCPM-o** — Apache badge, real caps (≤5,000 devices or <1M DAU, plus registration).

All of the above are now in the repo's forbidden or conditional lists.

### Speech-to-text

| Model | Licence | Speed | Streaming |
|---|---|---|---|
| **Parakeet-TDT 0.6B** (NVIDIA) | **CC-BY-4.0** | RTFx ~3300x GPU, ~30x CPU | Yes, ~160ms |
| **Whisper large-v3-turbo** | **MIT** | 25–30x with faster-whisper | Chunked |
| **Moonshine** | MIT | streaming-native | Yes |
| **Canary-1B original** | **CC-BY-NC** ✗ | — | Use -Flash / -v2 / -Qwen instead (CC-BY-4.0) |

Parakeet is now first in the self-hosted chain.

### The thing that could delete half your pipeline

End-to-end speech-to-speech models replace STT→LLM→TTS entirely:

- **[NVIDIA PersonaPlex-7B](https://github.com/NVIDIA/personaplex)** (Jan 2026) — MIT code, NVIDIA Open Model License weights, both commercial. **~70ms speaker-switch**, native full-duplex with backchannelling. Reportedly runs in 8GB. Prioritise evaluating this.
- **Qwen3.5-Omni** (Mar 2026) — Apache-2.0, single 4090 at INT4. ~234ms theoretical, **~700ms measured** in practice.
- **Moshi** (Kyutai) — CC-BY-4.0, the reference architecture, but scored 1.26/5 on instruction-following in NVIDIA's benchmark. Talks beautifully, obeys poorly.
- **Step-Audio 2 mini** — Apache-2.0, 8B. Caveat: the voice training-data consent chain is undocumented, which is a PR risk even with a clean licence.

**Caution:** even the full-duplex models still need your own turn-taking and
barge-in orchestration in production. They do not remove the layer this repo
already implements.

---

## 4. Text-to-video for marketing

| Model | Licence | Reality |
|---|---|---|
| **[Wan 2.2](https://github.com/Wan-Video/Wan2.2)** | **Apache-2.0, genuinely unrestricted** | Best open photorealism. **TI2V-5B runs on a 4090 (24GB), 5s of 720p in <9 min.** The 14B variants officially want **80GB** — community GGUF quantisations fit 24GB with quality loss. |
| **HunyuanVideo 1.5** | **Tencent Community Licence** | Widely miscalled Apache. **Does not apply in the EU, UK or South Korea at all.** Separate licence above 100M MAU. Best physics/motion. |
| **LTX-2 / 2.3** | **revenue-capped** | Marketed as open. Free only **under $10M annual revenue**, then a paid agreement with **2× liquidated damages**. Fastest, native 4K, synced audio. |
| **Mochi-1, CogVideoX, Open-Sora 2.0, SkyReels-V2** | Apache-2.0 | Clean fallbacks, trail on quality. |
| **Step-Video-T2V** | MIT | Genuinely MIT, but **300B params** — not a single-GPU model. |

**Wan 2.2 is the pick** and it is what this repo already targets. No revenue cap,
no geography clause, no output claim.

**Honest gap:** as of Aug 2026 the closed leaders (Veo 3.1, Kling 3.0, Seedance
1.5 Pro) still beat open weights on prompt adherence and top-end fidelity. Open
has closed much of the gap, not all of it. Sora is being discontinued — the API
shuts down 24 September 2026, so don't build on it.

**Consistency for branding:** train a LoRA with `musubi-tuner` (ComfyUI node
available) or `diffusion-pipe`. Avoid InstantID / IP-Adapter-FaceID — both pull
InsightFace, which is non-commercial and already banned by this repo's gate.

---

## 5. Hardware and cost

| GPU | Rent | What it does |
|---|---|---|
| RTX 4090 24GB | **$0.29–0.69/hr** | Live avatar (3 concurrent, SoulX) *or* Wan 2.2 TI2V-5B. Not both at once. |
| L40S 48GB | **$0.26 spot – $0.86/hr** | Comfortable live + LoRA training. No aggressive quantisation. |
| H100 80GB | **$2.46–2.69/hr** spot | Full-precision Wan 14B, batch generation, full fine-tunes. |

**Latency budget for the live avatar:** users tolerate ~200ms before the voice
starts but expect a first video frame within **~900ms**. Two seconds reads as
broken. A well-streamed self-hosted cascade lands at **300–600ms** to first
audio; a naive non-streaming pipeline lands at 2–5s, which is the difference
between a product and a demo.

---

## 6. Compliance — this one is live as of today

**EU AI Act Article 50 transparency obligations took effect 2 August 2026.** Any
system generating synthetic audio must mark it as artificially generated in a
machine-readable way, and deployers of voice-cloned or deepfake content must
disclose that it is synthetic.

This is not optional for a product serving the EU. Chatterbox's default PerTh
watermark satisfies the audio half; the video half needs C2PA metadata or an
equivalent marker on generated output.

Separately: **a permissive model licence never grants rights to a person's voice
or face.** US right-of-publicity law applies independently of MIT or Apache. If
you clone a real person — including yourself, if the company is a separate legal
entity — get a written release covering AI cloning and commercial synthetic use.
That is exactly what `aura/studio/provenance.py` records and what audit rule R7
enforces.

*(One caveat: some 2026 coverage references a US "Federal AI Voice Act". I could
not corroborate its passage against an authoritative legislative source. Confirm
with counsel rather than relying on it.)*

---

## 7. What this means for the build

**Live avatar (self-hosted tier):** SoulX-FlashHead or MuseTalk v1.5 for render,
Chatterbox for a cloned brand voice, Parakeet for STT. All MIT/Apache/CC-BY.
One 4090 serves ~3 concurrent conversations. Evaluate PersonaPlex as a possible
replacement for the whole STT→LLM→TTS chain.

**Marketing video:** Wan 2.2, brand LoRA trained with musubi-tuner. Rent an
L40S or H100 for generation runs rather than owning — video generation is bursty,
and bursty workloads are exactly where renting wins.

**If you sell this:** every component above is either permissive or explicitly
recorded with its condition. The revenue caps (LTX-2 at $10M, Duix at $10M/100k
users) are the ones that bite a *successful* product, which is the worst time to
discover them.
