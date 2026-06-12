# sharppicks.ai apex routing

## Canonical serving path

The sharppicks.ai apex is served by **Cloudflare Pages** from the
`landing/` directory of this repo. The Pages project should auto-deploy
on every push to the `main` branch.

The Flask + Railway service serves the `app.sharppicks.ai` subdomain
(iOS Capacitor app shell, React SPA, signed-in user routes) and the
`/api/*` endpoints. Flask's `@app.route('/')` returns the React SPA's
`dist/index.html` for sessions and `?view=signin|signup` parameters,
and historically fell back to `templates/app-landing.html` for
anonymous visitors. **That fallback is no longer reachable from the
apex** since Pages always answers the apex now; it remains in code
only because Flask still answers `app.sharppicks.ai`. Do not delete
the Flask fallback route without separately confirming nothing on
`app.sharppicks.ai` depends on it.

## File ownership at the apex

| Path on `sharppicks.ai` | Served from | Source |
|-------------------------|-------------|--------|
| `/` | Pages | `landing/index.html` |
| `/blog/` and `/blog/<slug>` | Pages | `landing/blog/` |
| `/guide.html`, `/privacy.html`, `/terms.html`, `/disclaimer.html` | Pages | `landing/*.html` |
| `/robots.txt` | Pages | `landing/robots.txt` |
| `/llms.txt`, `/llms-full.txt` | Pages | `landing/llms.txt`, `landing/llms-full.txt` |
| `/sitemap.xml`, `/sitemap-pages.xml`, `/sitemap-content.xml` | Pages | `landing/sitemap*.xml` |
| `/404.html` (catch-all) | Pages | `landing/404.html` (per `_redirects`) |

The Flask `@app.route('/robots.txt')` handler that reads from
`landing/robots.txt` is still in `app.py` but only answers
`app.sharppicks.ai/robots.txt`. The Pages-served apex `robots.txt`
is the canonical SEO surface.

## Pages configuration files

- `landing/_headers` sets `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin
  -when-cross-origin` site-wide, and `Cache-Control: public, max-age
  =31536000, immutable` for `/assets/*`.
- `landing/_redirects` forces HTTPS + apex canonical
  (`www.sharppicks.ai` and the `http://` schemes 301 to
  `https://sharppicks.ai`), proxies `/app` to `https://app.sharppicks.ai`,
  and has a catch-all `* /404.html 404` to stop Pages from serving
  `index.html` on unmatched paths (a previous incident put phantom
  blog-slug URLs into GSC as canonical-tagged duplicates).

## What lives where, deliberately

`app.sharppicks.ai` is the iOS Capacitor + Android container's
runtime URL. Anything that ships in the iOS / Android bundle reads
its API and assets from there. The marketing site at the apex must
not depend on that subdomain being reachable; conversely the Flask
service must not assume the marketing site is reachable from the
SPA's perspective.

| Concern | Lives on | Notes |
|---------|----------|-------|
| Marketing copy, blog, journal, tools, FAQs | `sharppicks.ai` (Pages) | SEO surface |
| iOS / Android app shell | `app.sharppicks.ai` (Flask/Railway) | Capacitor `server.url` |
| React SPA | `app.sharppicks.ai/` (Flask/Railway) | served by Flask's `/` route after auth |
| Public API (`/api/public/*`) | `app.sharppicks.ai` (Flask/Railway) | consumed by HQ Worker + iOS app |
| Admin (`/admin`) | `app.sharppicks.ai` (Flask/Railway) | superuser-only |
| AI crawler files (`/robots.txt`, `/llms.txt`, `/llms-full.txt`) | `sharppicks.ai` (Pages) | apex is the SEO + LLM-citation surface |

## Why this split, briefly

- The marketing site is a high-cache static surface that should not
  share a request lifecycle with the API or the model pipeline.
  Cloudflare Pages serves it from the edge cache.
- The app shell needs session state, OAuth, push tokens, and the
  Flask runtime. Putting it behind its own subdomain keeps the
  marketing site's cache-friendly headers from leaking into
  authenticated requests.
- iOS App Store guidelines treat `app.sharppicks.ai` as the app's
  origin for in-app purchase reconciliation and the App Store
  redirect on the Apple bridge email; changing the apex of the iOS
  Capacitor shell would force a re-archive and re-review.

## How to deploy changes to the marketing site

1. Edit files under `landing/` on the `main` branch.
2. Push to GitHub.
3. Cloudflare Pages should redeploy automatically within ~60 seconds.
4. Verify with five consecutive fetches of the changed URL; they
   should all return identical content with the new bytes.

If Pages does not auto-deploy, check the Pages project's
**Settings → Builds & deployments → Production branch** is set to
`main`, and **Settings → Builds & deployments → Build configuration**
points to the GitHub repository this file lives in.

## How to deploy changes to the API / app shell

This is the Flask/Railway path. Push to `main`, Railway redeploys
automatically; verify via the Railway dashboard's Deployments tab.
Changes to `landing/` do NOT need Railway to redeploy because the
apex serves from Pages.

## When this routing fails

The two known failure modes:

1. **Pages does not auto-deploy on push.** Symptom: file changes
   under `landing/` ship to GitHub `main` but the apex still serves
   the old version. Fix: manually trigger a Pages rebuild in the
   Cloudflare dashboard. Investigate the Git webhook on the Pages
   project.
2. **Cloudflare's managed `robots.txt` rule overrides the origin
   file.** Symptom: `landing/robots.txt` says one thing, the served
   `https://sharppicks.ai/robots.txt` shows a Cloudflare-prepended
   block with AI-bot Disallow rules and a different Content-Signal
   line. Fix: in the Cloudflare dashboard, under
   **Security → Bots → AI Crawl Control → Managed robots.txt**,
   toggle off, then **Caching → Configuration → Purge by URL** for
   `https://sharppicks.ai/robots.txt`. The toggle and the cache
   purge are both required.
