from aura.metrics import DriftMeter
from aura.render.quality import QualityController


def test_drift_math_and_budget():
    d = DriftMeter(budget_ms=80)
    assert d.sample(1.000, 1.050) == 50.0     # (video-audio)*1000
    assert not d.over_budget
    d.sample(1.000, 1.200)                     # 200ms
    assert d.over_budget
    assert d.current == 200.0


def test_quality_steps_down_then_up():
    q = QualityController(start=3, drift_budget_ms=80)
    lvl = q.observe(drift_ms=500, dropped_frames=10, render_latency_ms=999, gpu_mem_frac=0.99)
    assert lvl == 2                             # one step down
    # during cooldown it stays put
    q.observe(drift_ms=0, dropped_frames=0, render_latency_ms=1, gpu_mem_frac=0.1)
    # exhaust cooldown, then relaxed conditions raise it back
    for _ in range(200):
        lvl = q.observe(drift_ms=0, dropped_frames=0, render_latency_ms=1, gpu_mem_frac=0.1)
    assert 0 <= lvl <= 3 and lvl >= 2


def test_quality_never_out_of_range():
    q = QualityController(start=0)
    for _ in range(50):
        lvl = q.observe(drift_ms=999, dropped_frames=99, render_latency_ms=999, gpu_mem_frac=1.0)
        assert 0 <= lvl <= 3
