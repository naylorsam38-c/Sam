# Command Desk — what I proposed, for you to correct

You answered 0.01 **guided**: you decide the product things, the plumbing gets
proposed and you confirm. The 28 questions that were open were plumbing, so
they are filled in below rather than asked. Every line is a proposal. None of
it is something you said. Correct any of it and the build follows —
`packages/requirements-engine/build_command_desk.py` holds all of it in one
editable block.

The app is built and proven live against these. If you change one, the change
flows: rerun that script, `lock_structure.py`, `bind_and_assemble.py`, and the
live test rebuilds the app from the new answers.

---

## The upload limit

- **100 MB** per document. You said "no limit set"; the upload path needs a number.

## What starts, moves and finishes each lifecycle

### Agent lifecycle

- **Starts when:** an agent is created and switched on; it starts in 'running'
- **running → stopped-and-reported** by the system — the agent stops and reports that it stopped, why, and what it could be doing instead
- **stopped-and-reported → running** by the system — the agent is switched back on (On = yes)
- **stopped-and-reported → offline** by the system — the agent is switched off (On = no)
- **Preconditions:** none
- **When it finishes:** the agent stops running; its last report stays on the record and its jobs are left where they are

### Conversation lifecycle

- **Starts when:** an agent writes the first message of a thread; it starts in 'open'
- **open → needs attention** by the system — the thread carries something Sam has not read that Hub judges he needs to see
- **needs attention → closed** by the system — Sam has read it and nothing on it is outstanding
- **open → closed** by the system — the job it belongs to reaches done or failed and nothing on it is outstanding
- **Preconditions:** none
- **When it finishes:** the conversation locks and stays readable; Hub keeps it as the record of what was discussed

### Project lifecycle

- **Starts when:** creates a project and sets its goal
- **active → paused** by Sam
- **paused → active** by Sam
- **active → finished** by the system — Sam marks the goal met and no job under the project is queued or running
- **Preconditions:** none
- **When it finishes:** the project locks: its jobs and conversations stay linked and readable, and it stops setting system-wide context

### Linked service lifecycle

- **Starts when:** a service is connected through the Connect a service form; it starts in 'connected'
- **connected → expired** by the system — a real call to the service is refused because its token or key is no longer valid
- **expired → connected** by the system — the service is reconnected and a real call to it succeeds
- **expired → disconnected** by Sam
- **connected → disconnected** by Sam
- **Preconditions:** none
- **When it finishes:** the service stops being offered to agents; nothing that used it is deleted

### Job lifecycle

- **Before queued → running:** the job's agent exists and is on
- **When it finishes:** the job locks, its result and its cost stay on the record, and the done or failed notification fires

### Document lifecycle

- **Before filled → signed:** every detected field is filled or waived
- **When it finishes:** the completed copy and its attestation stay on the record; the original is untouched

## The approval rule

- **running** is the stage that waits, approved by **Sam**. A job pauses there when it reaches an irreversible action — sending an email, paying for something.
- If you decline, the job goes to **failed** and can be resubmitted: **yes** (that is what Retry does).

## How the report numbers are counted

- **jobs done per agent per week** — a job counts once, in the ISO week its Finished at falls in, against the agent named on the job, when its stage is done
- **jobs failed per agent per week** — a job counts once, in the ISO week its Finished at falls in, against the agent named on the job, when its stage is failed; a job that was retried and then finished counts as done in the week it finished and no longer counts as a failure

## The executable half of the buttons and reports

The interview records what a button *does* in prose. The Builder needs it as
an operation, so each one is declared:

- **Pause** — sets the agent's *Is on* to no and its stage to *stopped-and-reported*
- **Retry** — puts the job back to *queued* and clears its result and finish time
- **Open source document** — reads the stored original; changes nothing
- **Activity per agent** — counts jobs grouped by agent, filtered to stage done / failed
- **Cost** — sums the Job record's own Cost field, grouped by agent

## How each linked service authenticates

- **Gmail** — a real OAuth round trip
- **Google Calendar** — a real OAuth round trip
- **Tavily search** — a key you paste in
- **Model providers** — a key you paste in

Two smaller ones, both stated here rather than hidden:

- The calendar integration is named **Google Calendar**, so it resolves to a real provider.
- The Agent record's on/off field is called **Is on**: `on` is a SQL keyword and would not build.

## The one thing still missing

Your orb artwork — `orb-glyph.png` and `orb-rotor.png` — is not in this
repository, so the proven build carries the starter library's mark instead.
Drop those two files into `packages/builder/assets/` and the build uses yours.

