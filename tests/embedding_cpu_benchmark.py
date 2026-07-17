# tests/embedding_cpu_benchmark.py

"""
THROWAWAY measurement — grouping embedding step on CPU (no GPU/MPS).

Heroku has no GPU, so this measures how the real embedding step behaves when
forced onto CPU: how long bge-m3 takes to load, how long it takes to encode all
current dev-DB articles, and how much resident memory it peaks at. These numbers
decide the deploy dyno size / cost.

It reuses the real grouping code:
- the same articles the normal run uses (repository.get_all_articles)
- the same text builder (Clusterer._embed_text)
- the same encode call (batch_size=32)
...but forces the model onto device='cpu'. The real grouping code is untouched.

Run from the project root:
    .venv/bin/python tests/embedding_cpu_benchmark.py
"""

import os
import resource
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from spravomat.db import repository
from spravomat.grouping import config
from spravomat.grouping.clusterer import Clusterer

BATCH_SIZE = 32  # same as Clusterer.cluster()


def peak_rss_mb() -> float:
    """Peak resident memory of this process, in MB (handles the OS unit difference)."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is bytes on macOS, kilobytes on Linux.
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return peak / divisor


def main() -> None:
    """Load bge-m3 on CPU, embed all dev-DB articles, and print the timings + RAM."""
    print("🔬 CPU embedding benchmark (device='cpu', no GPU/MPS)\n")

    # 1. Read the real articles (same source the normal grouping run uses).
    read = repository.get_all_articles()
    if not read["success"]:
        print(f"❌ Could not read articles: {read['message']}")
        return
    articles = read["data"]
    n = len(articles)
    if n == 0:
        print("❌ No articles in the dev DB — nothing to embed.")
        return
    print(f"ℹ️ Articles read from dev DB: {n}")

    # 2. Load the model on CPU. Bypass Clusterer.__init__ so the ONLY model load
    #    is this CPU one (its __init__ would load on the Mac's default MPS device),
    #    then reuse the clusterer's real methods.
    from sentence_transformers import SentenceTransformer

    clusterer = Clusterer.__new__(Clusterer)
    print(f"ℹ️ Loading model {config.MODEL_NAME} on CPU (assumes weights are cached)...")
    load_start = time.perf_counter()
    clusterer.model = SentenceTransformer(config.MODEL_NAME, device="cpu")
    load_time = time.perf_counter() - load_start

    # 3. Build the exact same texts the real run embeds.
    texts = [clusterer._embed_text(a) for a in articles]

    # 4. Encode on CPU — the measured embedding step (same call as cluster()).
    print(f"ℹ️ Encoding {n} articles on CPU (batch_size={BATCH_SIZE})...")
    encode_start = time.perf_counter()
    clusterer.model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=False)
    encode_time = time.perf_counter() - encode_start

    total = load_time + encode_time

    # 5. Report.
    print("\n" + "=" * 48)
    print("📊 CPU EMBEDDING BENCHMARK RESULTS")
    print("=" * 48)
    print(f"  Articles embedded : {n}")
    print(f"  Model load time   : {load_time:6.2f} s   ({config.MODEL_NAME})")
    print(f"  Embedding time    : {encode_time:6.2f} s   ({encode_time / n * 1000:.1f} ms/article)")
    print(f"  Total wall-clock  : {total:6.2f} s   (load + encode)")
    print(f"  Peak RAM (RSS)    : {peak_rss_mb():6.1f} MB")
    print("=" * 48)


if __name__ == "__main__":
    main()
