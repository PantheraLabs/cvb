# CVB — Constraint-Violation Benchmark

**Do coding agents honor project constraints when they arrive as memory instead of orders?**

Teams record constraints once — "we standardized on httpx after requests
caused the March socket-exhaustion incident" — and expect every future AI
generation to honor them. In practice those constraints reach the model two
very different ways:

1. as **explicit instructions** pasted into a prompt, or
2. as **ambient memory context** injected by a memory layer, a CLAUDE.md
   file, or RAG.

Instruction-following benchmarks (IFEval, AgentIF) only measure the first.
CVB measures both, plus a no-context baseline, and reports the difference.

## Arms

| Arm | Context the model receives | What it measures |
|-----|---------------------------|------------------|
| `cold` | task only | baseline violation rate |
| `mandated` | task + constraints framed as explicit orders | instruction-following ceiling |
| `incentivized` | task + the same constraints embedded in an ambient project-memory narrative, never framed as orders | memory adherence |

**Headline metric — the gap:** `mandated strict accuracy − incentivized
strict accuracy`. How much adherence dies when rules live in memory instead
of orders.

Prompt templates are frozen strings in [`cvb/prompts.py`](cvb/prompts.py)
(`PROMPT_VERSION = "2.0"`). The incentivized narrative is built
deterministically from the scenario file — no LLM anywhere in scoring or
context construction. Scenario lint bans imperative wording ("must",
"required", "rule", "you should") from constraint text so the incentivized
arm stays genuinely non-directive.

## Scoring

- 35 scenarios, 7 categories x 5 (library-choice, security, encoding-io,
  style-architecture, error-handling, concurrency, logging-testing).
- Each scenario: a natural coding task that tempts the default violating
  behavior, plus 2-4 constraints. **Each constraint carries its own
  deterministic regex checks.**
- Reported per arm: **strict accuracy** (all constraints of a run honored)
  and **per-constraint accuracy** (IFEval-style).
- No LLM judge. Temperature 0. Runs are cheap and exactly reproducible.

## Run it

```bash
pip install -e .
export GROQ_API_KEY=...   # or any OpenAI-compatible endpoint via --base-url

python -m cvb.runner --scenarios scenarios --dry-run          # list matrix
python -m cvb.runner --scenarios scenarios --runs 3 \
    --json results/out.json                                   # ~945 calls
python -m cvb.report results/out.json --markdown results/out.md
```

Default models are probed from the live Groq catalog (first three available
of: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`,
`deepseek-r1-distill-llama-70b`, `qwen-2.5-72b-instruct`, `gemma2-9b-it`).
Override with `--models`, point anywhere OpenAI-compatible with
`--base-url` / `--api-key-env`.

## Results

_First full 3-model run pending — tables will land here with exact model
IDs, date, and committed raw JSON under `results/`._

## Honest limitations

- **Regex checks are conservative.** They catch the canonical violation,
  not every possible one. A pass means "no detected violation", not proof
  of compliance.
- **Baselines differ by model.** A stronger model violates less cold; the
  gap metric is within-model, which controls for this, but absolute rates
  are not comparable across models.
- **Weak models can fail checks for competence reasons** (broken code)
  rather than disobedience. Checks target the violating pattern, not code
  quality, and per-constraint accuracy limits the blast radius, but the
  confound does not fully vanish.
- **Scenario leakage:** public benchmarks enter training data. Scenarios
  are versioned and results date-stamped; treat future scores accordingly.
- Single-turn code generation only. No tool use, no retrieval — this
  isolates adherence from retrieval quality.

## Why this exists

- Conversational-recall benchmarks are the wrong yardstick for developer
  memory: an independent audit of LoCoMo found ~6.4% of its answer key
  wrong and its LLM judge accepting 63% of intentionally wrong answers.
- PROJECTMEM (arXiv 2606.12329) established the Memory-as-Governance
  framing — but ships no constraint-adherence evaluation. CVB fills that
  slot.
- Motivating product: [HCR](https://github.com/PantheraLabs/HybridCognitiveRuntime),
  a developer memory layer whose job is exactly the incentivized arm. The
  benchmark imports nothing from it and runs without it.

## Prompt changelog

- `2.0` (2026-07-29) — initial three-arm templates.

## License

MIT.
