# tests/enrichment_comparison.py

"""
THROWAWAY experiment — LLM enrichment model comparison. NOT part of the app.

Runs 3 models on the same real clusters with the same Slovak prompt and writes a
side-by-side comparison so you can eyeball Slovak quality and pick one. This is
NOT the real enricher — the winner gets built properly later, behind the
Enricher interface.

Run it yourself from the project root:
    .venv/bin/python tests/enrichment_comparison.py

Requirements:
- Local DB populated (articles + article_clusters) — run the pipeline first.
- API keys in .env: GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY.
  Fill only the ones you want; the script skips any model whose key is unset or
  whose SDK is not installed.
- SDKs (install the ones you use):
    .venv/bin/pip install google-genai openai anthropic

Output: prints a summary to the terminal and writes the full side-by-side to
tests/enrichment_comparison_output.md.
"""

import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Make the project root importable when run directly (`python tests/...py`) —
# running a script file puts tests/ on sys.path, not the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spravomat.db import repository
from spravomat.presentation.enrichment import _extract_keywords

load_dotenv()

# ==========================================================================
# CONFIG — edit freely, it's a throwaway experiment.
# ==========================================================================

# Model IDs. VERIFY these strings against each provider's current docs — if a
# model is renamed the API returns a "model not found" error (shown in output).
GEMINI_MODEL = "gemini-3.1-flash-lite"
OPENAI_MODEL = "gpt-4.1-mini"
ANTHROPIC_MODEL = "claude-haiku-4-5"

TEMPERATURE = 0.3
RUNS_PER_MODEL = 3          # repeat each cluster/model to see run-to-run variance
NUM_CLUSTERS = 9            # how many real clusters to sample
TITLES_PER_PROMPT = 10      # max article titles fed into the prompt

OUTPUT_FILE = "tests/enrichment_comparison_output.md"

# The shared Slovak prompt — SAME for all 3 models. (Defaulted from the POC
# prompt because none was pasted into the request; edit as you like.)
PROMPT_TEMPLATE = """Na základe týchto titulkov správ vytvor:
1. Krátky výstižný názov témy (max 8 slov, slovenčina)
2. Tri krátke body (max 12 slov každý, slovenčina) vysvetľujúce o čom téma je

Titulky:
{titles}

Odpovedz IBA v JSON formáte, žiadny iný text:
{{"title": "...", "bullets": ["...", "...", "..."]}}"""


# ==========================================================================
# Cluster selection — pull varied real clusters from the DB
# ==========================================================================

@dataclass
class SampleCluster:
    cluster_id: int
    sources: list[tuple[str, str]]  # (medium, title)
    tag: str = ""

    @property
    def media_count(self) -> int:
        return len({m for m, _ in self.sources})

    @property
    def titles(self) -> list[str]:
        return [t for _, t in self.sources]


def _normalize(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def _has_syndication(cluster: SampleCluster) -> bool:
    """True if two articles share a near-identical (normalized-equal) title."""
    norm = [_normalize(t) for t in cluster.titles]
    return len(norm) != len(set(norm))


def select_clusters() -> list[SampleCluster]:
    """Aggregate real clusters and pick a deliberately varied sample."""
    mapping = repository.get_cluster_mapping()["data"]
    articles = repository.get_all_articles()["data"]
    by_id = {a.article_id: a for a in articles}

    grouped: dict[int, list] = {}
    for article_id, cluster_id in mapping.items():
        article = by_id.get(article_id)
        if article is not None:
            grouped.setdefault(cluster_id, []).append(article)

    clusters = [
        SampleCluster(cluster_id=cid, sources=[(a.medium, a.title) for a in arts])
        for cid, arts in grouped.items()
    ]
    lateral = [c for c in clusters if c.media_count >= 2]

    large = sorted([c for c in lateral if c.media_count >= 4], key=lambda c: -len(c.sources))
    mid = sorted([c for c in lateral if c.media_count == 3], key=lambda c: -len(c.sources))
    small = sorted([c for c in lateral if c.media_count == 2], key=lambda c: -len(c.sources))
    syndicated = [c for c in lateral if _has_syndication(c)]

    selected: dict[int, SampleCluster] = {}

    def take(pool: list[SampleCluster], n: int, tag: str) -> None:
        for c in pool:
            if len(selected) >= NUM_CLUSTERS:
                return
            if c.cluster_id not in selected:
                c.tag = tag
                selected[c.cluster_id] = c
                n -= 1
                if n == 0:
                    return

    take(large, 3, "large (>=4 media)")
    take(syndicated, 2, "syndication (near-identical titles)")
    take(small, 3, "small (2 media)")
    take(mid, NUM_CLUSTERS, "mid (3 media)")
    take(large + mid + small, NUM_CLUSTERS, "extra")  # top up if still short

    return list(selected.values())


# ==========================================================================
# Model callers — each returns (status, text): status in ok | unavailable | error
# ==========================================================================

def _available(env_var: str, module: str) -> tuple[bool, str]:
    if not os.getenv(env_var):
        return False, f"{env_var} not set"
    if importlib.util.find_spec(module) is None:
        return False, f"{module} not installed"
    return True, ""


def call_gemini(prompt: str) -> tuple[str, str]:
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=TEMPERATURE),
        )
        return "ok", resp.text or ""
    except Exception as e:
        return "error", str(e)


def call_openai(prompt: str) -> tuple[str, str]:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
        return "ok", resp.choices[0].message.content or ""
    except Exception as e:
        return "error", str(e)


def call_anthropic(prompt: str) -> tuple[str, str]:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=512,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return "ok", text
    except Exception as e:
        return "error", str(e)


MODELS = [
    ("Gemini 3.1 Flash-Lite", "GEMINI_API_KEY", "google.genai", call_gemini),
    ("GPT-4.1 mini", "OPENAI_API_KEY", "openai", call_openai),
    ("Claude Haiku 4.5", "ANTHROPIC_API_KEY", "anthropic", call_anthropic),
]


# ==========================================================================
# Parsing + result model
# ==========================================================================

def parse_json(text: str) -> dict | None:
    """Parse the model's JSON reply, tolerating ```json fences. None on failure."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


@dataclass
class RunResult:
    status: str            # ok | error
    raw: str = ""
    title: str = ""
    bullets: list[str] = field(default_factory=list)
    json_ok: bool = False


def run_once(caller, prompt: str) -> RunResult:
    status, text = caller(prompt)
    if status != "ok":
        return RunResult(status="error", raw=text)
    parsed = parse_json(text)
    if parsed is None:
        return RunResult(status="ok", raw=text, json_ok=False)
    return RunResult(
        status="ok",
        raw=text,
        title=str(parsed.get("title", "")),
        bullets=[str(b) for b in parsed.get("bullets", [])],
        json_ok=True,
    )


# ==========================================================================
# Main
# ==========================================================================

def main() -> None:
    print("🔬 LLM enrichment comparison (throwaway)\n")

    active = []
    skipped = []
    for name, env_var, module, caller in MODELS:
        ok, reason = _available(env_var, module)
        (active if ok else skipped).append((name, caller, reason))

    for name, _, reason in skipped:
        print(f"  ⏭️  skipping {name}: {reason}")
    if not active:
        print("\n❌ No models available. Set API keys in .env and install the SDKs.")
        return
    print(f"  ✅ comparing: {', '.join(n for n, _, _ in active)}")

    clusters = select_clusters()
    print(f"  📦 sampled {len(clusters)} clusters, {RUNS_PER_MODEL} runs each\n")

    lines: list[str] = ["# LLM enrichment comparison\n"]
    lines.append(f"Prompt temperature {TEMPERATURE}, {RUNS_PER_MODEL} runs/model. "
                 f"Models: {GEMINI_MODEL}, {OPENAI_MODEL}, {ANTHROPIC_MODEL}.\n")
    json_failures = {name: 0 for name, _, _ in active}
    json_errors = {name: 0 for name, _, _ in active}
    json_total = {name: 0 for name, _, _ in active}

    for c in clusters:
        print(f"  → cluster {c.cluster_id} ({c.tag}, {c.media_count} media)")
        titles = c.titles[:TITLES_PER_PROMPT]
        prompt = PROMPT_TEMPLATE.format(titles="\n".join(f"- {t}" for t in titles))
        keyword_title = ", ".join(_extract_keywords(titles)) or "(none)"

        lines.append(f"\n## Cluster {c.cluster_id} — {c.media_count} media, "
                     f"{len(c.sources)} articles [{c.tag}]\n")
        lines.append("**Sources:**\n")
        for medium, title in c.sources[:TITLES_PER_PROMPT]:
            lines.append(f"- `{medium}` {title}")
        lines.append(f"\n**Keyword title (current v1):** {keyword_title}\n")

        for name, caller, _ in active:
            lines.append(f"\n### {name}\n")
            for i in range(1, RUNS_PER_MODEL + 1):
                result = run_once(caller, prompt)
                json_total[name] += 1
                if result.status == "error":
                    json_errors[name] += 1
                    lines.append(f"- Run {i} [ERROR]: {result.raw[:200]}")
                    continue
                if not result.json_ok:
                    json_failures[name] += 1
                    lines.append(f"- Run {i} [JSON ❌] raw: {result.raw[:200]}")
                    continue
                bullets = " / ".join(result.bullets) if result.bullets else "(no bullets)"
                lines.append(f"- Run {i} [JSON ✅]: **{result.title}** — {bullets}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n📊 Per model (of {} runs each):".format(RUNS_PER_MODEL * len(clusters)))
    for name, _, _ in active:
        total = json_total[name]
        fails = json_failures[name]
        errors = json_errors[name]
        valid = total - fails - errors
        print(f"   {name:24} {valid} valid JSON / {fails} bad JSON / {errors} API error")
    print(f"\n📝 Full side-by-side written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
