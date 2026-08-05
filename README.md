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
| `/privacy` | `site/privacy.html` | **App Store "Privacy Policy URL"** (required) |
| `/support` | `site/support.html` | **App Store "Support URL"** (required) |

Both required URLs are checked by App Review, so they must stay reachable.

## Privacy policy is generated — don't hand-edit

`site/privacy.html` is generated from `PRIVACY.md` in the **app** repo
(`~/Projects/garage-buddy`), which is the source of truth. Editing the HTML
directly will be silently overwritten the next time it's regenerated. Change
`PRIVACY.md`, regenerate, and commit both.

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
