# Echo Interactions

Standalone **messages → interactions** research prototype for Echo Guard.

## Scope

**Only semantic interaction mapping.** No safety taxonomy, risk detection, specialists, alerts, family accounts, Baileys transport, or integration with echo-v2. The input is a provider-neutral batch of messages, and the output is interaction membership backed by original message IDs.

- An LLM groups interleaved conversations, including ordinary topics.
- A deterministic resolver assigns stable interaction IDs when the evidence overlaps exactly one existing interaction.
- Uncertain links are explicitly unresolved; there is no forced merge based on time or topic.
- The mapper cannot invent interaction IDs. The resolver rejects unknown evidence IDs and unaccounted-for messages.
- A message can belong to multiple interactions when it genuinely bridges two discussions.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,llm]'
python -m pytest -q
echo-engine examples/interleaved_he.json
```

The CLI loads `.env` automatically with `python-dotenv` and displays a human-readable Rich table by default. Hebrew text is right-aligned inside the table while the table structure remains left-to-right for stable IDs and message IDs. Each successful run also writes a Markdown report to `runs/<guid>/result.md`; use `--runs-dir PATH` to change the report root. Use `--json` for machine-readable stdout while the report path is printed to stderr. `LLM_MODEL_NAME` supplies the model when `--model` is omitted, with `gpt-4.1-mini` as the fallback; pass `--model MODEL_NAME` to override it for one run. Environment variables already exported in the shell take precedence over `.env`. The included in-memory store provides stable IDs **only within one process**. The CLI runs one batch and cannot establish durable continuity between invocations; do not describe its IDs as persistent. This is intentionally not yet connected to live ingestion.

## Planned next experiments

1. Human-labeled interleaved group conversations: precision/recall of message-to-thread assignments and unassigned rate.
2. Feed incremental overlapping windows, including reply chains, and evaluate identity stability.
3. Add an explicit candidate-matching step for genuine continuations with zero repeated evidence.
4. Implement PostgreSQL storage and per-chat transaction/locking for concurrent workers.
5. Add a timeline visualization for manual corrections before any risk engine consumes the mappings.

## Important limitations

- Repeated semantic snapshots may split one thread when they cite no shared messages; this is conservative rather than silently merging.
- If a single snapshot attempts to split a previously stored thread, the resolver flags it as unresolved instead of rewriting history.
- Real workloads require pagination, retention policy, auth/privacy boundaries, and reconciliation of late/out-of-order messages.
- Text may be sensitive child data: do not log full prompts or outputs in production.
- No risk or safety inference is performed by this package.
