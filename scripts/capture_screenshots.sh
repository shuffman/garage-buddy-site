#!/bin/bash
# Captures the site's screenshots into site/shots/ from SAMPLE data only:
# the iOS app's -seedSampleData fleet and the web app's ?demo=1 fleet.
#
#   scripts/capture_screenshots.sh
#   APP_REPO=/path/to/garage-buddy WEB_REPO=/path/to/garage-buddy-web scripts/capture_screenshots.sh
#
# Needs from the app repo: -seedSampleData with fixed ids and seed, -openCar
# and -quickActionLog (all DEBUG-only). Needs cwebp (brew install webp) and
# Google Chrome.
#
# Look at every image before committing. The iOS shots must show the sample
# cars (Daily Civic, Odyssey, F-150, Model 3, Miata, 4Runner, Wrangler, 911,
# Bolt, Old Accord) and the web shots the demo fleet ("The wagon", "Commuter",
# demo@example.com). Anything else means real data reached a capture — stop.
set -euo pipefail

SITE="$(cd "$(dirname "$0")/.." && pwd)"
APP_REPO="${APP_REPO:-$SITE/../garage-buddy}"
WEB_REPO="${WEB_REPO:-$SITE/../garage-buddy-web}"
WORK="${TMPDIR:-/tmp}/gb-site-shots"
OUT="$SITE/site/shots"
SIM_NAME="GB Site Shots"         # a dedicated simulator, so no one else's is disturbed
BUNDLE="com.shuffman.carlog"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WEB_PORT=5199
WIDTH=600                        # published width; iPhone shots are 1206 wide raw
WEB_WIDTH=1280                   # web shots are 2560 wide raw (2x)

mkdir -p "$WORK/raw" "$OUT"

echo "==> Building the app (Debug, simulator) from $APP_REPO"
xcodebuild -project "$APP_REPO/CarLog.xcodeproj" -scheme CarLog -configuration Debug \
  -destination 'generic/platform=iOS Simulator' -derivedDataPath "$WORK/dd" build >/dev/null
APP=$(find "$WORK/dd/Build/Products/Debug-iphonesimulator" -maxdepth 1 -name '*.app' | head -1)

SIM=$(xcrun simctl list devices -j | python3 -c "
import json, sys
for devs in json.load(sys.stdin)['devices'].values():
    for d in devs:
        if d['name'] == '$SIM_NAME' and d['isAvailable']:
            print(d['udid']); sys.exit()")
[ -n "$SIM" ] || SIM=$(xcrun simctl create "$SIM_NAME" "iPhone 17 Pro")
# A fresh boot every run: a system alert left over from an earlier session
# (e.g. "Open in Garage Buddy?") would otherwise sit on top of every shot.
xcrun simctl shutdown "$SIM" 2>/dev/null || true
xcrun simctl boot "$SIM"
xcrun simctl bootstatus "$SIM" -b >/dev/null
# Reinstall so each run starts with an empty container: -seedReports queues
# uploads that a seeded run never sends, and they would otherwise show as a
# "Syncing" badge on every later shot.
xcrun simctl uninstall "$SIM" "$BUNDLE" 2>/dev/null || true
xcrun simctl install "$SIM" "$APP"
xcrun simctl ui "$SIM" appearance light
xcrun simctl status_bar "$SIM" override --time 9:41 --batteryState charged \
  --batteryLevel 100 --cellularBars 4 --wifiBars 3

phone() {
  local name="$1"; shift
  xcrun simctl launch --terminate-running-process "$SIM" "$BUNDLE" -seedSampleData "$@" >/dev/null
  sleep 10
  xcrun simctl io "$SIM" screenshot "$WORK/raw/$name.png" >/dev/null 2>&1
  echo "  $name"
}

echo "==> iPhone"
phone dashboard
phone garage     -startGarage
phone car        -startGarage -openCar "Daily Civic"
phone economy    -startMPG -chartRange 1Y
phone reports    -startReports -seedReports
phone entry      -quickActionLog
xcrun simctl terminate "$SIM" "$BUNDLE" 2>/dev/null || true

echo "==> Web (demo fleet, dev server)"
( cd "$WEB_REPO" && npx vite --port "$WEB_PORT" --strictPort >"$WORK/vite.log" 2>&1 ) &
VITE=$!
trap 'kill $VITE 2>/dev/null || true' EXIT
for _ in $(seq 30); do curl -s -o /dev/null "http://localhost:$WEB_PORT/" && break; sleep 1; done

web() {
  local name="$1" path="$2"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --virtual-time-budget=6000 --window-size=1280,800 \
    --screenshot="$WORK/raw/$name.png" "http://localhost:$WEB_PORT$path" 2>/dev/null
  echo "  $name"
}
web web-dashboard "/?demo=1"
# Demo ids share one counter with entries, so look the car up by name. Not
# "The wagon" (car-0): it carries a deliberate odometer typo, and its page
# opens with that warning.
CAR=$("$CHROME" --headless=new --disable-gpu --virtual-time-budget=6000 \
  --dump-dom "http://localhost:$WEB_PORT/garage?demo=1" 2>/dev/null | python3 -c "
import re, sys
for chunk in sys.stdin.read().split('href=\"/garage/')[1:]:
    if 'Tacoma' in re.sub('<[^>]+>', ' ', chunk.split('</a>')[0]):
        print(chunk.split('\"')[0]); break")
[ -n "$CAR" ] || { echo "demo Tacoma not found on /garage"; exit 1; }
web web-car       "/garage/$CAR?demo=1"

echo "==> Converting to WebP in $OUT"
for f in "$WORK"/raw/*.png; do
  name=$(basename "${f%.png}")
  width=$WIDTH
  case "$name" in web-*) width=$WEB_WIDTH ;; esac
  cwebp -quiet -q 82 -resize "$width" 0 "$f" -o "$OUT/$name.webp"
done
ls -l "$OUT"
echo "==> Done. Look at every image before committing."
