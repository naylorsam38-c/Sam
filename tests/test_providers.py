"""The API-vs-self-hosted switch: resolution order, licence gating, honest
degradation, and the cost maths that decides which tier you should be on."""
import pytest

from aura.providers import registry
from aura.providers.base import (Cost, ProviderInfo, ProviderUnavailable,
                                 Requires, Tier)
from aura.providers.licences import commercial_ok, is_noncommercial


# ── licence clearance ───────────────────────────────────────────────────────
def test_permissive_licences_clear():
    for lic in ("MIT", "Apache-2.0", "BSD-3-Clause"):
        assert commercial_ok(lic)


def test_noncommercial_licences_never_clear():
    for lic in ("CC-BY-NC-4.0", "S-Lab License 1.0", "CPML",
                "research only", "flux-1-dev"):
        assert is_noncommercial(lic)
        assert not commercial_ok(lic)


def test_unknown_licence_is_not_cleared():
    """Allow-list, not deny-list: guessing wrong here ships someone else's
    weights in a product you sell."""
    assert not commercial_ok("SomeCorp Custom License v2")
    assert not commercial_ok(None)


def test_separate_process_clears_copyleft_but_not_noncommercial():
    gpl = ProviderInfo(name="x", tier=Tier.FALLBACK, licence="GPL-3.0-or-later",
                       separate_process=True)
    assert gpl.commercial          # exec'd binary, never linked

    nc = ProviderInfo(name="y", tier=Tier.API, licence="CC-BY-NC-4.0",
                      separate_process=True)
    assert not nc.commercial       # no boundary makes "don't sell this" go away


# ── requirement probing ─────────────────────────────────────────────────────
def test_missing_requirements_are_named(monkeypatch):
    monkeypatch.delenv("SOME_KEY_XYZ", raising=False)
    r = Requires(env=("SOME_KEY_XYZ",), packages=("definitely_not_a_module",),
                 binaries=("definitely_not_a_binary",))
    missing = r.missing()
    assert "env:SOME_KEY_XYZ" in missing
    assert "pkg:definitely_not_a_module" in missing
    assert "bin:definitely_not_a_binary" in missing


def test_satisfied_requirements_report_nothing(monkeypatch):
    monkeypatch.setenv("SOME_KEY_XYZ", "present")
    assert Requires(env=("SOME_KEY_XYZ",), packages=("json",)).missing() == []


# ── resolution ──────────────────────────────────────────────────────────────
class _Fake:
    """Minimal provider used to drive the registry deterministically."""
    def __init__(self, info, fail=False):
        self.info, self._fail = info, fail
        self.setup_called = False

    async def setup(self):
        self.setup_called = True
        if self._fail:
            raise ProviderUnavailable("boom")

    async def close(self): ...


def _register_fakes(kind, monkeypatch, entries):
    """entries: [(name, info, fail)] — installs an isolated chain."""
    monkeypatch.setitem(registry._REGISTRY, kind,
                        {n: (lambda i=i, f=f, **kw: _Fake(i, f))
                         for n, i, f in entries})
    monkeypatch.setitem(registry.POLICIES, "test",
                        {kind: [n for n, _, _ in entries]})


async def test_first_usable_provider_wins(monkeypatch):
    good = ProviderInfo(name="good", tier=Tier.API, licence="MIT")
    _register_fakes("tts", monkeypatch, [("a", good, False), ("b", good, False)])
    p, res = await registry.resolve("tts", policy="test")
    assert res.chosen == "a" and p.setup_called


async def test_falls_through_when_setup_fails(monkeypatch):
    info = ProviderInfo(name="x", tier=Tier.API, licence="MIT")
    _register_fakes("tts", monkeypatch, [("a", info, True), ("b", info, False)])
    _p, res = await registry.resolve("tts", policy="test")
    assert res.chosen == "b"
    assert res.skipped and "unavailable" in res.skipped[0][1]


async def test_noncommercial_provider_is_skipped_in_commercial_mode(monkeypatch):
    bad = ProviderInfo(name="bad", tier=Tier.API, licence="MIT",
                       weight_licence="CC-BY-NC-4.0")
    good = ProviderInfo(name="good", tier=Tier.API, licence="MIT")
    _register_fakes("tts", monkeypatch, [("bad", bad, False), ("good", good, False)])

    _p, res = await registry.resolve("tts", policy="test", commercial=True)
    assert res.chosen == "good"
    assert "licence not cleared" in dict(res.skipped)["bad"]

    # opting out is possible, but must be explicit
    _p, res = await registry.resolve("tts", policy="test", commercial=False)
    assert res.chosen == "bad"


async def test_missing_requirement_skips_without_calling_setup(monkeypatch):
    gated = ProviderInfo(name="gated", tier=Tier.API, licence="MIT",
                         requires=Requires(env=("NOPE_NOT_SET",)))
    good = ProviderInfo(name="good", tier=Tier.API, licence="MIT")
    monkeypatch.delenv("NOPE_NOT_SET", raising=False)
    _register_fakes("tts", monkeypatch, [("gated", gated, False), ("good", good, False)])
    _p, res = await registry.resolve("tts", policy="test")
    assert res.chosen == "good"
    assert "missing env:NOPE_NOT_SET" in dict(res.skipped)["gated"]


async def test_explicit_engine_jumps_the_queue(monkeypatch):
    info = ProviderInfo(name="x", tier=Tier.API, licence="MIT")
    _register_fakes("tts", monkeypatch, [("a", info, False), ("b", info, False)])
    _p, res = await registry.resolve("tts", policy="test", engine="b")
    assert res.chosen == "b"


async def test_exhausted_chain_names_every_reason(monkeypatch):
    info = ProviderInfo(name="x", tier=Tier.API, licence="MIT")
    _register_fakes("tts", monkeypatch, [("a", info, True), ("b", info, True)])
    with pytest.raises(RuntimeError) as e:
        await registry.resolve("tts", policy="test")
    assert "a (" in str(e.value) and "b (" in str(e.value)


# ── real registered providers degrade rather than explode ───────────────────
async def test_real_chain_lands_on_a_fallback_with_no_keys_or_gpu(monkeypatch):
    for k in ("CARTESIA_API_KEY", "ELEVENLABS_API_KEY", "DEEPGRAM_API_KEY",
              "SIMLI_API_KEY", "SIMLI_FACE_ID", "AURA_MUSETALK_HOME"):
        monkeypatch.delenv(k, raising=False)
    _p, res = await registry.resolve("stt", policy="auto")
    assert res.info.tier == Tier.FALLBACK
    _p, res = await registry.resolve("avatar", policy="auto",
                                     source_image="assets/nova.png")
    assert res.chosen == "fallback"


# ── cost maths: the number that decides API vs own GPU ──────────────────────
def test_api_cost_is_flat_per_minute():
    assert Cost(per_minute=0.03).effective_per_minute(0.1) == 0.03


def test_gpu_cost_worsens_as_the_box_sits_idle():
    gpu = Cost(gpu_hour=0.60)
    busy = gpu.effective_per_minute(1.0)
    quiet = gpu.effective_per_minute(0.1)
    assert busy == pytest.approx(0.01)
    assert quiet == pytest.approx(0.10)
    assert quiet > busy      # idle GPU time still bills; APIs do not


def test_break_even_between_tiers():
    """A $0.50/hr GPU beats a $0.0577/min API only above ~14% utilisation."""
    api, gpu = 0.0577, Cost(gpu_hour=0.50)
    assert gpu.effective_per_minute(0.05) > api     # mostly idle -> rent the API
    assert gpu.effective_per_minute(0.30) < api     # busy -> own the card
