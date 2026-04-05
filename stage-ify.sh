#!/bin/bash
# stage-ify.sh - Rewrites data fetch URLs to point to the stage data repo.
# Run this after pulling updates from prod frontend (TweetFeed/TweetFeed.github.io).
#
# Changes only ACTUAL data fetches (jQuery $.ajax url: and $.get calls).
# User-facing links, code examples (<pre>), and KQL snippets stay as prod URLs,
# so the staging UI mirrors prod appearance while fetching from the stage data repo.

set -e
cd "$(dirname "$0")"

PROD_BASE='raw.githubusercontent.com/0xDanielLopez/TweetFeed/master'
STAGE_BASE='raw.githubusercontent.com/0xDanielLopez/tweetfeed-data-stage/master'

echo "Rewriting fetch URLs: $PROD_BASE -> $STAGE_BASE"

# Pattern 1: url: 'https://...'  (jQuery $.ajax)
find . -name "*.html" -not -path './.git/*' -exec sed -i -E "s|(url:\s*')https://${PROD_BASE}|\1https://${STAGE_BASE}|g" {} \;

# Pattern 2: $.get('https://...'  (jQuery $.get)
find . -name "*.html" -not -path './.git/*' -exec sed -i -E "s|(\\\$\\.get\\(')https://${PROD_BASE}|\1https://${STAGE_BASE}|g" {} \;

echo "Done. Verify with: git diff --stat"
