# Plan — Deploy to a single Hetzner VPS (Docker Compose)

> Getting Spravomat from localhost to public, on ONE self-managed VPS.
> Decided after comparing managed platforms (Heroku/serverless) vs a single box —
> chose a VPS for one flat cost hosting multiple apps. Decided 2026-07-18.

## Server (already provisioned)
- Hetzner CX23 (Ubuntu 26.04, 2 vCPU, 4 GB RAM, 40 GB SSD), Falkenstein.
- Secured: non-root sudo user, SSH key-only, root SSH disabled, ufw (22/80/443),
  fail2ban. 2 GB swap (poistka for the batch RAM peak). Docker + Compose installed.
- Repo cloned to ~/spravomat via GitHub deploy key (read-only).

## Architecture (all on the one box, decoupled via the DB)
  batch (compute)  →  Postgres (results)  →  web (displays)
    torch, on-demand    named volume          Flask, always on

## What to build (this task)
1. docker-compose.yml:
   - db: Postgres (pin the major version, e.g. postgres:17 — a tag bump won't
     auto-migrate the named volume). Data in a NAMED VOLUME (survives
     restarts/rebuilds). NOT exposed to internet — only on the compose network
     (no host port / localhost only). DBeaver access later via SSH tunnel.
   - web: Flask + gunicorn (~2 workers). Reads story_cards only. NO torch at
     runtime (lazy import). Caddy proxies to it.
   - batch: the heavy image (torch/bge-m3 + Gemini). NOT long-running — runs one
     command, then exits. The SAME image runs BOTH scheduled commands: collect
     (acquisition, torch unused) and process (grouping → presentation, torch).
     Always invoke with --rm so no stopped containers pile up:
     `docker compose run --rm batch python -m spravomat.orchestration.process`.
   - caddy: reverse proxy. Interim Caddyfile is HTTP-only (`:80`) on the server IP
     — NO ACME on a bare IP (Let's Encrypt won't issue certs for an IP). Structured
     so adding the domain later = one Caddyfile edit + a DNS A record → auto-HTTPS.
2. Dockerfiles:
   - web: lightweight (Flask, gunicorn, psycopg). NO torch. Small image.
   - batch: torch CPU-only wheel (--index-url
     https://download.pytorch.org/whl/cpu) + sentence-transformers + google-genai.
     Bake bge-m3 into the image (no per-run download).
3. Split requirements: requirements.txt = web only (no torch);
   requirements-batch.txt = full batch deps. Keeps web image small; torch only in
   batch.
4. .env.example (DATABASE_URL, GEMINI_API_KEY, POSTGRES password, ...). Real .env
   created on the server, NOT committed.
5. App reads DATABASE_URL from env (verified: connection.py does a raw
   psycopg.connect, config.py reads the env var unmodified). psycopg/libpq accepts
   both postgres:// and postgresql://, so NO scheme normalization is needed — just
   write postgresql:// in .env. Compose db service points DATABASE_URL at the db
   container.
6. Migrations: a one-off compose command to run the idempotent DDL (create tables
   on first deploy).

## Deploy workflow (how updates happen)
- Local: branch → test → merge to main → push to GitHub.
- Server: `git pull` → `docker compose up -d --build`. DB (named volume) untouched.
- Schema changes: run the migration command (idempotent DDL) — one extra step.

## Not in this task (later)
- Host cron for scheduled batch (3×/day) + collect (hourly) — after containers work.
- Domain + DNS (A record → server IP) — Caddy then does HTTPS automatically.
- DB backups: local daily pg_dump DONE (`scripts/backup_db.sh`, `plans/backup.md`).
  Off-box copy still open — the real remaining gap.
- Auto OS updates.

## Parked
- Coolify (skipped for now — bare Docker Compose is lighter; add later if wanted).
- Automated deploy (git push → auto-update) — manual git pull for now.

---

## Review (Claude, 2026-07-18)
Verdict: VPS + Compose approach is sound and well-structured. One real risk to
watch, a few concrete fixes, one item to delete.

### Main risk — RAM budget (4 GB, shared)
Batch peaks at ~2.25 GB (measured benchmark). Postgres + web (2 gunicorn workers)
+ Caddy + OS/Docker ≈ 1–1.5 GB baseline. So a batch run peaks the box at
~3.5–3.75 GB of 4 GB — tight. The 2 GB swap is the right insurance, but swapping
torch is slow, so ideally the batch stays in RAM (it will if baseline stays under
~1.7 GB). Guards:
- Never let collect and process overlap — an OOM could take down Postgres.
- Once cron is live, watch `dmesg` / memory under the first real batch peaks.
It will almost certainly fit, but it's the one real risk in the design.

### Concrete fixes
1. Use `docker compose run --rm batch ...` (line ~26). Without `--rm`, every
   on-demand/cron run leaves a stopped container behind, slowly filling the 40 GB
   disk.
2. Drop the `postgres://` vs `postgresql://` worry (line ~40). That was
   Heroku-specific (Heroku injected `postgres://`, SQLAlchemy rejected it). Here
   we author DATABASE_URL ourselves in `.env` and use psycopg directly — libpq
   accepts BOTH schemes. Verified: connection.py is a raw
   `psycopg.connect(DATABASE_URL)`, config.py reads it unmodified. No
   normalization code needed; just write `postgresql://`.
3. Caddy can't auto-HTTPS a bare IP (Let's Encrypt won't issue for an IP). Make
   the interim Caddyfile explicitly HTTP-only (`:80`) so it doesn't loop on ACME.
   Auto-HTTPS starts once the domain is added (already the line 52 plan) — just
   make the "for now" Caddyfile explicit. (line ~27)

### Smaller / consistency
4. acquisition vs collect mismatch: the `batch` service (line ~24) says
   "acquisition → grouping → presentation", but the later plan (line ~51) treats
   collect (acquisition, hourly) and process (grouping→presentation, 3×/day) as
   separate, and the example command is `process`. Cleaner: the batch IMAGE runs
   both commands (collect skips torch, process uses it); reword line ~24 so it
   doesn't read as one combined run.
5. ~~"CX23" looks like a typo~~ RESOLVED: CX23 is correct — Hetzner's 2026
   cost-optimized line (2 vCPU / 4 GB / 40 GB). Label kept as-is.
6. Pin the Postgres major version (e.g. `postgres:17`) — a future tag bump won't
   auto-migrate the named volume.
7. Backups (parked, line ~53): fine to defer, but on a single box a `pg_dump`
   off-box copy is the first thing to un-park — it's the only copy of the data.

### Solid — leave as-is
DB off the internet + SSH-tunnel access, split web/batch images + requirements
(web is genuinely torch-free — routes import only `db`, and grouping's torch
import is lazy), named volume, SSH/ufw/fail2ban hardening, idempotent migrations,
pull-and-rebuild deploy flow.

### Open questions for Lubomir
- Are collect and process guaranteed non-overlapping in the cron schedule (RAM)?
    A: Yes — schedule them non-overlapping; process runs at fixed times, collect on the hour but offset so it never coincides with process.
- Is a domain coming soon, or should we plan to run HTTP-only for a while?
    A: Domain: Coming very soon (tonight or tomorrow) but NOT this task. Build
   HTTP-only on the server IP now, but keep adding a domain trivial — one edit to
   the Caddyfile + a DNS A record. So make the interim Caddyfile explicit HTTP
   (:80) as you suggested, structured so switching to the domain (with auto-HTTPS)
   is a small change.
- Do you want DB backups in THIS task after all, given it's the only data copy?
    A: Not in this task, but un-park it as the very next step once containers run.
- Confirm the exact Hetzner plan (CX22?) so the RAM figure in this plan is right.
    A: It's CX23 — Hetzner's 2026 cost-optimized line. 2 vCPU / 4 GB / 40 GB. The label is right; keep CX23.

## Apply these fixes from your review, then build:
- docker compose run --rm batch ... (no leftover stopped containers)
- Interim Caddyfile HTTP-only on :80 (no ACME loop on bare IP)
- Drop the postgres:// vs postgresql:// normalization — not needed here
- Pin Postgres major (postgres:17)
- Reword the batch line so collect (no torch) and process (torch) read as separate
  commands from the same image, not one combined run
- Fix the CX label to CX23