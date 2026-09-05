# From Nova v2 to the Thing Everyone Uses — A Backwards Plan

**For:** Sam · **Status:** strategy, evidence-backed, red-teamed twice · **Date:** 22 August 2026
**Built on:** the Nova v2 design and the three research reports, plus new passes on the 2026 competitive landscape and on whether the verification layer is owned; then an adversarial operator-investor review that found two misread sources, a stale regulatory date, and a unit-economics contradiction — all corrected below. Where the plan rests on judgement rather than evidence, it says so.

---

## 1. The answer first, including the part you will not like

Working backwards from "in a few years everyone has to use it," the piece of Nova v2 that can become universal is not the orchestrator, not the assistant, and not the grounding detector. It is the **verification record** that Nova v2's Rail, conviction labels and deliverable gate together produce: every claim in a deliverable labelled by the check that earned it, verified by a model that did not write it, packaged as a signed, open, machine-readable record that a reader, an auditor or another agent can rely on without redoing the work.

That record is unowned today. Claim-grounding *scores* are a commodity — Google, Azure and AWS sell per-claim APIs; Anthropic ships Citations free; five open 7–8B checkers score within noise of each other. But no standard defines the record above the score: OpenTelemetry's GenAI conventions carry no trust or confidence attribute and are still "Development" status; the Agentic AI Foundation's charter names MCP, goose and AGENTS.md and nothing about attestation; C2PA covers images and audio, not text; the EU AI Act mandates event logs, not veracity. And trust is the stated blocker: 34% of enterprises say they trust agent actions, 70% name trust-and-governance as the scaling barrier, 51% name output accuracy, 74% of governance leaders rate inaccuracy a highly relevant risk — with the caveat that four of those five surveys are vendor-commissioned (Boomi, Deloitte, Teradata, KPMG) and should be read as direction, not magnitude.

Now the part that the red-team forced and that I think is right. **"Everyone has to use it in a few years" is not an honest promise for a content-trust standard.** Every precedent for attaching a trust record to content took a decade and a platform mandate: SPF (2006), DKIM (2007) and DMARC (2012) were only *mandated* for bulk senders by Google and Yahoo in February 2024; C2PA launched in 2021 with Adobe, Microsoft, Intel and the BBC and most platforms still strip the manifest on upload. The developer-facing precedents the first draft leaned on — Kubernetes, Terraform, dbt, OpenTelemetry, MCP — adopted fast because the adopter was also the beneficiary, and each had a hyperscaler or a lab pushing it. A verification record is reader-facing: the builder pays, someone else benefits. That shape does not spread on its own.

So the plan has two layers with different clocks, and it is honest about both:

- **The company** (fundable on a three-year horizon): a hosted, model-neutral verification service sold to regulated buyers, whose deliverable is a signed record, priced per verified deliverable. It is the *auditor's tooling* — the Vanta-for-AI-outputs — not the auditor. It wins by being the thing compliance teams and AI platforms route through, and it is viable whether or not the standard spreads.
- **The standard** (a ten-year bet with a three-year checkpoint): the Conviction schema, given away, carried into a foundation, with a named platform co-sponsor and a regulatory hook. If it takes, the company is the reference verifier of a universal record. If it does not, the company is still a compliance business. The plan never lets the second outcome depend on the first.

Nova — the controller with your history — is the first and best customer of that layer, and the demo that keeps the schema honest. It is not the product.

---

## 2. Why this, and not the obvious alternatives

**Not the orchestrator.** Amazon (AgentCore), Google (ADK 2.0, Agent Engine), Microsoft (Agent Framework 1.0, Foundry), OpenAI (AgentKit) and Anthropic (Agent SDK, Managed Agents) each own a runtime; LangGraph and Temporal own the open graph-and-durability space; Stripe, Uber and Airbnb build their own blueprints (report 1, Appendix A). Five well-funded owners, no buyer who switches for a sixth.

**Not the assistant.** It competes with every lab's first-party assistant, which ships with the model, the distribution and the memory.

**Not the detector.** Google Check Grounding returns per-claim scores with byte offsets; Azure Groundedness detects and corrects; AWS charges $0.10 per thousand text units and ships formal automated-reasoning checks; Cleanlab, Vectara, Galileo and open models fill the rest. Zero moat. *Correction from the first draft:* Patronus did **not** leave the judge business — its June 2026 $50M round *added* simulation environments alongside evaluation ([TechCrunch](https://techcrunch.com/2026/06/25/patronus-ai-lands-50m-to-build-digital-worlds-that-stress-test-ai-agents/)). The point stands without the embellishment: the detector is crowded.

**Not a dashboard.** Braintrust ($800M valuation, February 2026), Arize, Galileo and LangSmith sell verification as a scorer inside a trace, to developers, priced as observability. Langfuse went to ClickHouse, Lakera to Check Point, Aporia to Coralogix. Dashboards get absorbed by whoever owns the logs.

**And a correction that cuts against the thesis, stated plainly.** The first draft claimed labs ship verification "as advice, not as a product." That was wrong. Anthropic's Claude Code documentation prescribes "a verification subagent … has a fresh model try to refute the result, so the agent doing the work isn't the one grading it" *and* ships `/code-review`, a `/goal` evaluator and Stop hooks as product features ([Claude Code docs](https://code.claude.com/docs/en/best-practices)). The labs are productising in-loop verification of their own models. What they are not doing, and are structurally unlikely to do, is (a) verify across families with published independence rules, (b) emit a signed, portable, reader-facing record, or (c) accept a third party's verdict inside their own surface. The opening is narrower than the first draft said; it is (a) and (b), sold to people who bear the cost of being wrong.

**On "neutrality," honestly.** The red-team is right that neutrality is not a capability; it is the absence of a conflict, and a cross-family verifier is reselling Gemini's verdict on Claude's output through a routing policy anyone can copy. What is *not* copyable in a thirty-line config is the accumulated, published, per-label error-rate history across millions of deliverables, the benchmark the market quotes, the independence rules that auditors have learned to ask for, and the absence of a model to favour. Neutrality is the prerequisite; the calibration record and the auditor relationships are the moat. Grade that honestly as "medium, slow" rather than "structural."

---

## 3. The product, stated plainly

**The Conviction record.** Per deliverable: claims with evidence pointers, a machine label for each (the eight from Nova v2 §7.4 — `checked`, `entailed@rate`, `corroborated`, `single-source`, `sample-agreed`, `unsupported`, `derived`, `conflicted`), the verifier's family, tier, version and independence attestation, per-criterion verdicts against the acceptance criteria, content-hashed snapshots, budget spent, and a detached signature. **Readers see three states, not eight:** `verified`, `unverified`, `disputed`. The eight live in the JSON for auditors and machines. The IBM study (n = 208) supports phrase-level highlighting that calibrates trust in both directions ([arXiv 2508.06846](https://arxiv.org/html/2508.06846v1)); it does not support an eight-term taxonomy for readers, and every content-label deployment in the wild (Meta's "Made with AI," rolled back within months in 2024; YouTube's disclosures; cookie banners) shows readers habituate to anything more complex than a traffic light.

**The Rail** (open, permissive licence). The deterministic runtime from Nova v2 §3 and §8. Shipped as a library plus two integrations that ride loops people already run: a Claude Code hook / subagent, and an MCP server so any MCP client can request verification of a deliverable. A LangGraph node follows. Open because the invariants should spread faster than the company can sell them, and because an open reference implementation is the price of admission to any standards conversation.

**The Verifier service** (hosted; the revenue). Cross-family verification with published independence rules (worker family ≠ verifier family ≠ escalation family; verifier sees pointers and snapshots, never worker prose; re-checks against snapshots, never live), a public benchmark with the service's own losses published, stamped error rates per label, and a signed record. The company never trains a frontier model.

**Liability, decided.** The company is the auditor's tooling, not the auditor. The record is *evidence for* a human attestation under Article 12, ISO 42001 or a SOC 2 AI criterion — not a substitute for one. That is the position Vanta and Drata occupy for SOC 2, it sells at compliance-software multiples, and it does not require a licence, an E&O policy sized to the customers' exposure, or a fight with the Big Four over turf the Big Four already own. The first draft wanted the auditor's moat with a tooling team; this draft picks the tooling business and lets the auditor relationships be the channel.

---

## 4. The regulatory clock, corrected to today

The first draft's forcing function was three weeks stale. As of today: the Digital Omnibus was politically agreed on 6 May 2026, confirmed by member states on 13 May, and **defers Annex III high-risk obligations to 2 December 2027** (Annex I embedded systems to 2 August 2028), with formal publication expected before 2 August 2026 ([Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/); [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-deadline-omnibus-20260/)). Two consequences:

- The Article 12 logging pull for high-risk systems arrives in **December 2027**, which is year two of this plan, not year one. That is where the compliance milestone belongs.
- **Article 50 transparency obligations did apply from 2 August 2026** — including the requirement that providers of systems generating synthetic content ensure outputs are marked in a machine-readable format and detectable as AI-generated, with a four-month grace for watermarking of existing systems ([Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)). That is a *provenance* requirement for text that C2PA does not serve, and it is live now. The Conviction record's signature and manifest satisfy it as a by-product. This is the year-one regulatory hook, and it is smaller but real.

NIST's agent interoperability profile remains due Q4 2026 and concerns attributable audit logs of agent *actions* ([CSA note](https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-initiative-2026040/)); it is a design input, not a mandate.

---

## 5. Unit economics, reconciled

The first draft claimed a verification charge "an order of magnitude below generation cost" at "above 70% margin," while Nova v2 §9 says verification costs roughly as much as the worker run. Both cannot be true. The reconciliation, using the design's own cost model:

| Tier | Generation (customer pays) | Verification cost to the service | Priced at | Margin |
|---|---|---|---|---|
| T1 lookup | ~40k billed-equiv. tokens | Snapshot re-check (code) + grounding ~15k + cross-family verifier ~15k ≈ 30k | ~$0.25–0.60 | thin; this is the commodity rung and is priced to be nearly free |
| T2 brief | ~360k | 3 verifier calls ~120k + grounding ~90k ≈ 210k | ~$3–8 | positive only with caching and small-model grounding; ~40–60% |
| T3 deep dive | ~2M | ~15 verifier calls ~600k + grounding ~450k ≈ 1M | ~$25–60 | 50–65% |

Tokens are billed-equivalent; prices assume 2026 list rates with cache reads at ~0.1×. The honest summary: verification at T2/T3 is *not* an order of magnitude cheaper than generation — it is roughly a third to a half of it — and the margin is compliance-software margin, not API-reseller margin. The value is not in being cheap; it is that the customer already paid for generation and is buying a record they can show someone. T1 is priced as a loss-leader on-ramp. Willingness to pay at these levels is the first thing the plan tests (§7).

---

## 6. The two clocks

### The company (three-year horizon, fundable)

**Year 3:** the default neutral verification service for regulated AI deliverables in EU high-risk deployers, US financial services, health systems and legal; a public benchmark the market quotes; per-label error-rate history nobody else has; records accepted as Article 12 evidence by at least two notified bodies and referenced in at least one Big Four AI-assurance methodology; per-deliverable revenue with volume tiers; gross margin in the 50–65% range at T2/T3.

**Year 2:** Annex III obligations land (December 2027) with the record already mapped to Article 12 categories and already in use by design partners; hosted Verifier GA; 50+ paying organisations; the benchmark in its second public round with third-party submissions; a LangGraph node and at least one platform that can *require* a record as a policy (AgentCore, Foundry or Agent Engine — whichever partner §6 below lands).

**Year 1:** the Rail open and used by people the company does not know; Nova emitting records on every deliverable; hosted Verifier in beta with five design partners chosen for regulatory exposure; the benchmark published with the service's own results, wins and losses; Article 50 marking as the live hook.

### The standard (ten-year horizon, three-year checkpoint)

**The mechanism, named** — the thing the first draft lacked. A reader-facing standard needs a platform sponsor who benefits from it without owning a model. The candidates are the Agentic AI Foundation's non-lab platinum members: Cloudflare (edge, no model, already the natural place to sign and serve a manifest), Bloomberg (regulated, data-provenance native), and the observability acquirers (Datadog, ClickHouse) who would rather standardise the record than lose it to a lab. The year-one target is one of these as co-sponsor of the schema inside the AAIF, with the OWASP Agent Observability Standard as the fallback home and the OpenTelemetry GenAI attributes (`gen_ai.verification.*`) as a 12–24-month SIG campaign, not a week-12 filing.

**Three-year checkpoint:** the schema has a second independent implementation and a foundation home, *or* the ubiquity bet is closed and the company continues as a compliance business. This is stated as a decision, not a hope.

**What "everyone has to use it" would actually look like in year ten:** a verification manifest travels with AI output the way DMARC now travels with bulk email — not because readers asked, but because a platform mandated it. The plan's job in years one to three is to be the reference implementation that exists when that mandate is written.

---

## 7. The first 180 days, cut to what five to seven people can do

**Days 1–30: the willingness-to-pay test, before any code.** Five regulated buyers Sam can actually reach (the plan should name them; the red-team is right that a bank does not sign with a six-week-old repo — the day-90 partner is someone already known). Show them a mocked T1 and T2 record at the §5 prices. Collect a signed LOI or a "no." If fewer than two say yes, the product is T1-only and the plan reverts to the compliance-tooling fallback from day 31.

**Days 1–90: two deliverables, not seven.**
1. The Rail core with the Claude Code hook, and Nova emitting a Conviction record on every deliverable. The schema ships as the README and the JSON the Rail emits, not as a standards document.
2. The benchmark harness with first public results for the four cloud grounding APIs and five open checkers on data the vendors cannot have trained on — which is the evaluation scientist's entire first quarter, scheduled as such.

**Days 90–180:** the MCP server; the first design partner instrumented with the design's §13 metrics and the first numbers published; the Article 12 and Article 50 mapping table published alongside the schema; the AAIF co-sponsor conversation opened with the benchmark and the live partner as the credentials; the OTel proposal drafted with a SIG champion identified, not filed cold.

**Team, corrected.** Runtime engineer (Rail); evaluation scientist (benchmark, error-rate stamping); **a cryptography/security engineer** — the signature and the independence attestation are the record's entire value and were missing from the first draft; a regulatory lead who has talked to a notified body, not just read Article 12; Sam running Nova on it daily and writing. DevRel comes at month six when there is something to evangelise. Standards engineer comes with the co-sponsor. **Budget line the first draft omitted:** cross-family verification at T2 volume for five partners plus a nine-system benchmark is a five-figure monthly API bill before revenue.

---

## 8. Moat, graded honestly

| Source | Grade | Why |
|---|---|---|
| Per-label error-rate history and the quoted benchmark | Medium, slow, real | Calibration data accumulates only with volume; nobody else is collecting it per label. |
| Auditor and notified-body acceptance of the record | Strong if won, time-boxed | The window is the Dec 2027 enforcement ramp; it is an argument to be won (open question 3), not a fact. |
| The schema, if it gets a foundation home and a second implementation | Strong if adopted, zero if not | The ten-year bet; never let the company depend on it. |
| Neutrality | Prerequisite, not moat | Copyable as a routing policy; matters only because it lets the three above exist. |
| The Rail's invariants | None, by design | A distribution vehicle. |

What the moat is *not*: the detector, the orchestrator, the UI, the models.

---

## 9. What would kill it, including what the first draft missed

- **Adoption floor for content-trust standards.** DKIM/DMARC and C2PA say a decade plus a mandate. *Tripwire:* no platform co-sponsor by month 18. *Response:* the standard bet closes at the three-year checkpoint; the company continues.
- **The Big Four and ISO 42001 own "independent verification."** *Tripwire:* a notified body declines to accept a machine-generated record as evidence without a human attestation. *Response:* already designed in — the record is evidence for the attestation; partner with the auditors rather than compete.
- **Label fatigue.** *Tripwire:* design-partner readers stop looking at the three states. *Response:* the record's value must hold for machines and auditors even when readers ignore it; price to the compliance buyer, not the reader.
- **A lab ships reader-facing labels on its own schema.** *Tripwire:* a lab-defined label vocabulary in a major assistant before the open schema has a second implementation. *Response:* superset plus translator; the cross-family record still has no lab equivalent.
- **An observability vendor ships a signed deliverable-level record first.** *Tripwire:* such a SKU from Braintrust or Arize. *Response:* they are not cross-family-neutral and their acquirers are not either; compete on the benchmark and offer them the schema.
- **Willingness to pay below cost at T2.** *Tripwire:* the day-30 test. *Response:* T1-only on-ramp plus compliance tooling.
- **Neutrality compromised by a distribution deal.** *Tripwire:* any term that restricts verifier family choice. *Response:* walk.
- **The one fatal risk:** the schema never gets a second implementation *and* regulated buyers will not pay per deliverable. Both tripwires fire → stop.

---

## 10. What I would not do

Raise on "the orchestration platform." Train a model. Build a console before the record has a second implementer. Price per seat or per trace. Keep the schema proprietary. Promise ubiquity on a three-year horizon — promise the reference implementation and the compliance business, and keep the ten-year bet alive in public. Call the layer "Nova"; Nova is Sam's controller and the best demo of it, and the layer needs a name an auditor, a regulator and a competitor can all say.

---

## 11. Open questions

1. Willingness to pay per verified deliverable at the §5 prices — unmeasured; days 1–30.
2. Whether notified bodies will accept a machine record as Article 12 evidence — an argument to be won by December 2027.
3. Whether the AAIF will take a non-lab-sponsored schema, or whether OWASP AOS is the realistic home.
4. Whether a platform will ever *mandate* a verification manifest on AI output the way Google and Yahoo mandated DMARC — the only known path to "everyone," and entirely outside the company's control.
5. How cross-family independence generalises to long-form deliverables (~2 effective votes is measured for classification judges, not reports).
6. Whether labs will accept a third-party verdict inside their surface, or whether the record only ever travels around them.
7. The ARR of every eval/observability incumbent is undisclosed; the funding signals are strong, the revenue reality unknown.

---

## Sources

Regulatory (fetched 22 Aug 2026): [Gibson Dunn — Omnibus agreement and dates](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/) · [CSA — deferred, not cancelled](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-deadline-omnibus-20260/) · [CSA — NIST agent standards initiative](https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-initiative-2026040/). Trust layer: [Anthropic Citations](https://claude.com/blog/introducing-citations-api) · [Google Check Grounding](https://docs.cloud.google.com/generative-ai-app-builder/docs/check-grounding) · [Azure Groundedness](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/groundedness) · [AWS Automated Reasoning checks](https://aws.amazon.com/about-aws/whats-new/2025/08/automated-reasoning-checks-amazon-bedrock-guardrails) · [Cleanlab TLM](https://help.cleanlab.ai/tlm/) · [Patronus Series B](https://techcrunch.com/2026/06/25/patronus-ai-lands-50m-to-build-digital-worlds-that-stress-test-ai-agents/) · [Parallel Basis](https://parallel.ai/blog/granular-basis-task-api) · [Braintrust Series B](https://siliconangle.com/2026/02/17/braintrust-lands-80m-series-b-funding-round-become-observability-layer-ai/) · [ClickHouse–Langfuse](https://www.webpronews.com/clickhouse-acquires-langfuse-raises-400m-at-15b-valuation-for-ai-push/) · [Claude Code verification guidance](https://code.claude.com/docs/en/best-practices) · [OTel GenAI status](https://dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet-heres-what-actually-shipped-in-2026-3mke) · [Agentic AI Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) · [OWASP AOS](https://aos.owasp.org/) · [C2PA / OpenAI provenance](https://help.openai.com/en/articles/8912793-provenance-signals-content-credentials-synthid-in-openai-generated-content). Buyer surveys (vendor-commissioned unless noted): [Gartner](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027) · [Forrester for Boomi](https://futurecio.tech/study-finds-86-of-enterprises-have-deployed-ai-agents-but-just-34-trust-them/) · [Deloitte](https://www.deloitte.com/us/en/about/press-room/deloitte-survey-examines-ai-readiness-agentic-ai-success.html) · [Teradata](https://www.teradata.com/insights/white-papers/why-agentic-ai-stalls-enterprise) · [McKinsey](https://mckinsey.com/capabilities/tech-and-ai/our-insights/tech-forward/state-of-ai-trust-in-2026-shifting-to-the-agentic-era) · [KPMG](https://kpmg.com/us/en/media/news/q2-ai-pulse-2026.html). HCI: [IBM phrase-level highlighting](https://arxiv.org/html/2508.06846v1) · [citation-trust summary](https://matthewfacciani.substack.com/p/does-it-matter-if-an-ai-chatbot-cites) · [Tow Center](https://www.niemanlab.org/2025/03/ai-search-engines-fail-to-produce-accurate-citations-in-over-60-of-tests-according-to-new-tow-center-study/). Orchestration landscape and design evidence: the three prior reports.
