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
MAX_TITLE_CONTEXT_CHARS = 60
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
        # Truncate on a word boundary (like build_meta_description) so the
        # H1/<title> never ends mid-word.
        context = campaign.get("context", "").strip()
        if len(context) <= MAX_TITLE_CONTEXT_CHARS:
            title = context
        else:
            title = context[:MAX_TITLE_CONTEXT_CHARS].rsplit(" ", 1)[0] + "..."
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
