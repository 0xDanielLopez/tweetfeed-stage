# Campaign permalink pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate 8-10 static, indexable `/campaigns/<id>/` pages (stage only) so individual AI-clustered campaigns can rank for their own exact-match queries, instead of everything funneling through one generic client-rendered `/campaigns/` page.

**Architecture:** One new Jinja2 template (`scripts/templates/campaign_page.html.j2`) modeled byte-for-byte on the existing `scripts/templates/tag_page.html.j2` (same head/nav/footer, swapped body sections), rendered by one new script (`scripts/generate_campaign_pages.py`) modeled on `scripts/regen_tag_pages.py`'s structure (fetch → per-item render → write `.../index.html`, skip-and-continue on a single item's error). Data source is the live `GET https://api.tweetfeed.live/v1/campaigns` endpoint — no backend changes.

**Tech Stack:** Python 3, `requests`, `jinja2` (already in `requirements.txt` alongside `pyyaml` — verify before assuming, `regen_tag_pages.py` already imports both).

## Global Constraints

- Campaign id (`tfc-<12 hex>`) is a stable sha256 of `anchors` with day-over-day Jaccard-similarity continuity (`campaigns/ids.py` + `campaigns/continuity.py` in the campaigns repo) — safe to use directly as the permalink slug, no new slug scheme.
- Stage only. Do not touch `frontend-prod`, do not modify `/campaigns/index.html`'s card-rendering JS, do not wire into `.github/workflows/regen-landing-pages.yml`.
- Feed-derived text (campaign `context`, domain values, IOC values/users) must go through `html.escape(str, quote=True)` before interpolation — `campaign_page.html.j2` will have `autoescape=select_autoescape([])` (OFF), same as `tag_page.html.j2`, because both templates also emit raw JSON-LD via `| safe`. Do not turn autoescape on.
- No prose walls — the AI-written `context` field goes inside a `.card`, same visual pattern as the rest of the site (per `feedback_tweetfeed_aesthetic_over_seo`).
- IOC/domain tables use the site's classic table look (see `tag_page.html.j2`'s "Recent IOCs" table), never the `/search/` lookup-page style.
- `noindex` follows the same `IS_STAGE` pattern as `regen_tag_pages.py` (`not (REPO_ROOT / "CNAME").is_file()`) — stage pages get `noindex,nofollow` automatically; this plan does not hardcode indexability, it inherits the existing mechanism.

---

### Task 1: Campaign page template

**Files:**
- Create: `scripts/templates/campaign_page.html.j2`

**Interfaces:**
- Consumes (Jinja context, all provided by Task 2's `render_campaign()`):
  - `c` (dict): `id` (str, e.g. `"tfc-9747b61b0a0b"`), `title` (str, pre-built display title), `meta_description` (str), `context_html` (str, already-escaped/formatted context paragraph), `confidence` (str: `"low"|"medium"|"high"`), `first_seen` (str, `YYYY-MM-DD`), `ioc_count` (int), `domains` (list of `{value_full, value_display}` dicts, already-escaped), `generated_at_str` (str, human-readable UTC timestamp for the freshness note)
  - `iocs` (list of dicts, same shape as `tag_page.html.j2`'s `samples`: `date_short, type, type_color, type_text_color, value_full, value_display, value_query, user` — all pre-escaped)
  - `webpage_jsonld` (str, pre-built JSON string, rendered via `| safe`)
  - `noindex` (bool)
- Produces: nothing (leaf template)

- [ ] **Step 1: Copy `tag_page.html.j2` as the starting point**

```bash
cp /home/daniel/code/tweetfeed/frontend-stage/scripts/templates/tag_page.html.j2 \
   /home/daniel/code/tweetfeed/frontend-stage/scripts/templates/campaign_page.html.j2
```

- [ ] **Step 2: Edit the `<head>` block**

In `campaign_page.html.j2`:
- `<meta name="description" content="{{ m.meta_description }}">` → `content="{{ c.meta_description }}"`
- Drop the `<meta name="keywords">` line (tag pages use it, campaigns don't have an equivalent field — don't invent one).
- `<link rel="canonical" href="https://tweetfeed.live/tag/{{ m.slug }}/">` → `href="https://tweetfeed.live/campaigns/{{ c.id }}/"`
- Drop the `<link rel="alternate" type="application/rss+xml" ...>` line entirely (no per-campaign RSS feed exists).
- `<title>{{ m.seo_title }}</title>` → `<title>{{ c.title }} | TweetFeed</title>`
- All 3 `twitter:*` / `og:*` URL fields → `https://tweetfeed.live/campaigns/{{ c.id }}/`
- `twitter:title` / `og:title` → `{{ c.title }}`
- `twitter:description` / `og:description` → `{{ c.meta_description }}`
- `og:image:alt` → a static string: `"TweetFeed logo"` (tag pages set this per-tag; campaigns don't need per-campaign alt text for the shared OG image).
- Keep the Organization + Person JSON-LD blocks byte-identical (site-wide, not tag/campaign-specific).
- Replace the third JSON-LD block (`{{ webpage_jsonld | safe }}`) — keep as-is, Task 2 builds a campaign-shaped payload for the same variable name.
- Replace the `BreadcrumbList` JSON-LD:
```html
<script type="application/ld+json">
{
	"@context": "https://schema.org",
	"@type": "BreadcrumbList",
	"itemListElement": [
		{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://tweetfeed.live/"},
		{"@type": "ListItem", "position": 2, "name": "Campaigns", "item": "https://tweetfeed.live/campaigns/"},
		{"@type": "ListItem", "position": 3, "name": "{{ c.title }}", "item": "https://tweetfeed.live/campaigns/{{ c.id }}/"}
	]
}
</script>
```
- Delete the final `{{ faq_jsonld | safe }}` `<script>` block for now — Task 1 skips FAQ (keeps the template smaller for the prototype; revisit only if the prototype is later promoted past stage).

- [ ] **Step 3: Edit the sidebar `<aside class="docs-sidebar">`**

Mark the existing `<li><a href="../../campaigns/">AI Campaigns</a></li>` entry `class="active"` (matches the pattern already used for `<a href="../../tags/" class="active">` in the original), since a campaign detail page's parent section is Campaigns, not Tags. Remove `class="active"` from the Tag-index `<li>` (it shouldn't carry over).

- [ ] **Step 4: Replace the H1/H2 header block**

Replace both `#presentationSecondary` / `#presentationMobile` blocks' inner content:
```html
<div id="presentationSecondary" class="d-none d-md-block">
	<br><br><br>
	<h1 class="toph1"><i class="fas fa-layer-group" style="font-size: 36px;"></i> {{ c.title }}</h1>
	<p style="font-size:14px;color:#737373;margin-top:0.5rem;">Snapshot generated {{ c.generated_at_str }}. AI-clustered from public Twitter/X threat-intel reports.</p>
</div>
<div id="presentationMobile" class="d-block d-md-none">
	<br>
	<p class="toph1" role="heading" aria-level="1"><i class="fas fa-layer-group" style="font-size: 36px;"></i> {{ c.title }}</p>
	<p style="font-size:13px;color:#737373;margin-top:0.25rem;">Snapshot generated {{ c.generated_at_str }}.</p>
</div>
```
(`fa-layer-group` is already loaded via the shared Font Awesome 5.15.4 CDN link inherited from the head — same icon set as `fa-tag`, no new dependency.)

- [ ] **Step 5: Replace the "IOCs by window" 4-card row with a 3-card stat row**

Replace the entire `<h3 class="section-heading">IOCs by window</h3>` block and its `.row` of 4 cards with:
```html
<h3 class="section-heading">Campaign stats</h3>
<div class="row">
	<div class="col-md-4 col-sm-6 col-12">
		<div class="card shadow mb-4">
			<div class="card-header text-center">
				<span class="card-text cardTitle">IOCs</span>
				<hr>
				<p style="font-size: 32px; font-weight: 600; color: #0026E6; margin-bottom: 0.25rem; font-family: 'Rubik', sans-serif;">{{ c.ioc_count }}</p>
				<p style="font-size: 13px; color: #737373; margin-bottom: 0;">tracked in this campaign</p>
			</div>
		</div>
	</div>
	<div class="col-md-4 col-sm-6 col-12">
		<div class="card shadow mb-4">
			<div class="card-header text-center">
				<span class="card-text cardTitle">Confidence</span>
				<hr>
				<p style="font-size: 32px; font-weight: 600; color: #0026E6; margin-bottom: 0.25rem; font-family: 'Rubik', sans-serif; text-transform:capitalize;">{{ c.confidence }}</p>
				<p style="font-size: 13px; color: #737373; margin-bottom: 0;">clustering confidence</p>
			</div>
		</div>
	</div>
	<div class="col-md-4 col-sm-6 col-12">
		<div class="card shadow mb-4">
			<div class="card-header text-center">
				<span class="card-text cardTitle">First seen</span>
				<hr>
				<p style="font-size: 28px; font-weight: 600; color: #0026E6; margin-bottom: 0.25rem; font-family: 'Rubik', sans-serif;">{{ c.first_seen }}</p>
				<p style="font-size: 13px; color: #737373; margin-bottom: 0;">earliest IOC in this cluster</p>
			</div>
		</div>
	</div>
</div>
<p style="color:#737373; font-size:13px; font-family:'Rubik',sans-serif; margin-top:-0.5rem; margin-bottom:1.5rem;">Snapshot as of {{ c.generated_at_str }}. This is a manually-generated prototype page, not yet on the daily regeneration cycle.</p>
```

- [ ] **Step 6: Replace "About #tag" with "About this campaign"**

```html
<h3 class="section-heading">About this campaign</h3>
<div class="card mb-4">
	<div class="card-body">
		<p style="margin-bottom:0; font-family:'Rubik',sans-serif; color:#1c1c1c; font-size:15px; line-height:1.8;">{{ c.context_html }}</p>
	</div>
</div>
```

- [ ] **Step 7: Add "Domains in this campaign" table (new section, no tag-page equivalent)**

Insert after the "About this campaign" card:
```html
<h3 class="section-heading">Domains in this campaign</h3>
<div class="card mb-4">
	<div class="card-body">
		{% if c.domains %}
		<div class="table-responsive">
			<table class="table table-sm" style="table-layout:fixed; width:100%; min-width:320px; margin-bottom:0;">
				<colgroup><col style="width:100%;"></colgroup>
				<thead><tr><th>Domain</th></tr></thead>
				<tbody>
					{% for d in c.domains %}<tr>
						<td style="font-family:monospace; font-size:13px; vertical-align:middle;" title="{{ d.value_full }}"><i class="tf-copy far fa-copy" data-copy="{{ d.value_full }}" style="margin-right:0.4rem;"></i>{{ d.value_display }}</td>
					</tr>
					{% endfor %}</tbody>
			</table>
		</div>
		{% else %}
		<p style="margin-bottom:0; color:#737373; font-size:14px; font-family:'Rubik',sans-serif;">No registered-domain anchors for this campaign (clustered on tags or URL path patterns instead).</p>
		{% endif %}
	</div>
</div>
```

- [ ] **Step 8: Replace "Recent IOCs tagged #..." with "IOCs in this campaign"**

Same table markup/columns as the original (Date/Type/Value/Source), sourced from `iocs` instead of `samples`, header text changed:
```html
<h3 class="section-heading">IOCs in this campaign</h3>
<div class="card mb-4">
	<div class="card-body">
		{% if iocs %}
		<p style="margin-bottom:0.75rem; color:#737373; font-size:14px; font-family:'Rubik',sans-serif;">Showing up to 25 IOCs (the campaigns API caps each campaign's published list at 25). Live JSON: <a href="https://api.tweetfeed.live/v1/campaigns" target="_blank" rel="noopener noreferrer"><code>api.tweetfeed.live/v1/campaigns</code></a>.</p>
		<div class="table-responsive">
			<table class="table table-sm" style="table-layout:fixed; width:100%; min-width:720px; margin-bottom:0;">
				<colgroup>
					<col style="width:90px;"><col style="width:60px;"><col style="width:100%;"><col style="width:100px;">
				</colgroup>
				<thead><tr><th>Date</th><th>Type</th><th>Value</th><th>Source</th></tr></thead>
				<tbody>
					{% for s in iocs %}<tr>
						<td style="font-size:12px; color:#737373; vertical-align:middle; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ s.date_short }}</td>
						<td style="vertical-align:middle;"><span style="font-size:11px; padding:2px 6px; background:{{ s.type_color }}; color:{{ s.type_text_color }}; border-radius:3px;">{{ s.type }}</span></td>
						<td style="font-family:monospace; font-size:13px; vertical-align:middle; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{{ s.value_full }}"><i class="tf-copy far fa-copy" data-copy="{{ s.value_full }}" style="margin-right:0.4rem;"></i>{{ s.value_display }}</td>
						<td style="font-size:12px; vertical-align:middle; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"><a href="https://x.com/{{ s.user }}" target="_blank" rel="noopener noreferrer">@{{ s.user }}</a></td>
					</tr>
					{% endfor %}</tbody>
			</table>
		</div>
		{% else %}
		<p style="margin-bottom:0; color:#737373; font-size:14px; font-family:'Rubik',sans-serif;">No IOC rows available for this campaign.</p>
		{% endif %}
	</div>
</div>
```

- [ ] **Step 9: Replace "Related tags" with "Explore more"**

```html
<h3 class="section-heading">Explore more</h3>
<div class="card mb-4">
	<div class="card-body">
		<p style="color:#737373; font-size:14px; font-family:'Rubik',sans-serif; margin-bottom:0;">See all active campaigns on the <a href="../../campaigns/" class="text-decoration-none">Campaigns</a> page, or browse the full <a href="../../feeds/" class="text-decoration-none">IOC feed</a>.</p>
	</div>
</div>
```

- [ ] **Step 10: Delete the FAQ `<section>` block entirely** (Global Constraints: FAQ out of scope for the prototype — also drops the `faq_jsonld` reference, consistent with Step 2 deleting that `<script>` tag).

- [ ] **Step 11: Replace the License paragraph**

```html
<h3 class="section-heading">License</h3>
<p style="color: #737373;font-size: 16px;font-family: 'Rubik', sans-serif;">
	This campaign's IOC data: <b>CC0 1.0 Public Domain</b>. No attribution required, no warranty. Campaign descriptions are AI-generated from the underlying IOC data and may contain errors — verify before acting on them. Source code for the pipeline:
	<a target="_blank" rel="noopener noreferrer" href="https://github.com/0xDanielLopez/TweetFeed">github.com/0xDanielLopez/TweetFeed</a> (MIT).
</p>
```

- [ ] **Step 12: Leave nav, both footers, and the closing `<script>` tags byte-identical** to `tag_page.html.j2` — no campaign-specific changes needed there (relative paths `../../` are correct at `campaigns/<id>/index.html`, same depth as `tag/<slug>/index.html`).

- [ ] **Step 13: Verify the template parses as valid Jinja2 (syntax only, no real data yet)**

```bash
cd /home/daniel/code/tweetfeed/frontend-stage
python3 -c "
from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(loader=FileSystemLoader('scripts/templates'), autoescape=select_autoescape([]))
env.get_template('campaign_page.html.j2')
print('OK: template parses')
"
```
Expected: `OK: template parses` (a `TemplateSyntaxError` means an unclosed `{% %}` or `{{ }}` from the edits above — fix before moving on).

- [ ] **Step 14: Commit**

```bash
git add scripts/templates/campaign_page.html.j2
git commit -m "feat: add campaign permalink page template (prototype)"
```

---

### Task 2: Generator script

**Files:**
- Create: `scripts/generate_campaign_pages.py`

**Interfaces:**
- Consumes: `scripts/templates/campaign_page.html.j2` (Task 1's template, exact variable names as documented in Task 1's Interfaces block)
- Produces: `campaigns/<id>/index.html` files on disk (one per generated campaign); prints a per-campaign `[ok]`/`[skip]` summary line to stdout, matching `regen_tag_pages.py`'s log format.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Generate campaign permalink pages under campaigns/<id>/index.html.

PROTOTYPE (2026-08-12): manual, stage-only generation of the top-N campaigns
by ioc_count. Not wired into regen-landing-pages.yml or any cron. Re-run by
hand: `python3 scripts/generate_campaign_pages.py`.

Reads live https://api.tweetfeed.live/v1/campaigns, renders
templates/campaign_page.html.j2 for the N campaigns with the highest
ioc_count, writes campaigns/<id>/index.html. Skips a campaign silently (with
a stderr line) on a per-item render error so one bad campaign doesn't stop
the run - same pattern as regen_tag_pages.py.
"""
import datetime
import html
import json
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CAMPAIGNS_DIR = REPO_ROOT / "campaigns"
IS_STAGE = not (REPO_ROOT / "CNAME").is_file()
API_URL = "https://api.tweetfeed.live/v1/campaigns"
HTTP_TIMEOUT = 30
TOP_N = 10
MAX_TITLE_DOMAINS = 3
MAX_CONTEXT_CHARS = 600
MAX_META_DESC_CHARS = 155

TYPE_COLORS = {
    "url": ("#0026E6", "white"),
    "domain": ("#3399FF", "white"),
    "ip": ("#02bf0f", "white"),
    "sha256": ("#FFC34D", "#1c1c1c"),
    "md5": ("#FFC34D", "#1c1c1c"),
}


def fetch_campaigns():
    resp = requests.get(API_URL, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("campaigns", [])


def js_encode_uri_component(s):
    """Mirror JS encodeURIComponent(), matching regen_tag_pages.py's helper
    of the same name (kept private to this script - no shared module exists
    between the two generators yet, would be premature for a 2-script repo)."""
    return quote(s, safe="!*'()~")


def build_title(campaign):
    domains = campaign.get("anchors", {}).get("registered_domains", [])
    if domains:
        shown = domains[:MAX_TITLE_DOMAINS]
        title = ", ".join(shown)
        if len(domains) > MAX_TITLE_DOMAINS:
            title += f" and {len(domains) - MAX_TITLE_DOMAINS} more"
    else:
        # No domain anchors (tag- or path-pattern-clustered campaign) - fall
        # back to a short context excerpt so the title is never empty.
        context = campaign.get("context", "").strip()
        title = context[:80] + ("..." if len(context) > 80 else "")
        if not title:
            title = campaign["id"]
    return f"{title} — Campaign tracked by TweetFeed ({campaign.get('ioc_count', 0)} IOCs)"


def build_meta_description(campaign):
    context = campaign.get("context", "").strip()
    if len(context) <= MAX_META_DESC_CHARS:
        return context
    truncated = context[:MAX_META_DESC_CHARS].rsplit(" ", 1)[0]
    return truncated + "..."


def format_domain(value):
    val_display = value[:60] + "..." if len(value) > 60 else value
    return {
        "value_full": html.escape(value, quote=True),
        "value_display": html.escape(val_display, quote=True),
    }


def format_ioc(row):
    try:
        ts = datetime.datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S")
        date_short = ts.strftime("%b %d, %H:%M")
    except (ValueError, KeyError):
        date_short = row.get("date", "")
    color, text_color = TYPE_COLORS.get(row.get("type", ""), ("#737373", "white"))
    val = row.get("value", "")
    val_display = val[:60] + "..." if len(val) > 60 else val
    return {
        "date_short": html.escape(date_short, quote=True),
        "type": html.escape(row.get("type", ""), quote=True),
        "type_color": color,
        "type_text_color": text_color,
        "value_full": html.escape(val, quote=True),
        "value_display": html.escape(val_display, quote=True),
        "value_query": html.escape(js_encode_uri_component(val), quote=True),
        "user": html.escape(row.get("user", ""), quote=True),
    }


def build_webpage_jsonld(campaign, title, meta_description):
    payload = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": f"https://tweetfeed.live/campaigns/{campaign['id']}/",
        "description": meta_description,
        "isPartOf": {"@id": "https://tweetfeed.live/#organization"},
        "inLanguage": "en",
    }
    s = json.dumps(payload, indent="\t", ensure_ascii=False)
    lines = s.split("\n")
    return "\n".join([lines[0]] + ["\t" + line for line in lines[1:]])


def render_campaign(campaign, env, generated_at_str):
    title = build_title(campaign)
    meta_description = build_meta_description(campaign)
    context_raw = campaign.get("context", "").strip()
    context_html = html.escape(context_raw, quote=True)

    domains = [format_domain(d) for d in campaign.get("anchors", {}).get("registered_domains", [])]
    iocs = [format_ioc(r) for r in campaign.get("iocs", [])]

    c = {
        "id": campaign["id"],
        "title": html.escape(title, quote=True),
        "meta_description": html.escape(meta_description, quote=True),
        "context_html": context_html,
        "confidence": html.escape(campaign.get("confidence", "unknown"), quote=True),
        "first_seen": html.escape(campaign.get("first_seen", ""), quote=True),
        "ioc_count": campaign.get("ioc_count", 0),
        "domains": domains,
        "generated_at_str": generated_at_str,
    }

    template = env.get_template("campaign_page.html.j2")
    return template.render(
        c=c,
        iocs=iocs,
        webpage_jsonld=build_webpage_jsonld(campaign, title, meta_description),
        noindex=IS_STAGE,
    )


def main():
    campaigns = fetch_campaigns()
    campaigns.sort(key=lambda c: c.get("ioc_count", 0), reverse=True)
    top = campaigns[:TOP_N]

    generated_at_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    env = Environment(
        loader=FileSystemLoader(SCRIPT_DIR / "templates"),
        autoescape=select_autoescape([]),
        trim_blocks=False,
        lstrip_blocks=False,
    )

    written = 0
    skipped = 0
    for campaign in top:
        cid = campaign.get("id", "<missing-id>")
        try:
            page_html = render_campaign(campaign, env, generated_at_str)
            out_dir = CAMPAIGNS_DIR / cid
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.html").write_text(page_html, encoding="utf-8")
            written += 1
            print(f"  [ok]   campaigns/{cid}/  (ioc_count={campaign.get('ioc_count')})")
        except Exception as e:
            skipped += 1
            print(f"  [skip] campaigns/{cid}: {type(e).__name__}: {e}", file=sys.stderr)

    print(f"\nWrote {written}/{len(top)} campaign pages ({skipped} skipped).")
    return 0 if written > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify `requests` and `jinja2` are available in the environment you'll run this with**

```bash
cd /home/daniel/code/tweetfeed/frontend-stage
python3 -c "import requests, jinja2; print('deps OK')"
```
Expected: `deps OK`. If it fails, check whether this repo has a venv (`regen_tag_pages.py` already depends on both, so one likely already exists or these are on the system Python used by `regen-landing-pages.yml`'s CI — check `.github/workflows/regen-landing-pages.yml` for its `pip install` line and mirror it locally if needed).

- [ ] **Step 3: Commit the script (before running it, so the diff is reviewable independent of its output)**

```bash
git add scripts/generate_campaign_pages.py
git commit -m "feat: add campaign page generator script (prototype)"
```

---

### Task 3: Generate, verify, ship to stage

**Files:**
- Create: `campaigns/<id>/index.html` (8-10 of these, exact ids depend on today's live API response)
- No modifications to any existing file.

**Interfaces:**
- Consumes: Task 2's `scripts/generate_campaign_pages.py`
- Produces: nothing further downstream (leaf task for this prototype's scope)

- [ ] **Step 1: Run the generator**

```bash
cd /home/daniel/code/tweetfeed/frontend-stage
python3 scripts/generate_campaign_pages.py
```
Expected: `Wrote 8/8 campaign pages (0 skipped).` (or however many campaigns the live API currently returns, up to `TOP_N=10` — the exact count depends on how many of the 22 active campaigns exist right now; if it's fewer than 10 total, all get pages).

- [ ] **Step 2: Spot-check the output structurally**

```bash
find campaigns -maxdepth 2 -name index.html -newer scripts/generate_campaign_pages.py
```
Expected: one path per campaign written, e.g. `campaigns/tfc-9747b61b0a0b/index.html`.

For 2 of the generated pages (pick one with domain anchors and one without, if any exist), check the rendered HTML is well-formed and the key substitutions landed:
```bash
python3 -c "
from html.parser import HTMLParser
import sys
class P(HTMLParser):
    def error(self, msg): print('PARSE ERROR:', msg)
for p in sys.argv[1:]:
    with open(p) as f:
        P().feed(f.read())
    print(f'{p}: parsed OK')
" campaigns/*/index.html
```
Expected: `parsed OK` for every generated file, no `PARSE ERROR` lines.

- [ ] **Step 3: Run the project's own consistency checker to make sure nothing site-wide broke**

```bash
python3 scripts/check_consistency.py
```
Expected: same pass/fail result as before this change (the new pages aren't in `MAIN_PAGES` so this script won't specifically validate them, but it must not newly fail on anything else).

- [ ] **Step 4: Visual check on stage, for the 3-4 most structurally different generated pages** (one with many domain anchors, one with few/none, one with a long `context`, one with a short one)

Use the claude-in-chrome or Playwright MCP tools (load via ToolSearch if deferred) to serve the repo locally (`python3 -m http.server 8080` from the repo root) and screenshot each of the chosen `campaigns/<id>/` pages at both desktop and mobile widths. Look for:
- No broken card/grid layout (compare against `tag/<any-slug>/` for a reference).
- No two-footer overlap at the 768-991px breakpoint (this repo has a known d-lg-block/d-lg-none bug class — confirm both footers use `d-lg-*`, not `d-md-*`, by grepping the generated HTML, not just eyeballing).
- Domain/IOC tables don't overflow their container.
- The stat-row cards render three across on desktop, stack sanely on mobile.
- `og:image:alt`, title, and meta description are non-empty and don't contain unescaped HTML artifacts (view source, not just rendered output).

If anything looks broken, fix the template (Task 1) or the script's data-shaping (Task 2), regenerate (Step 1), and re-check — do not proceed to Step 5 with a known visual defect.

- [ ] **Step 5: Commit the generated pages and push to stage**

```bash
git add campaigns/
git status  # confirm ONLY campaigns/<id>/index.html files staged, nothing else
git commit -m "feat: generate 8-10 campaign permalink pages (prototype, stage-only)"
git push origin main
```

- [ ] **Step 6: Verify live on stage**

```bash
# Replace <stage-base-url> with the actual GH Pages stage URL (0xdaniellopez.github.io/tweetfeed-stage/) and <id> with one of the generated ids
curl -s -o /dev/null -w "%{http_code}\n" "https://0xdaniellopez.github.io/tweetfeed-stage/campaigns/<id>/"
```
Expected: `200` (allow ~30-70s after push for GH Pages Varnish to pick it up per the project's known cache-propagation timing).

- [ ] **Step 7: Report back to the user**

Summarize: how many pages were generated, which 2-3 you visually verified and how, the live stage URL(s) to look at, file size / page weight if notably large, and an explicit reminder that this is stage-only and unwired from any cron per the approved scope — prod rollout, `/campaigns/` internal linking, and daily automation are separate follow-up decisions, not part of this task.
