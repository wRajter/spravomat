# Plan — web

## Purpose
The dumb-render layer. Reads finished story cards from db and renders them as an
HTML page. No business logic, no joins, no data decisions — everything is
already baked into the cards by presentation.

## Scope for v1
- ONE route (`/`) — renders the list of story cards.
- Look & feel carried from the POC (`website/`): card layout, per-outlet colors,
  responsive CSS (POC already has @media breakpoints at 768px / 1024px).
- Server-rendered HTML (Flask + Jinja), no JS framework.

## Contract
- Input: story cards from db via a single repository function
  (`get_story_cards()`). Nothing else is read. NO joins — cards are
  self-contained.
- Output: an HTML page.

## What web does NOT do (carried logic is REMOVED, not ported)
The POC web was "dirty" — it did joins, image selection, top-15 cap, bullet
JSON parsing. All of that is gone; the data arrives finished. From the POC,
carry the LOOK (HTML card structure + CSS), NOT the logic.
- No data selection / filtering / capping (ranking already did top N)
- No image selection (image_url baked into the card)
- No joins (sources baked into the card)

## The ONE thing web may compute
Relative time ("pred 3 h") from the card's absolute `newest_at` timestamp — this
is presentation relative to the moment of viewing, so it belongs here, computed
at render time in Europe/Bratislava. Everything else is just rendered as-is.

## Technical shape
- Flask application factory (`create_app()`), like the POC / niki-rajter.
- Blueprint for the route.
- Jinja templates: base + card list + navbar + footer (from POC).
- Reads db only via `get_story_cards()` — web never touches SQL.

## Dependency on db (new work web requires)
- Read: `get_story_cards() -> list[StoryCard]` — returns the stored cards,
  ordered by rank_score desc. (StoryCard already exists in shared.)

## Parked (do NOT implement now)
- Frontend redesign / minimalist restyle (separate later task)
- Navbar items: categories, etc.
- Per-card detail subpages (would be another route + a single-card read)
- Any interactivity (filtering, pagination)

## Open questions (for later)
- exact ordering guarantee from get_story_cards (rank_score desc) — confirm
- how missing fields render (no image, empty bullets in v1) — templates must
  handle gracefully

---

# Claude's review (2026-07-16)

Overall: solid and correctly scoped — dumb render, one route, self-contained
cards, carry the LOOK not the LOGIC, and the single justified computation
(relative time). The main thing to flag: the POC template is a REWRITE, not a
port, because its fields don't match our `StoryCard`. Answer inline (`A:` lines).
No code until resolved.

## Gaps in the plan (my findings)

1. **POC template can't be ported as-is.** `home.html` reads fields we don't
   have and loops over per-article data our card doesn't carry:
   - `cluster.llm_title or cluster.keywords` -> ours is just `card.title`.
   - `cluster.llm_bullets` -> `card.bullets`.
   - `cluster.articles` with `article.published_at_str` AND
     `article.confidence_score` -> ours is `card.sources` = {medium, title, url}
     only. No per-source date, no score (confidence is internal to grouping —
     correctly not exposed).
   So: carry the CSS + HTML card structure, but rewrite the Jinja to the
   `StoryCard` shape.

2. **Per-outlet colors cover only 3 of 7 outlets.** `main.css` has
   `.medium-sme`, `.medium-aktuality`, `.medium-dennik_n`. Missing: `sita`,
   `24_hodin`, `teraz_sk`, `euractiv`. Need classes for all 7 + a fallback.

A: Gap 1 (template rewrite): agreed — carry CSS + HTML card structure, rewrite the
Jinja to the StoryCard shape. Our shape is simpler (no confidence, no per-article
data). confidence_score correctly stays unexposed (internal to grouping).

## Questions I need you to answer

### Q1 — per-source date in the card?
The POC showed each outlet's article date. Our `StoryCard.sources` entries are
{medium, title, url} only — no per-source date. Two options:
  (a) Keep as-is: show only the story's `newest_at` (one relative time per card).
      Simpler; no card-shape change.
  (b) Show a date per source: presentation adds `published_at` to each `sources`
      entry (small card-shape + presentation change).
A: (a) — one relative time per card (newest_at). One "pred X h" per story is
enough to signal freshness, and per-source dates add clutter against the
minimalist look. No card-shape change. Revisit later if needed.

### Q2 — outlet colors + display labels
  Colors: add `.medium-*` classes for all 7 outlets + a fallback style. Confirm.
  Labels: show raw keys (`24_hodin`, `dennik_n`, `teraz_sk`) or pretty names
  (`24hod`, `Denník N`, `Teraz.sk`)? (Raw is fine for v1 if you'd rather park
  pretty labels.)
A: add .medium-* for all 7 outlets + a fallback style (so future outlets
aren't unstyled). Confirmed.
Labels: pretty names (24hod, Denník N, Teraz.sk) via a key->label map. Cheap, and
raw keys like "dennik_n" look like a bug on the page.

### Q3 — get_story_cards()
New db repository function `get_story_cards() -> list[StoryCard]`, ordered by
`rank_score` desc. JSONB bullets/sources come back as Python list/dict already,
so reconstruction is clean. Confirm.
A: Confirmed. get_story_cards() -> list[StoryCard], ordered by rank_score desc.
JSONB bullets/sources come back as list/dict — clean reconstruction.

### Q4 — relative time
Compute with stdlib `zoneinfo` (Europe/Bratislava), NOT pytz (drop the
dependency the POC used). Implement as a small Jinja filter so the template
stays declarative. Confirm approach.
A: Confirmed. zoneinfo (Europe/Bratislava), not pytz — one less dependency,
stdlib. Implement as a Jinja filter so the template stays declarative.

### Q5 — empty state
If there are no story cards, render a friendly "no stories yet" message rather
than a blank page. Templates also handle no-image / empty-bullets gracefully.
Confirm.
A: Confirmed. Empty state = friendly "no stories yet" message. Templates handle
no-image and empty-bullets gracefully (v1 cards have empty bullets by design).

## Minor (my lean: park)
- Footer says "2025" — trivially update to current year.
- Google Fonts loaded from CDN (external request) — fine on Heroku; self-hosting
  is a later polish.
- Navbar `Kategórie` / `O projekte` are dead `#` links — fine for v1.
A (any of these you want done now, not parked?):

A: 
- Footer year: fix to current year (it's a visible error).
- Google Fonts CDN: keep (fine on Heroku; self-hosting is later polish).
- Dead navbar links: keep for v1 (tied to the parked navbar/categories work).
Structure confirmed: create_app() factory + blueprint, templates/static under
web/, reads db only via get_story_cards(). Matches the Procfile.

## Structure — agree with the plan
`create_app()` factory + blueprint, templates/static under `web/`, reads db only
via `get_story_cards()`. Matches the Procfile
(`gunicorn "spravomat.web:create_app()"`).