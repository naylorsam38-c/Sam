# The Edge Map and the Frontier Watch

**For:** Sam · **Status:** strategy, evidence-backed · **Date:** 23 August 2026
**Built on:** the four prior documents plus a dedicated pass that checked, for each candidate edge, who occupies it today and whether it compounds or decays. The second half of this document specifies a self-analysing loop — the Frontier Watch — and a recurring scheduled task that runs it has been set up alongside this document.

---

## 1. The one-sentence answer

Your edge is not a feature; it is **four accumulations that nobody is collecting and that a lab cannot ship in a release**: a continuously published per-label error-rate series on real deliverables, a neutral re-run benchmark of the commercial grounding APIs with version history, a source-independence graph that tells copies of a wire story apart from corroboration, and the claim-level schema that signed verification records are validated against. Everything else in the design — conflict surfacing, credibility chips, false-success detection, brief gates, text marking — is a feature a lab or an observability vendor can close in one to two releases, and should be shipped as product, not bet on as moat.

The shape of the edge is the shape of an audit firm's edge, not a software company's: the longer you do it honestly and in public, the harder you are to replace.

---

## 2. The edge map

Every candidate from the design, graded on three things: who holds it today, whether it gets stronger with use or can be closed in a release, and how long an incumbent would need. "Unoccupied" means no evidence found in a dedicated search, not proof of absence.

| # | Edge | Who holds it (Aug 2026) | Compounds or decays | Time for an incumbent to close | Verdict |
|---|---|---|---|---|---|
| 1 | **Per-label calibration series** — the observed false-positive / false-negative rate of each verification label (`entailed`, `corroborated`, …) on real deliverables, published continuously | Nobody. Vendors publish one-off benchmark accuracies; the [AAR position paper](https://arxiv.org/html/2602.13855v1) proposes the metrics with no live data | **Compounds.** Needs a labelled stream, adjudicated truth over time, and willingness to publish your own misses — labs will not publish standing error rates on their own checkers | 18+ months, and only if they choose to | **Bet on it.** Slowest to stand up, hardest to copy |
| 2 | **Neutral head-to-head of the commercial grounding APIs** (Google Check Grounding, Azure Groundedness, Bedrock, Anthropic Citations, Cleanlab, Vectara, Galileo, Patronus, open checkers) on identical data, open harness, re-run on every version | Nobody for the paid APIs. [LLM-AggreFact](https://llm-aggrefact.github.io/) covers open models and 2024-vintage LLMs only; an industry note says outright that "without a public head-to-head … procurement stalls" ([BestAIWeb](https://www.bestaiweb.ai/patronus-lynx-vectara-hhem-and-bedrock-contextual-grounding-how-rag-faithfulness-tooling-evolved-in-2026/)) | **Compounds** — trust and drift history. A grant could make LLM-AggreFact add the APIs in a cycle, closing "first" but not "the neutral operator with history" | 3–6 months to exist; years to replicate the history | **Bet on it.** Also the cheapest credibility you can buy |
| 3 | **Source-independence graph** — telling two copies of one press release from two independent sources, so `corroborated` means something | Nobody ships it. Best practice is manual author cross-referencing ([BuzzStream, 4M citations](https://www.searchenginejournal.com/ai-search-barely-cites-syndicated-news-or-press-releases/569854/)); NewsGuard and Ground News rate outlets but expose no "these are one story" signal to agents | **Compounds.** The cheap 60% (embedding similarity between passages) decays in one release; the curated wire/ownership graph and fingerprint index compound | Crude: one release. Curated: 12+ months | **Bet on it**, and ship the crude version first so the label exists |
| 4 | **The claim-level record schema** — signed, portable, validated-against | Partially, at the wrong layer: Sigstore-based signing of agent *actions* is moving fast ([agent-sign](https://github.com/always-further/agent-sign), [Aeon](https://www.aeon.fun/blog/signed-by-the-agent), [Red Hat](https://next.redhat.com/2026/08/07/supply-chain-provenance-for-ai-agent-identity/), [Microsoft toolkit](https://microsoft.github.io/agent-governance-toolkit/tutorials/26-sbom-and-signing/), [RATS-based evidence packages](https://arxiv.org/html/2608.00801v1)). Nobody signs *claims with verification labels* | **Compounds if adopted; zero if not.** Crypto and transport are commodity; the schema being the one others validate against is the durable part | Emitting a signed manifest: one release. Schema adoption: 12+ months | **Bet on it** — with the ten-year caveat from the backwards plan |
| 5 | Verifier-independence conformance spec (family ≠ worker; pointers not prose) | Nobody as a spec; folk practice everywhere ([Play Favorites](https://arxiv.org/html/2508.06709v1) quantifies the bias; AI Verify, OWASP AISVS, MLCommons do not codify it) | Slow compounding if cited; inert otherwise | Labs will not close it — it would disqualify their own same-family self-verification. Risk is irrelevance, not competition | **Write it** — cheap, and it is the argument for the whole category |
| 6 | Conflict-as-first-class (`conflicted` label with both sides) | Partially: [CONFLICTS benchmark](https://arxiv.org/abs/2506.08500), SIGIR/WWW 2026 papers, Gemini's per-statement double-check UI | **Decays** — actively researched by Google- and Amazon-adjacent teams | 1–2 releases | **Ship it** as a feature; the durable slice is conflict between *independent* sources (needs #3) |
| 7 | Credibility-weighted citation label | NewsGuard holds the rating asset and licenses it; engines use opaque signals | **Decays** — anyone can license the asset | 1 release | **Ship it**; the only compounding part is which sources' claims later fail your verification (a by-product of #1) |
| 8 | False-success detector (environment state, not LLM judge) | Unoccupied as env-state; Sentrial markets the problem with behavioural classifiers; [the paper](https://arxiv.org/abs/2606.09863) gives the recipe | **Method decays** (TF-IDF over state diffs is trivially copied); **the corpus of (claimed-success, actual-state) pairs compounds** | 1–2 quarters for Arize / LangSmith / Braintrust | **Ship it** inside the Rail; keep the pairs |
| 9 | Pre-send brief quality gate | Partially: Kiro's clarifying-question loop; every harness will copy | **Decays** | 1 release per harness | **Feature**, not edge — unless spec-quality scores are tied to downstream verification outcomes (#1 again) |
| 10 | Machine-readable marking of AI-generated text (EU AI Act Art. 50(2)) | **Occupied by the labs.** Anthropic shipped SynthID-Text on all models after 2 Aug 2026; Google's SynthID network now includes OpenAI, Apple, NVIDIA; the Code of Practice was finalised 8 Jul 2026 with deadlines 2 Dec 2026 (marking) and 2 Feb 2027 (detection interoperability) ([Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content); [Anthropic](https://www.anthropic.com/news/claude-text-watermark)) | Decays for a third party | Already closed | **Do not compete on watermarking.** The open slot is the Code's *second* technique — signed, tamper-evident metadata on file-based deliverables saying which parts were generated and which verified — which is #4 with a regulatory deadline attached |

**What this changes from the backwards plan.** The plan named the verification record as the universal piece. The edge map narrows it: the record is the *vehicle*; the *edge* is the three datasets behind it (#1, #2, #3) and the schema (#4). The company's real asset in year three is not software, it is a calibration series, a benchmark history and an independence graph that took three years of honest publication to build. Reposition the first 180 days accordingly: the benchmark harness (#2) moves to the front of the queue because it is the fastest credibility and the cheapest to start; the calibration series (#1) starts the day the first design partner's deliverables flow, because it cannot be back-filled.

---

## 3. Where you will be overtaken in six months, and where you will not

**Fast fronts — expect incumbents here by Q1 2027.** Text watermarking and detection APIs (forced by the Code deadlines); source-disagreement chips in deep-research products; false-success detection inside observability suites; spec/brief gates inside agent IDEs; signed agent-action provenance on Sigstore. On each of these, be a user or a fast follower; none is worth a month of the team's time beyond shipping the minimum.

**Slow fronts — accumulation beats speed.** The calibration series, the re-run benchmark with version history, the independence graph. These are where the team's time goes, and they are exactly the things a weekly watch cannot lose for you — only neglect can.

---

## 4. The Frontier Watch — a self-analysing loop

The purpose is not to read news. It is to detect, early, the two events that change the plan: an incumbent closing an edge you are betting on, and an edge you dismissed becoming open. The loop has three cadences, each with a defined output and a defined decision. It uses the same method that produced these documents — parallel sourced research, adversarial review, citation check — so the quality does not depend on who is running it.

### 4.1 Weekly scan (automated; set up as a scheduled task alongside this document)

Every Monday, a fresh session runs the following, with no memory of previous runs other than this document's edge table, which it receives as its baseline.

1. **Search each of the ten fronts** for the past seven days: vendor release notes and blogs (Anthropic, OpenAI, Google, Microsoft, AWS, Braintrust, Arize, LangSmith, Galileo, Vectara, Cleanlab, NewsGuard, Patronus), arXiv (cs.CL, cs.AI, cs.SE) for claim verification / citation faithfulness / LLM-as-judge bias / agent evaluation, standards venues (OpenTelemetry GenAI SIG, OWASP AOS/AISVS, Agentic AI Foundation, C2PA, NIST agent initiative, AI Verify), and EU AI Act implementation news.
2. **For each front, classify the movement**: `none` · `feature shipped by incumbent` · `benchmark or dataset published` · `standard proposed or merged` · `regulatory date moved` · `funding or acquisition in the category`.
3. **Re-grade the edge table**: does any "bet on it" edge move from unoccupied to partially occupied? Does any "ship it" feature become table stakes? Does any dismissed edge open?
4. **Fire tripwires** (below) and emit a short report: what moved, which rows changed grade, the recommended action, and the three most important links. Push notification only if a tripwire fired; otherwise the report is filed.

### 4.2 Tripwires — the events that change the plan

| Tripwire | Why it matters | Action |
|---|---|---|
| A lab or cloud publishes a standing error rate per label or per grounding score on production traffic | #1 is being occupied | Publish yours the same week, with more labels and the methodology; the series you already have is the counter |
| A neutral benchmark of the commercial grounding APIs appears (LLM-AggreFact adds them; a university or MLCommons runs one) | #2 "first" is closed | Contribute to it rather than compete; keep the version-history slice; become a named maintainer |
| Any AI citation product ships a syndication / independence signal | #3 crude version closed | Ship the curated graph and the `corroborated` definition as the differentiator |
| A signed claim-level record appears from a lab, an observability vendor, or a Sigstore project | #4 contested | Translate to and from it on day one; make the open schema a superset; go to the foundation with both |
| OTel GenAI or OWASP AOS merges trust/verification attributes from someone else | Schema home taken | Implement theirs immediately; differentiate on #1–#3 |
| The Code of Practice's Feb 2027 detection-interoperability mechanism specifies a document-metadata format | #10 second-technique slot defined | Conform within 30 days; this is the regulatory hook for #4 |
| A lab publishes cross-family verification as a product surface (not advice) | The category's main argument is being made by a lab | Good for the category; the edge moves entirely to #1–#3 |
| Funding round or acquisition in claim verification above $50M | Category is being priced | Re-run the backwards plan's §9 kill list |

### 4.3 Monthly re-read (one human hour)

Read the four weekly reports together. Ask the three questions the weekly scan cannot: has the *pace* of any front changed; is the team's time still going to the slow fronts; has anything shipped that should become a feature of the Rail this month. Update the edge table in this document — it is the baseline for next month's scans.

### 4.4 Quarterly deep re-assessment (the full method, ~one day of compute)

Re-run the process that produced these documents, against the current edge table and the backwards plan: parallel research passes per front, an adversarial review whose explicit job is to refute the current edge grades, and a citation audit. Output: a dated revision of this document and of the plan's kill list. The adversarial reviewer is briefed to assume every "compounds" grade is wrong and to find the release that closes it.

### 4.5 What the loop measures about itself

A watch that never fires is either early or blind. Track, per quarter: tripwires fired; tripwires that in hindsight should have fired (found in the quarterly re-assessment); and the lead time between an incumbent's move and the watch's detection. If the hindsight count exceeds the fired count two quarters running, the fronts or the sources are wrong and the scan is redesigned.

---

## 5. What I would not do

Spend the team on any fast front beyond the minimum. Compete on watermarking. Wait for volume before starting the calibration series — it cannot be back-filled. Let the benchmark be funded or hosted by any vendor in the table — neutrality is the point. Treat the weekly scan as strategy; it is an alarm, and the monthly and quarterly passes are where decisions are made.

---

## 6. Open questions

1. Whether a dedicated literature pass under "evidence redundancy," "source clustering," and "churnalism detection" turns up prior work on independence labelling that this search missed — worth a day before committing to #3.
2. NewsGuard's API/licensing terms for agent developers were not confirmed from a primary source.
3. LLM-AggreFact's maintenance status — its visible commercial entries are 2024 models — determines whether #2 is contributed to or built beside.
4. Whether the calibration series (#1) can be published at design-partner volume without leaking partner data; the methodology needs a privacy design before the first publication.
5. Whether the Feb 2027 interoperability mechanism will specify a document-metadata format at all, or only watermark detection.
