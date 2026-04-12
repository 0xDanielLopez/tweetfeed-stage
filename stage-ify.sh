#!/bin/bash
# stage-ify.sh - Rewrites data fetch URLs to point to the stage data repo.
# Run this after pulling updates from prod frontend (TweetFeed/TweetFeed.github.io).
#
# All AJAX/fetch calls now use TweetFeed.dataUrl() from config.js,
# so only config.js needs to be patched.

set -e
cd "$(dirname "$0")"

PROD_BASE='https://raw.githubusercontent.com/0xDanielLopez/TweetFeed/master'
STAGE_BASE='https://raw.githubusercontent.com/0xDanielLopez/tweetfeed-data-stage/master'

echo "Rewriting DATA_BASE in js/config.js: prod -> stage"
sed -i "s|${PROD_BASE}|${STAGE_BASE}|g" js/config.js

# Also catch any straggler hardcoded URLs in HTML files (from syncing prod)
echo "Checking for straggler hardcoded URLs in HTML files..."
PROD_RAW='raw.githubusercontent.com/0xDanielLopez/TweetFeed/master'
STAGE_RAW='raw.githubusercontent.com/0xDanielLopez/tweetfeed-data-stage/master'

# Pattern 1: url: 'https://...'  (jQuery $.ajax)
find . -name "*.html" -not -path './.git/*' -exec sed -i -E "s|(url:\s*')https://${PROD_RAW}|\1https://${STAGE_RAW}|g" {} \;

# Pattern 2: $.get('https://...'  (jQuery $.get)
find . -name "*.html" -not -path './.git/*' -exec sed -i -E "s|(\\\$\\.get\\(')https://${PROD_RAW}|\1https://${STAGE_RAW}|g" {} \;

# Pattern 3: TweetFeed.dataUrl calls that somehow have prod URLs (shouldn't happen)
find . -name "*.html" -not -path './.git/*' -exec sed -i -E "s|(\\\$\\.get\\()https://${PROD_RAW}|\1https://${STAGE_RAW}|g" {} \;

echo "Done. Verify with: git diff --stat"
