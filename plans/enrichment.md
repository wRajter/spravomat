# Plan — LLM enrichment (GeminiEnricher)

> Concrete LLM provider behind the Enricher interface in `presentation`.
> Not a new component — fills the enrichment slot presentation left open.
> Decided 2026-07-17 after a 3-model comparison test.

## Decision — provider
Gemini 3.1 Flash-Lite. Chosen from a comparison test (Gemini vs GPT-4.1 mini vs
Claude Haiku 4.5) on real clusters:
- Best Slovak quality for a native reader — informative but not dry.
- Faithful — no hallucination (Haiku invented "finále" instead of the correct
  "semifinále"; Gemini stayed accurate).
- Most stable across repeated runs (matters — no cache, titles must not swing).
- Cost was negligible for all (~cents/month at our volume), so quality decided.

## Scope
Add `GeminiEnricher(Enricher)` as the DEFAULT enricher. Existing
`KeywordEnricher` stays as the FALLBACK. Runs every `process` cycle (3x/day) for
the top N cards. No cache — recomputed each run (accepted tradeoff; stable story
identity is a separate parked task).

## Behavior
1. Per cluster: call Gemini with the tuned Slovak prompt (temperature 0.3), ask
   for {"title", "bullets"} JSON.
2. Retry on failure (429/529/timeout/network): 2–3 attempts, short backoff.
3. Parse JSON safely — strip markdown fences, tolerate surrounding text. If it
   can't parse into {title, bullets}, treat as failure.
4. On failure after retries (or unparseable): fall back to keyword title + empty
   bullets FOR THAT CARD ONLY. One failed card must not abort the run; other
   cards keep their LLM output. Partial failure is fine.
5. Missing GEMINI_API_KEY: degrade the whole run to KeywordEnricher. App must
   work without an LLM (like v1). Never crash on a missing key.

## Config
- `presentation/config.py`: model = "gemini-3.1-flash-lite", temperature = 0.3,
  retry count. 
- API key `GEMINI_API_KEY` from `.env` (already present from the test).

## The prompt (Slovak — from the comparison test)
[paste the tuned prompt]

## Parked
- Second LLM provider (OpenAI) as a middle fallback tier (LLM -> LLM -> keyword).
  The Enricher ABC leaves this open. Add later ONLY if Gemini proves to fail
  often in production — decide with real evidence, not preventively.

---

# Claude's review (2026-07-17)

Overall: strong, complete plan. The two-level fallback (run-level degrade if no
key; card-level fallback on per-cluster failure), retry-on-transient,
no-crash-on-missing-key, and keeping the OpenAI tier parked are all right. The
default/fallback split, no-cache, top-N-per-run, and the ABC leaving OpenAI open
need no changes. Feedback below is mechanics + one gap. Answer inline (`A:`).

## Questions I need you to answer

### Q1 — the prompt (didn't paste; line 40 is a placeholder)
The decision was made ON the comparison-test prompt, so use that exact
`PROMPT_TEMPLATE` from `tests/enrichment_comparison.py` verbatim (title <=8
words + 3 bullets <=12 words, JSON out). Confirm — and where does it live?
  (a) in `enrichment.py` next to GeminiEnricher (prompt + JSON parsing are one
      unit) — my lean
  (b) in `presentation/config.py` (treat as a tunable knob)
A: Neither (a) nor (b) — put the prompt in its OWN file:
presentation/prompts.py. Reasoning: config is for short knobs (model,
temperature, retries); a long multi-line Slovak prompt would bloat it and hurt
readability. And the prompt is logic-adjacent but not logic, so it shouldn't
clutter enrichment.py either. A dedicated prompts.py keeps three clean layers:
enrichment.py (logic), prompts.py (the prompt text), config.py (knobs).
enrichment.py imports the prompt from prompts.py — the prompt/parser link stays
clear (same component, adjacent files), the text just has its own home. Use the
exact PROMPT_TEMPLATE from the comparison test, verbatim.

### Q2 — how the enricher is selected
Runner currently hardcodes `KeywordEnricher()`. Add a factory in
`enrichment.py`: `get_enricher()` -> `GeminiEnricher()` if `GEMINI_API_KEY` set,
else `KeywordEnricher()`. Runner calls `get_enricher()`. Selection logic stays
with the enrichers; runner stays thin. Confirm.
A: Confirmed. get_enricher() factory in enrichment.py: GeminiEnricher if
GEMINI_API_KEY set, else KeywordEnricher. Runner calls get_enricher() and stays
thin — selection logic lives with the enrichers.

### Q3 — per-card fallback = composition
`GeminiEnricher` HOLDS a `KeywordEnricher` and delegates to it when a single
cluster fails after retries (keyword title + empty bullets, that card only; run
continues). Confirm this shape.
A: Confirmed. GeminiEnricher holds a KeywordEnricher and delegates to it on
per-card failure (keyword title + empty bullets, that card only, run continues).
Composition keeps keyword logic in one place.

### Q4 — what counts as retryable
Recommend: retry on ANY exception, bounded (`RETRY_COUNT` attempts, short
backoff), then fall back — rather than coupling to google-genai's specific
429/529/timeout/network exception types. A non-retryable error (e.g. bad key)
just falls back slightly slower; no v1 behavior difference. Confirm any-exception
bounded, or insist on specific types?
A: Any-exception bounded — retry on any exception (RETRY_COUNT attempts, short
backoff), then fall back. More robust than enumerating 429/529/timeout: an
unforeseen error can't slip past and crash a card. A non-retryable error (bad
key) just falls back a few seconds slower — no v1 behavior difference.

### Q5 — config additions
Alongside model / temperature / retry count in `presentation/config.py`, add:
  - `max_tokens` (~512 — enough for title + 3 bullets)
  - request `timeout` (so a hung call can't stall the whole process run)
Confirm.
A: Confirmed both. max_tokens (~512, enough for title + 3 bullets) and a request
timeout (so a hung call can't stall the whole process run — it times out ->
retry -> fallback, run continues).

### Q6 — dependency
`google-genai` was pip-installed ad hoc for the test but is only a commented
"parked" line in pyproject/requirements. Un-park it and add to both
`requirements.txt` and `pyproject.toml`. Confirm.
A: Confirmed. Un-park google-genai, add to BOTH requirements.txt and
pyproject.toml (Heroku needs requirements; local install needs pyproject).
Otherwise enrichment breaks on deploy.

### Q7 — input = titles only
Per the parked "enrichment input fields" decision, v1 feeds titles only (as the
test did), not perex/summary. Confirm titles-only for now.
A: entry = headline + summary/perex