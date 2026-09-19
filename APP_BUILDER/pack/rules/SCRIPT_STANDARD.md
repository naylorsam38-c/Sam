# The Script Standard

**Status: LOCKED. 2026-09-08.**

This is the standard every script written for this system must meet — by me, by a
model, by a contractor, by anyone. It is not a style guide and it is not advice.
A script that does not meet it is not finished, however well it runs.

Hand this document to whoever is building. If they push back on any rule here,
the answer is no.

---

## 0. Why this exists

Scripts pass their tests and then the thing doesn't work in the real app. That
happens for one reason: the script tested its own idea of the system instead of
the system. Everything below exists to close that gap and keep it closed.

The finish line is not "it works." The finish line is that the script proves it
works, out loud, against the real thing, and repairs itself when the real thing
moves.

---

## 1. The hard rules

These are absolute. They are not traded off against time, difficulty, token
cost, or convenience.

### 1.1 No mocks. No simulations. No fake providers. Ever.

- Tests run against the real model and the real system, or they are not evidence.
- A green test suite that never touched the live thing does not count as proof
  of anything.
- This extends to test data. Never synthesise a product, an answer, or a
  requirement in order to exercise a code path. Real products, real answers,
  real tests.
- If the real thing cannot be reached, the script does not substitute something
  that can. It stops and says what it could not reach. See rule 1.4.

### 1.2 Testing means running it

Testing is starting the real thing as a real process and driving it from the
outside — real requests, real database, real browser where a person would use
one. Reading the code and reasoning about it is not testing. Neither is calling
a function directly in the same process that defines it.

If a human would click it, the test clicks it.

### 1.3 Every script opens with a config block

Above any logic, plainly labelled, editable. One comment per setting, in plain
English, saying what it does and what changes if it is altered. The person
running the script must be able to tune it without reading the code below it.

No setting hidden further down the file. No magic numbers inline.

### 1.4 If something is unknown, do not guess

Pause that specific step. Name the gap. Surface it clearly. A guess that happens
to work is worse than a stop, because it hides the gap until later.

"Held, awaiting X" is an acceptable outcome. Inventing X is not.

### 1.5 Never reconstruct a document from memory and present it as the real file

If the actual file is not on disk, say so and ask for it. A reconstructed
document that looks right is the most expensive mistake available.

### 1.6 Touch nothing except what was asked

No opportunistic refactors, no tidying, no renaming on the way past. Change what
was asked, test it, deliver it.

### 1.7 Deliver only after testing passes

Not "should work." Not "passes locally, untested end to end." Build it, test it,
break it, fix it, retest it until it is stable. Then verify the result against
the original request before calling it complete.

---

## 2. The three-layer architecture

Every script is built in three layers. This is the shape. The language and the
framework do not matter — the shape does.

### Layer one — the hard checks

The script runs and each check passes or fails. No model involved. No cost. This
is the whole script on a good day, and a good day should be almost every day.

Each check is one claim about the real system, written as the claim, printed as
one line:

```
PASS  a one-sided like mints no match
PASS  the like back mints a real match
FAIL  the rendered page threw no javascript errors
```

Checks are written as **the job**, not as the screens. "A person arrives, picks a
look, moves a button, and ends up with a usable app" — not "the customise screen
renders." Written as screens, gaps hide between them. Written as the job, gaps
fail themselves into view.

### Layer two — repair from the shelf

When a check fails, layer two reads the failure's own message. If the fix is
already a numbered part on the shelf, it drops that part in and carries on.

Still no model. Still no cost. This layer gets stronger every time layer three
runs, and it is where the system should spend most of its repair work forever.

Layer two never invents a fix. It only places parts that already exist and are
already numbered.

### Layer three — build the missing part

Reached only when the shelf genuinely does not have it. The model builds the
part, the part gets numbered into the library, and from that moment layer two
owns it.

Every trip to layer three permanently shrinks how often layer three is needed.
That is the entire point of the design. A script that keeps calling layer three
for the same failure is broken — the part was never numbered.

---

## 3. Repair must never hide anything

This is the rule that makes the three layers safe.

When layer two or layer three fixes something:

- The original failure is still **named** in the output. It does not disappear
  because it was repaired.
- The part used or created is still **numbered** and stated by number.
- The run reports what broke, what fixed it, and which layer did it.

Healing, not covering up. A silent self-repair is indistinguishable from a bug
that hasn't surfaced yet, and it will surface at the worst time.

Correct output looks like:

```
FAIL  the public form dropdowns were empty
      repaired by shelf part option_source_binding@1.2.0 (layer 2)
PASS  the public form dropdowns were empty  [after repair]
```

Never like:

```
PASS  the public form dropdowns were empty
```

---

## 4. Numbering a held gap

New numbers are permanent, so they are the one thing that waits on approval.

1. Layer three identifies behaviour that is genuinely not on the shelf.
2. Same behaviour = same number. If the shelf already does this and only a
   setting differs, that is a variation against the existing part, not a new
   number.
3. Genuinely new behaviour is **held**. The library is not touched.
4. The held item goes on a review list showing only what is NEW — never the
   already-approved items. Yes or no down the list.
5. On approval it is numbered into the library and layer two owns it from then
   on.

The unit reviewed is a finished, working app, not a loose part. A working app is
something that can actually be judged, and the app running is itself the proof of
the parts underneath it.

A "no" means that app does not ship. It never bins the part — the parts are the
asset, and binning one means rebuilding it later.

---

## 5. Output contract

The person reading the output is not going to read the whole thing, and should
not have to. The script must be readable from two places only:

- **Any line starting `FAIL`** — what broke.
- **The last line** — the verdict.

Therefore:

- One line per check. The line states the claim in plain English, not a test
  function name.
- The final line is a verdict and a count: `14/14 checks passed` followed by a
  plain-English PASS or the failures.
- If a section did not run, it says `SKIP` and says why. **Skipped is not
  passed.** A run that finishes suspiciously fast or reports `SKIP` on the
  browser half has not proved what it claims.
- Never print a pass for something that was not actually executed.

---

## 6. Environment hygiene

- Every run builds fresh. Delete and rebuild the working directory so the script
  can never read a stale database and report a pass from last time.
- The script starts its own process on its own port and shuts it down at the
  end, including on failure.
- Real credentials live in the config block and never in a shared archive, a
  repository, or a chat message. If a key is missing, the script stops and says
  which key. It does not fall back to anything.

---

## 7. Verification before delivery

Before a script is called complete:

1. Run it. It passes.
2. Break the thing it tests on purpose. The script must fail, and the failure
   message must name the actual cause.
3. Fix it. Run again. It passes.
4. Read the checks back against the original request. Every requirement asked
   for has a check that would catch its absence.
5. Look for the next failure point before it becomes a problem, and say what it
   is.

A script that has never been seen to fail has not been tested. It has been run.

---

## 8. The standard

Do the whole thing, do it right, with tests and documentation.

Never table work when a permanent solution is within reach. No workarounds when
a proper fix exists. Time, fatigue, complexity and inconvenience are not reasons
to lower any of this.

The finish line is: **"Holy shit, that's done."**

Then reverse-engineer it, self-assess against this document, and repeat.
