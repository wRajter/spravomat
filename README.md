# Spravomat

Slovak lateral-reading news aggregator. Collects articles from Slovak news
outlets, clusters them by story, and shows which outlets cover each story.

## Structure

- `spravomat/acquisition` — fetch + normalize articles (RSS, scraping)
- `spravomat/grouping` — cluster articles into stories
- `spravomat/presentation` — rank stories + LLM enrichment
- `spravomat/db` — database access layer
- `spravomat/orchestration` — pipeline scheduling
- `spravomat/shared` — config, logging
- `spravomat/web` — Flask web app

## Setup

```bash
pip install -e .
cp .env.example .env   # then fill in values
```

## Run

```bash
flask --app spravomat.web run   # web app
```