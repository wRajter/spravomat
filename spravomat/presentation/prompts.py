# spravomat/presentation/prompts.py

"""
LLM prompt text for enrichment.

Kept in its own file so the (long, multi-line, Slovak) prompt doesn't bloat
config.py (short knobs) or enrichment.py (logic). enrichment.py imports and
fills it; the prompt/parser link stays clear (adjacent files, same component).

Validated on real clusters in the comparison + full-input re-test (2026-07-17).
The `{articles}` placeholder is filled with one block per article (title + text).
"""

ENRICHMENT_PROMPT = """Na základe týchto článkov o tej istej udalosti vytvor:
1. Krátky výstižný názov témy (max 12 slov, slovenčina)
2. Tri krátke odrážky (slovenčina)

Pravidlá:
- Titulok postav tak, aby vystihoval udalosť.
- Odrážky NAPLŇ konkrétnymi detailmi z textov (fakty, čísla, mená, súvislosti) — NEopakuj len to, čo je v titulku. Každá odrážka nech pridáva niečo nové.
- Vychádzaj IBA z informácií v textoch nižšie. Nič si nevymýšľaj.
- Nepoužívaj vlastné znalosti mimo poskytnutých textov.
- Informatívne, nie clickbait.

Články o tej istej udalosti (titulok + text):
{articles}

Odpovedz IBA v JSON formáte, žiadny iný text:
{{"title": "...", "bullets": ["...", "...", "..."]}}"""
