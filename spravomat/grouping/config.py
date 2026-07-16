# spravomat/grouping/config.py

"""
Grouping's private configuration: embedding model + clustering thresholds.

These are internal to grouping and fully hidden behind the contract — changing
them must not affect downstream. Values carried from the POC (proven on real
data); re-validation against ground truth is a parked open question.
"""

# Sentence-embedding model.
MODEL_NAME = "BAAI/bge-m3"

# Distance threshold for the primary clustering pass (distance = 1 - cosine).
BASE_THRESHOLD = 0.40

# Thresholds used only for the internal stability (threshold) score.
THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50]

# Minimum confidence score (0–9) to keep an article; below this it is dropped.
UNCATEGORIZED_THRESHOLD = 5

# Agglomerative linkage. "complete": a cluster forms only if ALL pairs are close
# enough, which prevents unrelated topics merging into mega-clusters.
LINKAGE = "complete"
