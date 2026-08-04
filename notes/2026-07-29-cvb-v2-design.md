# CVB v2 — Constraint-Violation Benchmark, Design

Date: 2026-07-29. Status: approved-pending-review.

## What this measures

Coding agents receive project constraints two ways in practice: as explicit
instructions in a prompt, or as ambient memory context injected by a tool
(HCR, CLAUDE.md files, RAG). Instruction-following benchmarks (IFEval,
AgentIF) only measure the first. CVB v2 measures both and reports the gap.

**Headline metric: the Mandated→Incentivized adherence drop** — how much
constraint adherence decays when the same rules arrive as background memory
instead of direct orders.

## Arms (per scenario × model)

| Arm | Context delivered | Measures |
|-----|-------------------|----------|
| `cold` | task only | baseline violation rate |
| `mandated` | task + constraints framed as explicit orders ("You must follow these project rules: ...") | instruction-following ceiling |
| `incentivized` | task + same constraints embedded in an ambient project-memory narrative (preflight-style: "Project context: past incidents, recorded decisions..."), never framed as orders | memory-adherence — the gap nobody publishes |

Prompt templates are fixed and versioned in the repo. The incentivized
narrative is generated deterministically from the scenario's constraint list
by a template — no LLM in the loop.

## Scoring

- Each scenario has 2–4 constraints; **each constraint has its own
  deterministic check** (`regex_absent`, `regex_present`,
  `regex_absent_unless` — v1's check engine, extended per-constraint).
- Per-constraint YES/NO → IFEval-style metrics per arm:
  - **strict scenario accuracy**: all constraints honored
  - **per-constraint accuracy**: fraction of constraints honored
- No LLM judge. Runs are cheap and exactly reproducible. A pass means "no
  detected violation", stated honestly in the README.

## Scale

- **35 scenarios, 7 categories × 5**: library choice, security, encoding/IO,
  style/architecture, error handling, concurrency, logging/testing.
  10 ported from CVB v1 (multi-constraint upgraded), 25 new.
- **Models (default matrix, all Groq — no paid keys required):**
  `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, plus a third probed
  from the live Groq catalog (preference order: deepseek-r1-distill-llama-70b,
  qwen-2.5-72b, gemma2-9b-it). `--models` flag overrides; any
  OpenAI-compatible endpoint works via `--base-url`, so Anthropic/OpenAI arms
  can be added later without code change.
- Temperature 0, 3 runs per arm. Full default matrix ≈ 35 × 3 arms × 3
  models × 3 runs = 945 calls.

## Repo layout (PantheraLabs/cvb, MIT, zero HCR imports)

```
cvb/
  README.md            # method, results tables, honest limitations
  LICENSE              # MIT
  scenarios/           # 35 .json files, one per scenario (multi-constraint)
  cvb/
    runner.py          # arms, model calls, retries, JSON output
    checks.py          # deterministic check engine
    prompts.py         # fixed templates: cold / mandated / incentivized
    report.py          # aggregate tables (markdown + JSON)
  results/             # committed run outputs, one dir per model+date
  tests/               # check-engine unit tests, scenario lint (every
                       # scenario: valid checks, tempting task, no overlap)
```

HCR relationship: HCR is cited as the motivating product and one way to
deliver incentivized context in real use; the benchmark itself never imports
it. HCR's repo keeps a pointer doc. Installer scripts (former repo content)
live on `installer-archive` branch until week-3 launch folds them into the
product repo.

## Publication story (week 2 exit criteria)

1. Repo public with results tables for 3 Groq models.
2. README cites: LoCoMo audit (why conversational-recall benchmarks are the
   wrong yardstick), PROJECTMEM arxiv 2606.12329 (Memory-as-Governance framing,
   no constraint evaluation — the open slot CVB fills).
3. Every claim traceable to committed raw run JSON.

## Non-goals

- No retrieval-quality measurement (HCR's synthetic eval covers that).
- No agentic/tool-use scenarios in v2 — single-turn code generation only.
  (v3 candidate.)
- No LLM judge, no human eval.

## Risks

- Weak models may fail checks for competence reasons (broken code), not
  disobedience. Mitigation: checks target the violating pattern, not code
  quality; report per-constraint, not per-run.
- Groq catalog churn: runner probes availability at start, records exact
  model IDs in output JSON.
- Scenario leakage into future training data: version scenarios, date-stamp
  results, accept it (all public benchmarks share this).
