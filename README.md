# garage-buddy-site

The public web pages for **Garage Buddy** — deliberately a separate repo from
the iOS app.

**Why separate:** the app repo's `main` triggers an Xcode Cloud build on every
push. Keeping the website here means editing a paragraph of copy doesn't burn a
five-minute iOS build (and an app fix doesn't redeploy the website).

## Pages

| Path | File | Used for |
|---|---|---|
| `/` | `site/index.html` | Landing page |
| `/features` | `site/features.html` | Full feature documentation, hand-written from the app code |
| `/release-notes` | `site/release-notes.html` | Version history — **generated**, don't hand-edit |
| `/privacy` | `site/privacy.html` | **App Store "Privacy Policy URL"** (required) |
| `/support` | `site/support.html` | **App Store "Support URL"** (required) |
| `/terms` | `site/terms.html` | Terms of service |

Both required URLs are checked by App Review, so they must stay reachable.

## Release notes are generated — don't hand-edit

`site/release-notes.html` is built from `CHANGELOG.md` in the **app** repo
(`~/Projects/garage-buddy`), which is the source of truth. **Re-run after every
release**, as part of the same commit that bumps the version:

```sh
python3 scripts/gen_release_notes.py            # reads ../garage-buddy/CHANGELOG.md
python3 scripts/gen_release_notes.py --changelog /elsewhere/CHANGELOG.md
```

Versions below `1.0.0` were TestFlight-only, so they're folded behind a
disclosure rather than leading the page — see `COLLAPSE_BELOW` in the script.

The script implements only the markdown subset the changelog actually uses
(`## [version] - date`, `### Category`, bullets with continuation lines, nested
bullets, `**bold**`, `` `code` ``, links). That's deliberate: there's no
markdown library on the machine, and one page doesn't justify a dependency. If
the changelog starts using new syntax, extend `inline()` — anything unhandled
is HTML-escaped and passes through as literal text rather than breaking.

`scripts/gen_release_notes.py` is duplicated in
[`workout-buddy-site`](https://github.com/shuffman/workout-buddy-site) with a
different config block, for the same reason `style.css` is: two self-contained
repos beat a shared package for something this small.

## The features page is hand-written — check it on feature releases

`site/features.html` documents every feature, written by reading the app's
screens and models (last checked against **1.10.1**, and garage-buddy-web as of its 1.9.1 parity work). Unlike the release notes
it isn't generated, so it drifts: when a release adds, removes or renames
something user-visible, update the matching section. UI labels in bold are
quoted from the app, so a renamed button is worth a grep here.

Features that need the user's own AI key are marked with `<span class="tag">AI
key</span>` — a text label, not a colour.

## The odometer hero

`site/odometer.js` draws the landing page's opening element: an odometer whose
drums roll and settle right-to-left, the ones place spinning longest. The app's
first move is photographing an odometer and reading the number off it, so the
page opens with that rather than with a paragraph.

The reading (`087421`) is **illustrative, not real data**. Reduced-motion users
get the settled reading immediately with no roll.

## Screenshots are captured from sample data — never by hand

`site/shots/*.webp` come from `scripts/capture_screenshots.sh`, which builds the
iOS app, launches it in a dedicated simulator ("GB Site Shots") with
`-seedSampleData`, and captures the web app's `?demo=1` fleet with headless
Chrome. Re-run it after a release that changes what those screens look like:

```sh
scripts/capture_screenshots.sh
APP_REPO=/path/to/garage-buddy scripts/capture_screenshots.sh   # a branch/worktree
```

**Sample data only.** The Mac App Store listing once shipped a real garage
because a capture picked up live data. Before committing, look at every image:
the phone shots must show the ten sample cars (Daily Civic … Old Accord), the
web shots the demo fleet (The wagon, 2019 Toyota Tacoma, Commuter).

The app-side launch arguments the script needs — a deterministic
`-seedSampleData`, `-openCar <name>` and `-quickActionLog` — were added on the
app repo's `screenshot-open-car` branch (2026-09-16). Until that is merged,
point `APP_REPO` at a checkout of it.

Known quirks, both from how the demo runs rather than the pages:
- The Reports shot shows a **Syncing** chip: `-seedReports` queues uploads a
  seeded run never sends. It's used on the features page only, not the landing
  page.
- Web demo car `car-0` ("The wagon") has a deliberate odometer typo, so the
  script looks up the Tacoma by name instead.

Phone shots are published at 600px wide, web shots at 1280px, as WebP (~20–40
KB each). Markup is a `ul.shots` with `shots--phone` or `shots--wide`; alt text
is not optional.

## Privacy policy is generated — don't hand-edit

`site/privacy.html` is generated from `PRIVACY.md` in the **app** repo
(`~/Projects/garage-buddy`), which is the source of truth and covers the app
*and* `web.garage-buddy.app`. Change `PRIVACY.md`, then:

```sh
python3 scripts/gen_privacy.py            # reads ../garage-buddy/PRIVACY.md
```

and commit both. The script shares `inline()` and the nav with
`gen_release_notes.py`. Until 2026-09-16 there was no script — the page had
been converted once by hand and was two months behind the policy.

## Serving

The same `site/` directory is published to **two** places. Both are live;
neither depends on the other.

### GitHub Pages — `garage-buddy.app` (primary)

`.github/workflows/pages.yml` uploads `site/` on every push to `main`. TLS is
GitHub's (Let's Encrypt), issued automatically for the custom domain.

The custom domain (`garage-buddy.app`) lives in the **repo's Pages setting**,
not in the repo contents:

```sh
gh api -X PUT repos/shuffman/garage-buddy-site/pages -f cname=garage-buddy.app
```

`site/CNAME` is kept as documentation and is **inert for Actions-based
deploys** — verified 2026-08-05: three successful deploys with the file present
left the Pages `cname` setting at `null` until it was set explicitly via the
API. (The file *is* honoured by the legacy branch build, which is where the
"just commit a CNAME" advice comes from.)

### Set the domain AFTER DNS points at GitHub

Order matters. If the custom domain is set while DNS still points elsewhere,
validation fails, GitHub never requests a Let's Encrypt certificate, and it does
**not** retry on any useful timescale — `https_certificate` stays absent from
the API response entirely and HTTPS serves GitHub's default cert, failing with
`no alternative certificate subject name matches target host name`.

Re-`PUT`ting the same `cname` does not fix it. Clear the domain and set it
again:

```sh
echo '{"cname":null}' | gh api -X PUT repos/shuffman/garage-buddy-site/pages --input -
gh api -X PUT repos/shuffman/garage-buddy-site/pages -f cname=garage-buddy.app
```

The certificate then moves `authorization_pending` → `authorized` → `approved`
within about a minute. Enable enforcement afterwards with
`-F https_enforced=true`.

Clean URLs work without configuration: Pages resolves `/privacy` to
`privacy.html` on its own, so no `try_files` equivalent is needed.

**Pages cannot set HTTP headers.** The `header` block in the `Caddyfile`
(`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) applies to the
Railway deploy only — those headers are simply absent on `garage-buddy.app`.
There is no way to add them on GitHub Pages; moving to Cloudflare Workers
(`_headers` file) is the only fix if they're ever required.

### Railway + Caddy — `garagebuddy.fulgent.org` (legacy)

Caddy in a container (`Dockerfile` + `Caddyfile`). `try_files` provides clean
URLs. Railway injects `$PORT`; TLS is handled at Railway's edge, so
`auto_https` is off.

Local check (needs Docker running):

```sh
docker build -t gb-site .
docker run --rm -e PORT=8080 -p 8099:8080 gb-site
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8099/privacy   # expect 200
```

This deploy is kept because the **App Store Connect privacy and support URLs
still point at it**. Retire it only after those are switched to
`garage-buddy.app` and a new build has been reviewed against the new URLs.

## Domains

| Domain | Host | DNS |
|---|---|---|
| `garage-buddy.app` | GitHub Pages | **Cloudflare** — apex `A`/`AAAA` to GitHub, `www` `CNAME` to `shuffman.github.io` |
| `garagebuddy.fulgent.org` | Railway | DreamHost — wired with the `register-domain` skill |

`garage-buddy.app` DNS moved off DreamHost 2026-08-04: DreamHost's DNS API
returns `no_such_zone` for newly registered domains until the zone is
provisioned by hand in their panel. `fulgent.org` is unaffected and stays on
DreamHost — it's a long-established zone the API can already manage.

**Cloudflare records must stay DNS-only (grey cloud).** A proxied record breaks
GitHub's HTTP-01 challenge, so the certificate never issues — and because
`.app` is HSTS-preloaded, no certificate means the site is flatly unreachable
rather than merely insecure.

`.app` is on the HSTS preload list, so `garage-buddy.app` is HTTPS-only in
browsers — there is no plain-HTTP fallback while a certificate is provisioning.
