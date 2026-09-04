"""Engine library: real, stdlib-only capabilities the Builder wires into a
generated app. Each module implements one engine and exposes `prove()`,
which runs a real scenario against a real system (a real sqlite database, a
real socket server, a real file on disk, real elapsed wall-clock time) and
returns the real observed evidence. No engine here is faked, mocked, or
stubbed -- see ../ENGINE_CATALOGUE.md for the full registry and
../PROOFS.md for every prove() run's actual captured output.
"""
