# Deployment

This system has not been deployed to any live infrastructure by this
build — it was built and verified entirely inside a sandboxed development
environment with no GPU, no cloud account, no persistent host, and no
browser. This document is what a deployer (human or Dispatch) needs to
actually stand it up, plus exactly what is and isn't already confirmed
working (per spec section 27's handoff requirements).

## Components and where they run

| Component | Where | Deployed here? |
|---|---|---|
| Open WebUI | Docker container (or standalone) | No — not deployed; `docker-compose.yml` defines it |
| Control API | Docker container, or native process | No — run locally in this session only, ephemerally |
| Worker | Docker container(s), or native process(es) | No — same |
| Local execution agent | Native process on the laptop (recommended); optional container | No |
| Local Ollama | Native install on the laptop | Stood in with a protocol-real fake server for testing only — **a real Ollama install was never used** |
| Cloud GPU | RunPod (or your chosen provider) | Not provisioned — `GPU_PROVIDER=mock` was used for all verification in this build |

## Exact versions

- Python: 3.11 (pinned via `requires-python`-equivalent expectations in
  `requirements.txt`; tested against CPython 3.11.15 in this build).
- Key pinned dependency ranges: see `requirements.txt` /
  `local-agent/requirements.txt` (FastAPI `>=0.110,<1.0`, SQLAlchemy
  `>=2.0,<3.0`, Alembic `>=1.13,<2.0`, PyJWT `>=2.8,<3.0`, `bcrypt
  >=4.0,<5.0`).
- Open WebUI: `ghcr.io/open-webui/open-webui:main` (a rolling tag — pin to
  a specific release tag before a real deployment if you want
  reproducibility; `main` was chosen here only because no specific version
  was specified and none was verified against).
- GPU pod base image: `nvidia/cuda:12.4.1-runtime-ubuntu22.04` with Ollama
  installed via its official install script (`gpu/image/Dockerfile`) — not
  built or pushed anywhere by this session.

## GPU provider and cost-control configuration

Default (`.env.example`): `GPU_PROVIDER=mock` (safe, free, for
development). For a real deployment: `GPU_PROVIDER=runpod`, plus
`GPU_PROVIDER_API_KEY`, `GPU_TEMPLATE_ID` (built from `gpu/image`), and
`GPU_VOLUME_ID` (a RunPod persistent network volume, created once).

Cost controls default to `GPU_MAX_HOURLY_COST=2.00`,
`GPU_MAX_SESSION_MINUTES=240`, `GPU_IDLE_TIMEOUT_MINUTES=20`, both
auto-start and auto-stop enabled. Change these in `.env` before a real
deployment to match your actual budget tolerance — the shipped defaults
are reasonable starting points, not a recommendation for your specific
cost ceiling.

## Deployment steps

1. `git clone` this repository onto the machine that will run the control
   API and worker (can be the same laptop that runs Ollama and the agent,
   or a separate always-on machine).
2. Follow `scripts/install/phase_a_laptop.sh` on the laptop (Ollama,
   Open WebUI, the agent).
3. Follow `scripts/install/phase_b_cloud.sh` for the cloud GPU — this
   requires you to actually create a RunPod account, API key, network
   volume, and template; the script verifies your configuration and gives
   you the exact commands to test a real start/stop, but will not spend
   your cloud budget without explicit confirmation.
4. Run `scripts/install/phase_c_tasks.py` and `phase_d_agent.py` against
   the now-real stack.
5. `make health` — confirm every `/health/*` endpoint is green against
   real Ollama, a real cloud GPU (once started), a real worker, and a
   real agent.

## Endpoints (once deployed)

There are no live deployment URLs to report — nothing was deployed to a
reachable host by this build. Once you deploy:

- Control API: `http://<your-host>:8000` (or behind whatever reverse
  proxy/TLS termination you put in front of it — see `docs/SECURITY.md`
  regarding not binding it to `0.0.0.0` on an untrusted network).
- Open WebUI: `http://<your-host>:3000`.
- Local execution agent: `http://<laptop>:8787` — should generally not be
  exposed beyond the machine(s) that need to reach it.

## Verification report

Given none of the above was actually deployed, there is no live
verification report to give beyond what `BUILD_REPORT.md` and
`TEST_REPORT.md` already state: 151/156 automated tests passing (5
honestly skipped, all naming what they'd need — real hardware/browser —
and where the same behavior is verified another way), plus a manual pass
against a real four-process stack (control API + worker + local agent +
protocol-real fake Ollama) run inside this build environment. Treat "it
works against the mock provider and a real agent process" as the ceiling
of what's confirmed; a real RunPod account, a real Ollama install, and
Open WebUI itself all still need to be exercised once deployed.
