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

Caddy in a container (`Dockerfile` + `Caddyfile`), deployed on Railway.
`try_files` provides clean URLs, so `/privacy` and `/privacy.html` both work.
Railway injects `$PORT`; TLS for the custom domain is handled at Railway's edge,
so `auto_https` is off.

Local check (needs Docker running):

```sh
docker build -t gb-site .
docker run --rm -e PORT=8080 -p 8099:8080 gb-site
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8099/privacy   # expect 200
```

## Domain

`garagebuddy.fulgent.org` — Railway service + DreamHost DNS, wired with the
`register-domain` skill. Re-running that skill is safe; DNS records are upserted.
