# Nova v2 Against the August 2026 AI App Landscape — Compatibility and the Path to It

**For:** Sam · **Status:** research + compatibility verdicts, fact-checked · **Date:** 23 August 2026
**Built on:** three research passes — consumer and workplace assistants and what third parties may plug into them; coding agents and agent platforms and where a verification step can hook in; and the protocol/API layer (MCP, A2A, each vendor's model API) that decides whether the Rail can drive workers and a cross-family verifier at all. Primary sources throughout; gaps flagged.

---

## 1. The verdict

**Compatible — with one hard boundary that decides the architecture.**

Everything Nova v2 needs *below* the user interface exists today: strict schema output, prefix caching, batch pricing and tool calling at every major vendor; cross-family model access under one key; signing primitives for the record; a stable agent-to-agent protocol that carries arbitrary metadata. The Rail, the stateless workers, the cross-family Verifier and the signed record are buildable now at the API layer, and none of the three big vendors' terms prohibit using one model to judge another's output (they prohibit training competitors and, at Google, caching grounded search results — a real constraint on the snapshot store, handled below).

What does **not** exist anywhere is a way for a third party to see or gate a chat assistant's *final answer before the user does*. ChatGPT's Apps SDK exposes tool inputs, tool outputs and widget APIs and nothing that touches the model's response; Claude.ai, Gemini, Copilot, Perplexity, Grok and Le Chat are the same. MCP's new 2026-07-28 revision moves the other way: server-initiated *sampling* (an MCP server borrowing the host's model) is deprecated under SEP-2577 — it keeps working for at least twelve months, but new implementations are told not to adopt it — which leaves a server that wants a model to bring its own provider keys. The only documented completion-blocking hooks in the industry are Claude Code's and Codex's `Stop`-family hooks, and those are agent-harness features, not chat-app features.

So the answer to "could my system be compatible" splits cleanly:

- **Nova as the controller of its own loop** — calling models through APIs, verifying with a different family, signing the record — is compatible with every model vendor, every aggregator, every agent runtime and every coding agent that has a headless mode. That is the system as designed.
- **Nova inside someone else's chat app** — owning the user's conversation in ChatGPT, Claude.ai or Gemini and verifying what those apps say — is not possible and will not become possible by building harder. In those apps Nova can be a tool the assistant calls and a source of verified deliverables the assistant hands back; it cannot be the gate.

The path to full compatibility (§6) is therefore not one integration but a ladder: run Nova on APIs first, hook the two coding agents that expose blocking hooks, become a required check wherever output ends in a pull request, expose the Rail as an MCP server so every chat app can *call* it, expose it as an A2A agent so every enterprise platform can *route* to it, and then lobby for the one host feature that would close the boundary.

---

## 2. The landscape in three layers

The apps sort into three layers that behave differently for Nova, and it matters which layer a given app is in.

**Layer 1 — assistants you talk to** (ChatGPT, Claude.ai/Cowork, Gemini app and Spark, Microsoft Copilot, Perplexity, Grok, Le Chat, Meta AI, DeepSeek, Kimi, Qwen). Closed loops. They let third parties in only through MCP tools and, in some, app widgets; they never let a third party intercept the answer. The notable August 2026 facts: ChatGPT's Atlas browser was discontinued on 9 August and its agentic work folded into the desktop app and a Chrome extension; OpenAI replaced its App Directory with a Plugin Directory on 9 July; Claude's Cowork reached the Chrome side panel on 12 August; Gemini Spark (the 24/7 personal agent, AI Ultra, US) gained custom MCP in June; Perplexity's "Computer" is itself a multi-model orchestrator with a "Check Sources" step — a Nova-shaped competitor inside a Layer-1 app.

**Layer 2 — agents and platforms that do work** (Claude Code and the Agent SDK, Codex, Cursor, Copilot cloud agent, Antigravity CLI, Kiro, Devin, OpenHands, Aider; and the runtimes — Anthropic Managed Agents, OpenAI Agents SDK, Google ADK 2.x and Agent Engine, Microsoft Agent Framework 1.0 and Foundry Agent Service, AWS AgentCore, LangGraph/LangSmith, CrewAI, Temporal + Pydantic AI, Inngest, Vercel AI SDK 7, Cloudflare Agents, n8n, Agentforce). Open loops. Nearly all have headless modes so Nova can call them as workers; most runtimes let you insert a deterministic node between agent output and delivery; many are multi-vendor. Two movements worth noting: OpenAI deprecated AgentKit's Agent Builder and hosted Evals (shutdown 30 November 2026) while keeping the code-first Agents SDK, and Google transitioned the consumer Gemini CLI to Antigravity CLI on 18 June.

**Layer 3 — protocols and APIs** (MCP 2025-11-25 and 2026-07-28; A2A v1.0, with 150+ organisations as of April 2026 and native support in Azure Foundry, Copilot Studio, Bedrock AgentCore and Google Cloud; the Anthropic, OpenAI and Google model APIs; aggregators; Sigstore, C2PA 2.4, W3C Verifiable Credentials 2.0). This is the layer Nova actually runs on, and it is the most compatible of the three.

---

## 3. Compatibility matrix — assistants and workplace apps

Verdict key: **Native** = Nova can own the loop; **Host** = Nova can be the agent host that calls workers and verifies before writing; **Tool** = the app's assistant can call Nova as an MCP tool and hand back the deliverable plus record, but the app's own prose is not gated; **Deliver** = files only; **No** = no third-party surface.

| App | Third-party surface (Aug 2026) | MCP client | Pre-display hook | Attach deliverable + record | Memory exportable to seed Nova | Verdict |
|---|---|---|---|---|---|---|
| ChatGPT | Apps SDK (MCP + widgets), Plugins, Developer mode (write actions Business/Enterprise/Edu; Pro read-only; web only; Agent mode cannot use custom apps) | Yes | No — apps see tool input/output only | Yes — tool results return file objects; widgets can upload to the file library | Chat export ZIP only; no memory import/export | **Tool** |
| Claude.ai / Cowork / Chrome panel | Custom remote MCP (user-added, no review), Claude Apps, Skills, Projects | Yes | No | Yes — MCP resources, Apps UI, Cowork writes files | **Yes, official** (view/export/import; labelled experimental) | **Tool** (best memory seed) |
| Claude Code / Agent SDK | 31-event hooks incl. blocking `Stop`, `SubagentStop`, `TaskCompleted`; Dynamic Workflows; plugins; MCP in/out; schema outputs | Client + server | **Yes — blocking** | Yes (files) | n/a | **Native** (API keys only; Anthropic's ban on Free/Pro/Max OAuth tokens in other harnesses explicitly names the Agent SDK) |
| Gemini app | Gems, Workspace; custom MCP only in **Spark** (AI Ultra, US, personal account, English, manual confirm on writes) | Spark only | No | Limited | Import yes (from ChatGPT/Claude); export via Takeout/prompt | **Tool** (Spark) / Deliver |
| Microsoft Copilot (consumer) | Six fixed connectors, export to Office formats | No | No | Export files | No | **No** |
| Microsoft 365 Copilot | Declarative agents (MCP tools), Copilot Studio (MCP client, computer-use, evaluations GA), Work IQ APIs GA 16 Jun 2026 (Chat via A2A/REST; Context and Tools via MCP) | Yes | No in chat; **yes inside your own Studio agent** | Yes | Tenant-level only | **Host** (enterprise) |
| Perplexity | Bring-Your-Own-Connector MCP, Projects, Computer, API platform | Yes | No | Yes (workspace files) | Not found | **Tool** — note Computer is a competing orchestrator |
| Grok | 20+ connectors, BYO MCP, Skills | Yes | No | Limited | Not found | **Tool** |
| Le Chat (Mistral) | Custom MCP connectors, Memories | Yes | No | Limited | Not found | **Tool** (2026 status partly unverified) |
| Meta AI · DeepSeek app · Qwen app · Kimi | No official third-party surface (Qwen partner-only; Kimi Work is a desktop agent with no documented MCP) | No | No | Kimi: local files | No | **No** / Deliver |
| Notion | Custom Agents (Notion 3.3) can call custom MCP servers (Business/Enterprise, admin toggle); Notion MCP server | Client + server | **Yes, inside your agent's run** | Yes | Workspace export | **Host** |
| Slack | Agent Kit, Slack MCP server, Real-time Search API, Slackbot as MCP client | Client + server | **Yes, inside your agent** | Yes (Block Kit, files) | Per plan | **Host** |
| Google Workspace | Workspace MCP server (preview), Studio skills, Apps Script | Server | No | Yes (Drive) | Takeout | Deliver |
| Salesforce Agentforce / Agent Fabric | Native MCP client, registry, A2A, Agent Script deterministic control, AI Gateway governance | Client + server | Yes, inside your agent | Yes | Org data | **Host** (enterprise) |
| ServiceNow | MCP server GA 5 May 2026 via Action Fabric | Server | n/a | Yes (records) | Org data | Tool |
| Atlassian Rovo · Zoom · Canva/Adobe | Curated MCP agents / A2A starting / MCP servers | Curated | No | Yes | Org data | Deliver |
| Zapier · n8n | Zapier MCP (9,000 apps); n8n native MCP client nodes, Guardrails node, OTel | n8n: client + server | **n8n: yes, you own the flow** | Yes | n/a | **Host** (n8n) / Tool (Zapier) |

**The four most compatible places for the personal-controller use case**, in order: Claude Code / Agent SDK on API keys (the only surface with a completion-blocking hook, plus workflows and file outputs); Notion Custom Agents (your agent runs, verifies, then writes); Slack Agent Kit (same, with Block Kit to render the record); Microsoft 365 via Copilot Studio and Work IQ (enterprise, but an external controller can legitimately drive Copilot). ChatGPT is the largest audience and has the cleanest file-attachment contract, but it is strictly deliver-only.

**The "route everything through Nova" question.** Seeding Nova with your history is possible now — Claude exports memory officially, Gemini imports chats and memory, ChatGPT gives a full export ZIP — but every export is free text with no machine-readable schema, so Nova needs its own normaliser. Continuously driving a subscription app from an external controller is mostly blocked by terms: Anthropic explicitly bans using Free/Pro/Max OAuth tokens in any other harness (API keys are the sanctioned path); OpenAI bans bypassing rate limits and safety measures. The compatible shape is Nova on APIs, with the consumer apps as delivery surfaces it reaches through MCP.

---

## 4. Compatibility matrix — coding agents and agent platforms

| Platform | Nova as orchestrator (calls it as a worker) | Verification step before delivery | Multi-vendor models | Structured output / artifact | OTel | Verdict |
|---|---|---|---|---|---|---|
| Claude Code / Agent SDK | Yes (`claude -p`, SDK `query()`, workflows with JSON schema) | **Yes — blocking hooks** | No (Claude via Anthropic, Bedrock, Vertex, Foundry) | Yes | Not first-party | **Top pick** |
| Codex CLI / cloud | Yes (`codex exec`, SDK) | **Yes — blocking `Stop`, `PostToolUse`** | No | Partial | No | Strong |
| Cursor Cloud Agents | Yes (REST v1, model picker, artifacts endpoint) | No — `stop` hook is non-blocking; gate at the PR | Yes | Artifacts API | No | Worker; gate at PR |
| GitHub Copilot cloud agent | Yes (agent-tasks REST, May–Jun 2026; Claude or GPT) | No hooks; poll task state; gate at PR | Yes | PR | No | Worker; gate at PR |
| Antigravity CLI (ex-Gemini CLI) | Likely (headless) | Hooks exist; blocking semantics unverified | No | Unknown | No | Verify docs first |
| AWS Kiro | Yes (headless) | Weak — Agent Stop non-blocking | No | No JSON mode | No | Medium; specs are a natural brief format |
| Devin (API v3) | Yes (sessions + webhooks; "Fusion" multi-model) | No in-session; gate at PR | Yes | Session JSON | No | Worker |
| OpenHands SDK (MIT) | Yes — and the loop is open source, so the Rail can sit inside it | **Yes** | Yes (LiteLLM) | Yes | Unverified | **Top pick for a fully controlled worker** |
| Aider | Yes (CLI) | No; verify the diff | Yes | No | No | Cheap worker |
| Replit Agent 4 | No public API | Built-in human approve only | — | No | No | Skip |
| OpenAI Agents SDK | Yes | Yes (output guardrails run after the agent, tripwire exceptions) | Yes (LiteLLM) | Typed `final_output` | Tracing exporters | Good — avoid the deprecated Agent Builder |
| Anthropic Managed Agents | Yes | Yes (hooks, approvals) | No | Yes | Gap | Good |
| Google ADK 2.x / Agent Engine | Yes | Yes (graph node, after-agent callback) | Yes (LiteLLM wrapper) | Yes | Yes | Good |
| Microsoft Agent Framework 1.0 / Foundry / Copilot Studio | Yes | Yes (middleware, approval actions) | Yes (GPT, Claude, Mistral, DeepSeek) | Yes | Yes | Good |
| AWS Bedrock AgentCore | Yes | **Yes — Policy/Gateway interceptors and custom Lambda evaluators, outside the model** | Yes (Gateway inference targets; Harness via LiteLLM) | Yes (Memory metadata) | Yes (native) | **Top pick for enterprise** |
| LangGraph 1.x / LangSmith | Yes | Yes (node + `interrupt` + middleware; Guard policies Aug 2026) | Yes | Yes | Yes | **Top pick** |
| Temporal + Pydantic AI | Yes — the Rail *is* a workflow; workers are activities | Yes (verification activity) | Yes | Yes | Yes (Logfire/OTel) | **Top pick — architectural twin of the Rail** |
| CrewAI AMP · Inngest · Vercel AI SDK 7 · Cloudflare Agents · n8n | Yes | Yes (task guardrail / step / workflow step / Guardrails node) | Yes | Yes | Mostly | Good |
| Dify · Flowise | Partial | HITL node | Yes | Partial | Dify yes | Low |
| Salesforce Agentforce / Agent Fabric | Yes (A2A/MCP registration) | Yes (Agent Script step) | Yes | Yes | Proprietary | Enterprise |
| GitHub Checks · GitLab status checks | — | **Yes — a required check** | — | Annotations + Sigstore attestations | — | **Delivery target #1** |
| Desktop/computer-use agents (Cowork, ChatGPT agent, Spark, Windows Agent Runtime, Manus) | OpenAI CUA and Copilot Studio CUA only | Human approval only; no programmatic hook | Mixed | No | No | Later |

---

## 5. What blocks full compatibility, precisely

1. **No pre-display interception in any chat app, and MCP is moving away from it.** MCP's flow is request → tool result → "client processes result"; there is no post-response notification in 2025-11-25 or 2026-07-28, and sampling is deprecated in the new revision. *Consequence:* the Rail must hold its own model keys and be its own controller; in chat apps it is a tool.
2. **Google's grounding terms forbid caching, analysing or training on Grounded Results** (terms updated 28 April 2026; limited storage for display and chat history is permitted; grounding prompts and outputs retained 30 days). *Consequence:* the snapshot store must be fed by Nova's own fetcher or URL-context, never by Gemini Search Grounding output.
3. **Anthropic Citations and structured outputs are mutually exclusive** (a 400 error). *Consequence:* the grounding pass on Claude is two calls — citations first, schema second — or runs on OpenAI or Google, where annotations and schema coexist.
4. **No single hyperscaler hosts all three closed families.** Bedrock has Anthropic + OpenAI (GPT-5.x) but not Gemini; Foundry has OpenAI + Anthropic; Vertex has Google + Anthropic + open weights. Cloudflare AI Gateway and OpenRouter give one key across all three at ~5% on credits, with zero-data-retention routing for OpenAI and Anthropic only. *Consequence:* cross-family verification is practical; verifier *identity* through a gateway is only as trustworthy as the gateway's response headers, so the record must pin provider, model id and response id.
5. **Schema enforcement is uneven at the small tier.** DeepSeek has JSON mode but no JSON-schema; many small open models emit invalid JSON; Gemini's Interactions API (GA June 2026, now recommended) has no batch and only implicit caching. *Consequence:* the Rail validates every worker return regardless of vendor; batch verification on Google goes through the legacy `generateContent` path.
6. **Blocking hooks exist only in Claude Code and Codex.** Cursor's `stop`, Kiro's Agent Stop and (unverified) Amp's `agent.end` are non-blocking; Copilot cloud agent, Devin and Replit have no in-session hook. *Consequence:* for every agent whose output ends in a pull request, the gate is a required check, not a hook.
7. **Subscription-token harnesses are banned.** Nova on Claude must run on API keys; running Nova "on top of" a Pro/Max login is a terms violation.
8. **Memory has no schema.** Every export is prose.

---

## 6. How to get there — the compatibility ladder

Ordered so that each rung works on its own and widens reach. Nothing on rungs 0–4 needs a vendor to change anything.

**Rung 0 — Run Nova as its own controller on vendor APIs.** Keys from at least two families (three for a true escalation family, or Cloudflare AI Gateway / OpenRouter for one key across all three). Strict-schema briefs at Anthropic, OpenAI, Google, Mistral, xAI; validate and retry everywhere. Prefix-cache the fixed brief sections above the largest vendor minimum (4,096 tokens for Haiku 4.5 and Gemini 3.x implicit caching). Evidence snapshots from Nova's own fetcher. Grounding on Rail-supplied documents, not vendor web search. Sign the record as an in-toto statement in a DSSE envelope via Sigstore, keyless; optionally mirror its hash into a C2PA 2.4 assertion embedded in the PDF, DOCX or HTML deliverable so the file is self-describing. Seed Nova's history from the Claude memory export and the ChatGPT data export through a normaliser. *This rung is the system as designed; it is buildable today.*

**Rung 1 — Hook the two coding agents that can be gated, and become a required check everywhere else.** Ship a Claude Code plugin whose `SubagentStop` and `TaskCompleted` hooks run the Rail's evidence re-check and refuse completion on an unmet load-bearing criterion, with a saved Dynamic Workflow that calls the Verifier via MCP; mirror it on Codex `Stop` hooks. Build the "Verified by Nova" GitHub App: it posts a check run with annotations and a Sigstore attestation, and repository rulesets make it required — this covers Copilot cloud agent, Cursor, Devin, Codex cloud and GitHub's own Agentic Workflows with no cooperation from any of them. Mirror on GitLab external status checks. *Reach: every coding agent in the table.*

**Rung 2 — Expose the Rail as an MCP server.** One server, three tools (`verify_deliverable`, `research_with_record`, `extract_with_record`), returning `structuredContent` plus a `resource_link` to the deliverable and the signed record, with two format-faithful examples in the tool description. That single artifact reaches ChatGPT (Developer mode and, after review, the Plugin Directory — return file objects), Claude.ai and Cowork (custom connector, no review), Gemini Spark, Perplexity, Grok, Le Chat, Cursor, VS Code and Copilot Studio. Nova is a tool there, not a gate — say so in the record's `scope` field so nobody mistakes a verified *attachment* for a verified *conversation*. *Reach: every Layer-1 app with an MCP client.*

**Rung 3 — Become a host where hosting is allowed.** Notion Custom Agents and Slack Agent Kit let your agent run, verify and *then* write; Microsoft 365 via Copilot Studio and Work IQ lets an external controller drive Copilot inside a tenant; n8n's Guardrails node and HTTP node make a "Nova Verify" step trivial. On these, Nova owns the loop and the record gates the write. *Reach: the workplace.*

**Rung 4 — Expose the Rail as an A2A agent.** A2A v1.0 artifacts carry arbitrary `metadata` (any JSON), so the full verification record rides natively; signed Agent Cards give verifier identity. Deploy on Bedrock AgentCore Runtime and Azure Foundry, both of which speak A2A, and register in Agentforce's Agent Fabric. For the substrate, Temporal + Pydantic AI is the architectural twin of the Rail (workers as activities, a verification activity before delivery, multi-provider models, Logfire/OTel); LangGraph is the alternative. AgentCore Policy is where the verification becomes enforceable *outside* any agent framework. *Reach: every enterprise platform.*

**Rung 5 — The vendor features that would close the boundary, and what to ask for.** A blocking `stop` with a JSON decision in Cursor, Kiro and Amp (Claude Code and Codex already have it). A pre-PR "verification webhook" that holds a cloud agent's PR in draft until an external verdict (Copilot, Devin). A named in-toto predicate for agent-authored change surfaced in PR UI and requirable by ruleset (GitHub). Native OpenTelemetry export with trace-id passthrough in the Claude Agent SDK, Codex and Cursor. An MCP post-response notification — the one feature that would let a third party gate a chat answer, and the one the protocol is currently moving away from; the realistic ask is a host-side "verified attachment" rendering convention rather than a gate. A programmatic approval API on computer-use agents (Copilot Studio's CUA partly has one).

---

## 7. What this changes in the design

Three adjustments to Nova v2, all small.

- The snapshot store's fetcher is Nova's own, and Gemini Search Grounding output is never evidence (terms). URL-context and Rail-supplied documents only.
- The grounding pass is vendor-aware: two calls on Claude, one on OpenAI or Google.
- The record gains two fields: `scope` (`loop` when Nova owned the run; `attachment` when Nova was a tool inside someone else's app) and `verifier_route` (provider, gateway, model id, response id) so a record produced through an aggregator is still attributable.

And one confirmation: the design's insistence that Nova hold its own keys and be its own controller — which the first report treated as a choice — is the direction the protocols are moving. MCP 2026-07-28 did not remove sampling overnight, but it told new implementations not to rely on it.

---

## 8. Gaps

Antigravity CLI hook semantics and Jules API status are unverified from primary docs. Two dated claims were not re-checked in the final audit and rest on the research pass alone: Bedrock hosting proprietary GPT-5.x, and Cowork's Chrome side panel on 12 August 2026. The AgentKit deprecation is cited to a secondary source. Amp's `agent.end` blocking behaviour, Copilot cloud-agent completion webhooks and Bugbot merge-blocking are undocumented. Meta AI, Mistral Le Chat's 2026 changes, Kimi Work, Manus and Genspark rest on secondary sources. OpenRouter's zero-retention specifics and the Cohere structured-output status were not re-verified. Gemini consumer-app MCP outside Spark is inferred from absence. The MCP tasks extension's adoption by hosts is undocumented. c2pa-rs writer support for OOXML and HTML should be confirmed before committing to embedded manifests.

---

## Sources

Protocols and APIs: [MCP 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/) · [MCP 2025-11-25 changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog) · [MCP tools spec](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) · [A2A v1.0 (Linux Foundation)](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year) · [A2A spec](https://a2a-protocol.org/latest/specification/) · [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) · [Anthropic caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) · [Anthropic citations](https://platform.claude.com/docs/en/build-with-claude/citations) · [Anthropic commercial terms](https://www.anthropic.com/legal/commercial-terms) · [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) · [OpenAI caching](https://developers.openai.com/api/docs/guides/prompt-caching) · [OpenAI terms](https://openai.com/policies/terms-of-use/) · [Gemini Interactions API](https://ai.google.dev/gemini-api/docs/interactions-overview) · [Gemini grounding](https://ai.google.dev/gemini-api/docs/google-search) · [Gemini terms](https://ai.google.dev/gemini-api/terms) · [Bedrock OpenAI models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-openai.html) · [Cloudflare AI Gateway unified billing](https://developers.cloudflare.com/ai-gateway/features/unified-billing/) · [Sigstore attestations](https://docs.sigstore.dev/cosign/verifying/attestation/) · [C2PA 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html) · [W3C VC 2.0](https://www.w3.org/press-releases/2025/verifiable-credentials-2-0/).
Assistants: [OpenAI Apps SDK reference](https://developers.openai.com/apps-sdk/reference) · [ChatGPT Developer mode](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt) · [App submission guidelines](https://developers.openai.com/apps-sdk/app-submission-guidelines) · [Evolving Atlas](https://help.openai.com/en/articles/20001371-evolving-atlas-into-chatgpt-for-browser-based-agentic-work) · [ChatGPT release notes](https://help.openai.com/en/articles/6825453-chatgpt-release-notes) · [Claude connectors](https://claude.com/docs/connectors/building) · [Claude memory export](https://support.claude.com/en/articles/12123587-import-and-export-your-memory-from-claude) · [Cowork in Chrome](https://claude.com/blog/cowork-chrome-side-panel) · [Anthropic third-party harness ban (The Register)](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/) · [Gemini Spark MCP](https://support.google.com/gemini/answer/17209137?hl=en&co=GENIE.Platform%3DDesktop) · [Gemini Spark updates](https://blog.google/innovation-and-ai/products/gemini-app/gemini-spark-updates-june-2026/) · [Gemini import (9to5Google)](https://9to5google.com/2026/03/26/gemini-import/) · [Work IQ APIs](https://www.microsoft.com/en-us/microsoft-365/blog/2026/06/02/announcing-the-new-work-iq-apis/) · [M365 publish](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/publish) · [Notion custom agents MCP](https://www.notion.com/help/mcp-connections-for-custom-agents) · [Slack MCP](https://docs.slack.dev/changelog/2026/02/17/slack-mcp/) · [Workspace at Next 2026](https://workspace.google.com/blog/product-announcements/10-more-announcements-workspace-at-next-2026) · [Agentforce MCP](https://www.salesforce.com/agentforce/mcp-support/) · [ServiceNow MCP](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-opens-its-full-system-of-action-to-every-AI-Agent-in-the-enterprise/default.aspx) · [Rovo third-party agents](https://support.atlassian.com/rovo/docs/out-of-the-box-third-party-mcp-agents/).
Agents and platforms: [Claude Code hooks](https://code.claude.com/docs/en/hooks) · [Dynamic Workflows](https://code.claude.com/docs/en/workflows) · [Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks) · [Codex hooks](https://learn.chatgpt.com/docs/hooks) · [Cursor hooks](https://cursor.com/docs/hooks) · [Cursor Cloud Agents API](https://cursor.com/docs/cloud-agent/api/endpoints) · [Copilot agent tasks API](https://docs.github.com/en/rest/agent-tasks/agent-tasks) · [GitHub Agentic Workflows](https://github.blog/changelog/2026-06-11-github-agentic-workflows-is-now-in-public-preview/) · [Antigravity CLI transition](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) · [Kiro hooks](https://kiro.dev/docs/hooks/types/) · [Devin release notes](https://docs.devin.ai/release-notes/overview) · [OpenHands SDK](https://docs.openhands.dev/sdk) · [OpenAI Agents SDK guardrails](https://openai.github.io/openai-agents-python/guardrails/) · [AgentKit deprecation](https://mcp.directory/blog/openai-agentkit-deprecation-2026) · [Managed Agents](https://anthropic.com/engineering/managed-agents) · [ADK 2.0](https://adk.dev/2.0/) · [Agent Framework at Build 2026](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-at-build-2026-announce/) · [Foundry Agent Service GA](https://devblogs.microsoft.com/foundry/foundry-agent-service-ga/) · [Copilot Studio what's new](https://learn.microsoft.com/en-us/microsoft-copilot-studio/whats-new) · [AgentCore release notes](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html) · [LangSmith changelog](https://docs.langchain.com/langsmith/changelog) · [Pydantic AI + Temporal](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/) · [n8n Guardrails](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.guardrails) · [GitHub check runs](https://docs.github.com/en/rest/checks/runs) · [GitLab status checks](https://docs.gitlab.com/user/project/merge_requests/status_checks/) · [DevOps.com on agent change controls](https://devops.com/the-agent-proposes-the-pipeline-disposes-controls-for-ai-authored-change/).
