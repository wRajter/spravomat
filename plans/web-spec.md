# Spec — web (finalized)

> Authoritative spec to build against. Consolidates the decisions made in
> `web.md` (kept as reference + full Q&A rationale). Finalized 2026-07-16.

## Purpose
The dumb-render layer. Reads finished story cards from db and renders them as an
HTML page. No business logic, no joins, no data decisions — everything is
already baked into the cards by presentation.

## Scope for v1
- ONE route (`/`) — renders the list of story cards.
- Carry the LOOK from the POC (`website/`): card layout, per-outlet colors,
  responsive CSS (breakpoints at 768px / 1024px). Carry the CSS + HTML card
  structure; REWRITE the Jinja to the `StoryCard` shape.
- Server-rendered HTML (Flask + Jinja), no JS framework.

## Contract
- Input: story cards from db via a single repository function
  `get_story_cards()`. Nothing else is read. NO joins — cards are self-contained.
- Output: an HTML page.

## What web does NOT do (carried logic is REMOVED, not ported)
The POC web was "dirty" — joins, image selection, top-N cap, bullet JSON parsing.
All gone; the data arrives finished. Carry the LOOK, not the LOGIC.
- No data selection / filtering / capping (ranking already took top N)
- No image selection (image_url baked into the card)
- No joins (sources baked into the card)
- No confidence score shown (internal to grouping, never exposed)

## The ONE thing web computes — relative time
Relative time ("pred 3 h") from the card's absolute `newest_at`, computed at
render time in Europe/Bratislava. This is presentation relative to the moment of
viewing, so it belongs here.
- Use stdlib `zoneinfo` (Europe/Bratislava), NOT pytz (drop that dependency).
- Implement as a small Jinja filter so the template stays declarative.
- ONE relative time per card (from `newest_at`). No per-source dates — the card
  does not carry them, and per-source timestamps would clutter the look
  (revisit later if needed).

## Rendering decisions
- **Title**: `card.title` as-is (already resolved — keyword title in v1, LLM
  later).
- **Bullets**: render `card.bullets` if present; empty in v1 — template omits
  the list gracefully.
- **Sources**: loop `card.sources` = {medium, title, url}. Show the outlet
  (colored badge + pretty label) and the linked title. No date, no score.
- **Image**: render `card.image_url` if present; omit the block if None.
- **Meta**: `media_count`, `article_count`, and the relative time.
- **Outlet colors**: `.medium-*` classes for all 7 outlets + a fallback style
  (so future outlets are not unstyled).
- **Outlet labels**: pretty names via a key -> label map, e.g.
  `sme -> SME`, `aktuality -> Aktuality`, `dennik_n -> Denník N`,
  `teraz_sk -> Teraz.sk`, `sita -> SITA`, `24_hodin -> 24hod`,
  `euractiv -> Euractiv`. Unknown key falls back to the raw key.
- **Empty state**: if there are no cards, render a friendly "no stories yet"
  message instead of a blank page.

## Technical shape
- Flask application factory `create_app()` (matches Procfile
  `gunicorn "spravomat.web:create_app()"`).
- Blueprint for the route.
- Jinja templates under `web/templates/`: base + card list + navbar + footer
  (carried from POC, Jinja rewritten). Static under `web/static/`.
- Reads db only via `get_story_cards()` — web never touches SQL.

## Dependency on db (new work web requires)
- Read: `get_story_cards() -> dict` (standard shape; `data` is
  `list[StoryCard]`), ordered by `rank_score` desc. JSONB bullets/sources come
  back as Python list/dict, so reconstruction is clean. `StoryCard` already
  exists in `shared`.

## Minor fixes decided
- Footer year: fix to the current year (visible error in the POC).
- Google Fonts via CDN: keep (fine on Heroku; self-hosting is later polish).
- Dead navbar links (`Kategórie`, `O projekte`): keep for v1 (tied to the parked
  navbar/categories work).

## Parked (do NOT implement now)
- Frontend redesign / minimalist restyle (separate later task)
- Navbar items: categories, etc.
- Per-card detail subpages (another route + a single-card read)
- Any interactivity (filtering, pagination)
- Per-source dates in the card (revisit if needed)
