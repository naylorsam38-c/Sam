# Aura build targets. `make build` refuses to build the image until the licence
# + dependency audit passes (spec §22–23 + correction).

.PHONY: audit test phase1 build demo-build run

audit:            ## fail (exit 2) on any licensing violation; exit 1 if unpinned
	python scripts/licence_audit.py

test:
	pytest -q

phase1:           ## offline visual proof (CPU fallback), spec Phase 1
	python scripts/phase1_proof.py --minutes 2

build: audit      ## production image; blocked unless `make audit` passes (exit 0)
	docker compose build

demo-build:       ## CPU fallback demo only; bypasses the gate (NOT licence-verified)
	docker build --build-arg SKIP_LICENCE_AUDIT=1 -t aura:demo .

run:
	docker compose up
