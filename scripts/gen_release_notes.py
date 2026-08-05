#!/usr/bin/env python3
"""Generate site/release-notes.html from the app repo's CHANGELOG.md.

The changelog in the app repo is the source of truth. This script renders it;
it never edits it. Re-run after every release and commit the result:

    python3 scripts/gen_release_notes.py
    python3 scripts/gen_release_notes.py --changelog /path/to/CHANGELOG.md

There is no markdown library on this machine and adding a dependency for one
page isn't worth it, so this handles exactly the subset the changelog uses:
`## [version] - date` headings, `### Category` subheadings, `-` bullets with
two-space-indented continuation lines, nested `  -` bullets, `**bold**`,
`` `code` `` and `[text](url)`. Anything else passes through escaped.
"""
import argparse, html, os, re, sys

APP_NAME = "Garage Buddy"
DEFAULT_CHANGELOG = "../garage-buddy/CHANGELOG.md"
OUT = "site/release-notes.html"
# Versions below this were TestFlight-only and are folded away behind a
# disclosure so the page leads with what shipped. None = show everything.
COLLAPSE_BELOW = (1, 0, 0)
NAV = [("/", APP_NAME), ("/release-notes", "Release Notes"),
       ("/support", "Support"), ("/privacy", "Privacy"), ("/terms", "Terms")]

VER_RE = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\S+))?(.*)$")
CAT_RE = re.compile(r"^### (.+)$")


def vtuple(v):
    parts = []
    for p in v.split("."):
        m = re.match(r"\d+", p)
        parts.append(int(m.group()) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def inline(text):
    """Escape, then apply the inline markdown the changelog actually uses."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def parse(md):
    """-> [ {version, date, note, sections: [ {category, items: [str]} ]} ]"""
    releases, rel, sec = [], None, None

    def flush_sec():
        nonlocal sec
        if rel is not None and sec and sec["items"]:
            rel["sections"].append(sec)
        sec = None

    for raw in md.splitlines():
        line = raw.rstrip()
        m = VER_RE.match(line)
        if m:
            flush_sec()
            if rel:
                releases.append(rel)
            version, date, note = m.group(1), m.group(2) or "", m.group(3).strip()
            rel = {"version": version, "date": date, "note": note, "sections": []}
            sec = {"category": "", "items": []}
            continue
        if rel is None:
            continue                      # intro prose above the first release
        m = CAT_RE.match(line)
        if m:
            flush_sec()
            sec = {"category": m.group(1).strip(), "items": []}
            continue
        if sec is None:
            sec = {"category": "", "items": []}
        if re.match(r"^\s{2,}- ", line):                       # nested bullet
            if sec["items"]:
                sec["items"][-1] += "\n• " + line.strip()[2:]
            continue
        if line.startswith("- "):                              # new bullet
            sec["items"].append(line[2:])
            continue
        if line.startswith("  ") and line.strip() and sec["items"]:
            sec["items"][-1] += " " + line.strip()             # continuation
            continue
    flush_sec()
    if rel:
        releases.append(rel)
    return releases


def render_item(item):
    head, *rest = item.split("\n• ")
    out = f"  <li>{inline(head)}"
    if rest:
        out += "\n    <ul>" + "".join(f"\n      <li>{inline(r)}</li>"
                                      for r in rest) + "\n    </ul>\n  "
    return out + "</li>"


def render_release(r):
    anchor = "v" + re.sub(r"[^0-9a-zA-Z]+", "-", r["version"])
    date = f'<span class="ver-date">{html.escape(r["date"])}</span>' if r["date"] else ""
    parts = [f'<section class="release">',
             f'  <h2 id="{anchor}">{html.escape(r["version"])} {date}</h2>']
    for s in r["sections"]:
        if s["category"]:
            slug = re.sub(r"[^a-z]+", "", s["category"].lower())
            parts.append(f'  <h3 class="cat cat-{slug}">'
                         f'{html.escape(s["category"])}</h3>')
        parts.append("  <ul>")
        parts.extend(render_item(i) for i in s["items"])
        parts.append("  </ul>")
    parts.append("</section>")
    return "\n".join(parts)


def build(releases):
    nav = "\n".join(
        f'  <a href="{href}"{" aria-current=\"page\"" if href == "/release-notes" else ""}>'
        f'{label}</a>' for href, label in NAV)

    shipped = [r for r in releases
               if COLLAPSE_BELOW is None or vtuple(r["version"]) >= COLLAPSE_BELOW]
    early = [r for r in releases if r not in shipped]

    latest = shipped[0] if shipped else (releases[0] if releases else None)
    latest_html = ""
    if latest:
        d = f' &middot; {html.escape(latest["date"])}' if latest["date"] else ""
        latest_html = (f'<p class="tagline">Current version '
                       f'<strong>{html.escape(latest["version"])}</strong>{d}</p>')

    body = "\n\n".join(render_release(r) for r in shipped)
    if early:
        body += ('\n\n<details class="early">\n'
                 f'  <summary>Earlier pre-release versions '
                 f'({len(early)} TestFlight builds)</summary>\n\n'
                 + "\n\n".join(render_release(r) for r in early)
                 + "\n</details>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{APP_NAME} — Release Notes</title>
<meta name="description" content="What changed in every version of {APP_NAME} — new features, fixes, and improvements.">
<link rel="stylesheet" href="/style.css">
</head>
<body>

<nav>
{nav}
</nav>

<h1>Release Notes</h1>
{latest_html}

<p class="lede">Everything that changed in {APP_NAME}, newest first.</p>

{body}

<footer>
  <p>{APP_NAME} &middot; <a href="/support">Support</a> &middot;
  <a href="/privacy">Privacy Policy</a> &middot; <a href="/terms">Terms</a><br>
  An <a href="https://odhllc.com">ODH LLC</a> app.</p>
</footer>

</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changelog", default=DEFAULT_CHANGELOG)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = args.changelog if os.path.isabs(args.changelog) else \
        os.path.normpath(os.path.join(root, args.changelog))
    if not os.path.exists(src):
        sys.exit(f"changelog not found: {src}")

    releases = parse(open(src, encoding="utf-8").read())
    if not releases:
        sys.exit(f"no releases parsed from {src}")

    out = os.path.join(root, args.out)
    open(out, "w", encoding="utf-8").write(build(releases))
    items = sum(len(s["items"]) for r in releases for s in r["sections"])
    print(f"{os.path.relpath(out, root)}: {len(releases)} releases, "
          f"{items} entries (latest {releases[0]['version']}) from {src}")


if __name__ == "__main__":
    main()
