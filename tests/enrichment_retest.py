# tests/enrichment_retest.py

"""
THROWAWAY re-test — enrichment with FULL article input (title + summary + perex).

The comparison test fed titles only, which made bullets paraphrase the title.
This re-test feeds each article's title + summary + perex so bullets can draw
concrete detail from the text. Gemini only (already chosen), ~4 varied clusters,
2 runs each. Purpose: eyeball whether (a) bullets now add real detail, and
(b) the model stays faithful with the longer input.

Run from the project root:
    .venv/bin/python tests/enrichment_retest.py
"""

import json
import os
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from spravomat.db import repository

GEMINI_MODEL = "gemini-3.1-flash-lite"
TEMPERATURE = 0.3
RUNS = 2
NUM_CLUSTERS = 4
MAX_ARTICLES = 6          # cap articles per cluster fed to the model
MAX_TEXT_CHARS = 500      # cap each article's summary+perex text
OUTPUT_FILE = "tests/enrichment_retest_output.md"

# New prompt: bullets must draw concrete detail from the texts, not restate title.
PROMPT_TEMPLATE = """Na základe týchto článkov o tej istej udalosti vytvor:
1. Krátky výstižný názov témy (max 12 slov, slovenčina)
2. Tri krátke odrážky (slovenčina)

Pravidlá:
- Titulok postav tak, aby vystihoval udalosť.
- Odrážky NAPLŇ konkrétnymi detailmi z textov (fakty, čísla, mená, súvislosti) — NEopakuj len to, čo je v titulku. Každá odrážka nech pridáva niečo nové.
- Vychádzaj IBA z informácií v textoch nižšie. Nič si nevymýšľaj.
- Informatívne, nie clickbait.

Články o tej istej udalosti (titulok + text):
{articles}

Odpovedz IBA v JSON formáte, žiadny iný text:
{{"title": "...", "bullets": ["...", "...", "..."]}}"""


def article_text(a) -> str:
    """summary + perex (whichever are present), capped."""
    parts = [p for p in (a.summary, a.perex) if p]
    return " ".join(parts)[:MAX_TEXT_CHARS]


def build_prompt(articles) -> str:
    blocks = []
    for a in articles[:MAX_ARTICLES]:
        blocks.append(f"- Titulok: {a.title}\n  Text: {article_text(a) or '(bez textu)'}")
    return PROMPT_TEMPLATE.format(articles="\n".join(blocks))


def select_clusters():
    mapping = repository.get_cluster_mapping()["data"]
    articles = repository.get_all_articles()["data"]
    by_id = {a.article_id: a for a in articles}

    grouped = {}
    for article_id, cluster_id in mapping.items():
        a = by_id.get(article_id)
        if a is not None:
            grouped.setdefault(cluster_id, []).append(a)

    def media_count(arts):
        return len({a.medium for a in arts})

    lateral = [(cid, arts) for cid, arts in grouped.items() if media_count(arts) >= 2]
    big = sorted([x for x in lateral if media_count(x[1]) >= 4], key=lambda x: -len(x[1]))
    small = sorted([x for x in lateral if media_count(x[1]) == 2], key=lambda x: -len(x[1]))
    mid = sorted([x for x in lateral if media_count(x[1]) == 3], key=lambda x: -len(x[1]))

    picked = big[:2] + small[:1] + mid[:1]
    seen, out = set(), []
    for cid, arts in picked + big + mid + small:
        if cid not in seen:
            seen.add(cid)
            out.append((cid, arts))
        if len(out) >= NUM_CLUSTERS:
            break
    return out


def parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def call_gemini(prompt):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=TEMPERATURE),
    )
    return resp.text or ""


def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set in .env")
        return

    clusters = select_clusters()
    print(f"🔬 Enrichment re-test (full input) — {len(clusters)} clusters, {RUNS} runs each\n")

    lines = ["# Enrichment re-test — full article input (title + summary + perex)\n"]
    for cid, arts in clusters:
        media = sorted({a.medium for a in arts})
        print(f"  → cluster {cid} ({len(media)} media, {len(arts)} articles)")
        lines.append(f"\n## Cluster {cid} — {len(media)} media, {len(arts)} articles\n")
        lines.append("**Input fed to the model (title + text snippet):**\n")
        for a in arts[:MAX_ARTICLES]:
            snippet = (article_text(a) or "(bez textu)")[:180]
            lines.append(f"- `{a.medium}` **{a.title}**\n  _{snippet}_")

        prompt = build_prompt(arts)
        lines.append("\n**Gemini output:**\n")
        for i in range(1, RUNS + 1):
            try:
                raw = call_gemini(prompt)
                parsed = parse_json(raw)
            except Exception as e:
                lines.append(f"- Run {i} [ERROR]: {e}")
                continue
            if not parsed:
                lines.append(f"- Run {i} [JSON ❌] raw: {raw[:200]}")
                continue
            bullets = "\n".join(f"    - {b}" for b in parsed.get("bullets", []))
            lines.append(f"- Run {i}: **{parsed.get('title', '')}**\n{bullets}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n📝 Output written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
