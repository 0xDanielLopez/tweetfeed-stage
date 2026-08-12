# Campaign permalink pages (prototype)

Status: approved, stage-only prototype. Not wired to the daily regen cron or prod yet.

## Problem

`/campaigns/` is a single client-rendered page trying to rank for hundreds of
distinct exact-match queries (domains, wallet addresses, hashes that appear
inside AI-clustered campaigns). 2026-08-12 audit measured 11,283 impressions
over 28 days at 0.25% CTR, position ~13 — one generic page cannot rank well
for that many unrelated exact-match terms. phishunt.io's per-entity pages
(`/cert/{CA}/`, `/domain/{brand}/`) solve the same shape of problem and reach
2-28% CTR on similar exact-match queries.

## Prior art / risk closed before designing

phishunt's first campaign-permalink attempt (`/campaigns/<id>/`) broke within
24h: `cluster_id` was an autoincrement row id reassigned on every daily
rebuild, so every permalink 404'd the next day. Fixed 2026-08-02 via a
content-hash `stable_key` plus Jaccard-similarity continuity across runs.

TweetFeed's campaigns backend (`campaigns/ids.py` + `campaigns/continuity.py`,
already in production) independently implements the same fix: `id` is a
sha256 of the candidate's anchors (`tfc-<12 hex>`), and `continuity.py`
inherits yesterday's id for any candidate whose IOC-membership Jaccard
overlap with a previous campaign is >= 0.3. So the id is already safe to use
as a permalink slug — no new stability layer needed.

## Scope (this session)

Stage-only, manually generated, 8-10 campaign pages (the highest `ioc_count`
campaigns out of the 22 currently active). No cron wiring, no prod push, no
`/campaigns/` internal-linking changes yet (avoids introducing links to pages
that don't exist for the other ~12-14 campaigns). Those are separate
follow-up decisions once this prototype is visually reviewed.

## Architecture

Mirrors the existing tag-page generator exactly (same repo, same pattern,
zero new infra):

- `scripts/generate_campaign_pages.py` — new script, modeled on
  `scripts/regen_tag_pages.py`. Reads live `GET
  https://api.tweetfeed.live/v1/campaigns`, selects the top-N campaigns by
  `ioc_count`, renders each through the Jinja2 template below, writes
  `campaigns/<id>/index.html`.
- `scripts/templates/campaign_page.html.j2` — new template, modeled on
  `scripts/templates/tag_page.html.j2` (same nav/footer/analytics
  boilerplate, same head/schema conventions).

## URL

`/campaigns/<id>/` using the existing `tfc-<hash>` id verbatim. No new slug
scheme — the id is already stable and unique; page *content* (title, H1,
domain list) is what needs to match exact-match search queries, not the URL
path.

## Page content

- Title: built from the 2-3 most prominent `anchors.registered_domains` (or
  a trimmed `context` excerpt when there are more anchors than fit), e.g.
  "jcd666.vip, pxb70.com and 3 more — Campaign tracked by TweetFeed (106
  IOCs)".
- Intro: the AI-written `context` field, in a `.card` (matches site
  convention — no prose walls outside cards).
- Domains table: `anchors.registered_domains`, classic IOC-table look
  (matches `feedback_tweetfeed_tables_classic_format` — not the `/search/`
  lookup-page style).
- IOC table: the campaign's `iocs` array (API already caps this at 25),
  same classic table component used elsewhere on the site.
- Stat row: `confidence`, `first_seen`, `ioc_count` as small badges/tiles,
  matching the dashboard/feeds stat-tile pattern already on the site.
- Freshness note: since this prototype isn't cron-wired, the page states
  the generation timestamp so it never implies live data it can't back up.
  The template is otherwise regen-safe (idempotent, no hand-editing) so a
  future daily-regen wire-up can reuse it unchanged.

## SEO

- Self-canonical (not pointing at `/campaigns/`).
- Meta description built from a truncated `context`.
- `WebPage` + `BreadcrumbList` JSON-LD, matching the tag-page schema
  pattern.
- Indexable (no `noindex`) — unlike phishunt's dynamic archive pages, these
  are static snapshots regenerated wholesale each run, not live
  per-request pages serving current-vs-stale state, so there's no
  live/stale ambiguity to hide from crawlers for this prototype's fixed
  snapshot.

## Explicitly out of scope for this session

- Wiring into `regen-landing-pages.yml` or any new GH Action (daily
  automation).
- Linking to these pages from `/campaigns/`'s existing card list (would
  create dead links for the campaigns without a generated page yet).
- Handling a campaign that later drops out of the 7-day window (archive
  vs. 410 vs. delete) — moot until this is cron-wired.
- Prod rollout.

## Definition of done for this prototype

- Template renders correctly for a range of campaign shapes (few anchors vs
  many, short vs long `context`, low vs high `ioc_count`).
- 8-10 real pages generated and pushed to stage only.
- Visual check (screenshot or live stage URL) confirms no layout breakage,
  consistent with the rest of the site (cards, black borders, no
  `d-md-block` footer bug).
- `scripts/check_consistency.py` still passes (won't cover the new pages
  specifically since they're not in `MAIN_PAGES`, but must not break
  anything site-wide).
