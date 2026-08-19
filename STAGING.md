# Staging repo - NOT production

This is the **staging** environment for TweetFeed frontend.

- **Production**: https://tweetfeed.live (repo: [TweetFeed/TweetFeed.github.io](https://github.com/TweetFeed/TweetFeed.github.io))
- **Staging URL**: https://0xdaniellopez.github.io/tweetfeed-stage/
- **Data source**: `0xDanielLopez/tweetfeed-data-stage` (see `js/config.js`, `DATA_BASE`), NOT the
  prod data repo. It is a snapshot, so home/dashboard/graphs/researchers/trends/feeds/changelog/
  about/search render whatever date that snapshot was taken on - do not sign off a data-shaped
  change here assuming live prod numbers. The five `malicious-*` pages differ again: they read
  `api.tweetfeed.live`, which is always live.

This repo exists to test frontend changes before promoting them to production. Do not rely on its content or URL for any real use.
