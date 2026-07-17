# spravomat/presentation/config.py

"""
Presentation's configuration: ranking/filter knobs and keyword settings.

Internal to presentation (like grouping's thresholds). LLM provider/model config
is added here later, when a concrete enricher is built; the API key stays in the
environment (.env), never here.
"""

# Number of top-ranked stories turned into cards (arbitrary for v1, tunable).
TOP_N = 15

# Minimum distinct media for a cluster to count as a lateral-reading story.
MIN_MEDIA = 2

# Number of keywords in the keyword-derived title.
KEYWORD_TOP_N = 5

# Slovak stop words excluded from keyword extraction (carried from the POC).
SK_STOP_WORDS = [
    "a", "na", "v", "do", "je", "sa", "že", "to", "z", "s", "o", "ako", "aj",
    "po", "pri", "zo", "so", "pre", "vo", "si", "by", "ale", "už", "ani", "či",
    "ak", "sú", "má", "som", "bol", "bola", "bolo", "sme", "ste", "ich", "jeho",
    "jej", "im", "ho", "ju", "mi", "mu", "mňa", "tebe", "nás", "vás",
]

# --- LLM enrichment (GeminiEnricher) ---
# Model + call parameters. The API key comes from GEMINI_API_KEY in the
# environment (never here). If the key is unset, enrichment degrades to the
# keyword fallback — see enrichment.get_enricher().
ENRICH_MODEL = "gemini-3.1-flash-lite"
ENRICH_TEMPERATURE = 0.3
ENRICH_RETRY_COUNT = 3      # attempts per cluster before the keyword fallback
ENRICH_MAX_TOKENS = 512     # response cap — enough for a title + 3 bullets
ENRICH_TIMEOUT = 30         # seconds per request (a hung call can't stall the run)
