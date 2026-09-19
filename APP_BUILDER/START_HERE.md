# START HERE

Everything in one place. Three things at the top level:

| | |
|---|---|
| `THE_BUILD_CHAIN.md` | **Read this first.** What each script is and what it does. |
| `pack/` | The working system. Harvest, numbering, assembly, host, chain. |
| `GOD_MODE/` | The rules and standards the whole thing is built against. |

---

## To run it

```
cd pack/5_chain
python chain.py
```

One command. It finishes on **BUILT**, **HELD**, or **BROKEN**, and the last
line is the verdict and only the verdict.

It needs the real system around it: PostgreSQL, Redis, and a real config file at
`/tmp/indico_real.conf`. Without those it says so and claims nothing — it does
not pretend to have run.

To run the whole chain at zero cost, with no model ever touched, set
`ALLOW_LAYER_THREE = False` in `chain.py`.

---

## The pack, in order

| | |
|---|---|
| `1_harvest/` | Pulls real parts out of real source repositories. Never invents code. |
| `2_numbering/` | Gives every app, capability and part its permanent number. |
| `3_assembly/` | Builds an app from numbered parts on the shelf. |
| `4_host/` | Serves only the routes the shelf governs. Refuses everything else. |
| `5_chain/` | The five scripts that build, prove, repair and audit. |
| `shelf/` | The parts themselves, with provenance and licence on each. |
| `rules/` | The standards, byte-identical to the copies in `GOD_MODE/`. |
| `evidence/` | Live run evidence. |

---

## God mode

`GOD_MODE/ACTIVE/` holds what is in force. The two locked standards are in
`ACTIVE/active_standards/` — the Script Standard and the Build Chain Standard.

Those are the authority. They settle a disagreement. But
`THE_BUILD_CHAIN.md` is what describes the system as it actually exists, and it
is the one to read.

`REGISTERS/CHANGE_HISTORY.md` is the trail of what changed and why.
`ARCHIVE/` is history and is deliberately left alone.

---

## Where it stands

Ten capabilities bound and running for real against a real Indico-backed host:
register, log in, log out, search records, filter list, view record detail, book
slot, scan barcode, send email notification, generate report. Every one harvested
from real source, every one proven by a real browser journey.

The chain runs end to end and reaches BUILT.

Six capabilities are correctly absent because they need a key, not a part: take
payment, issue refund, apply discount code, send push notification, split
payout, manage inventory. The code paths exist and run. They hit a wall where
the credential should be.

Layer three refuses to run until a model endpoint is set. That is the next step,
and `RENT_A_GPU.md` is what it needs.
