#!/usr/bin/env bash
# Build the site and open it in your browser.
#
#   ./preview.sh
#
# Leave it running while you work. Add a folder, drop in photos, save a
# text file — the page reloads by itself. Press Ctrl-C to stop.
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\n  %s\n' "$*"; }
step() { printf '  %s\n' "$*"; }
die()  { printf '\n  %s\n\n' "$*" >&2; exit 1; }

say "myBureau — starting a preview of your site"

# ---- the two things this needs ----------------------------------------
if ! command -v zola >/dev/null 2>&1; then
  step "Zola is not installed — it is what builds the site."
  if command -v brew >/dev/null 2>&1; then
    step "Installing it now (this happens once, and takes a minute)…"
    brew install zola
  else
    die "Please install Homebrew first — https://brew.sh — then run this again."
  fi
fi

if ! command -v npm >/dev/null 2>&1; then
  die "Node is not installed. Get it from https://nodejs.org (the LTS button), then run this again."
fi

# ---- prepare ----------------------------------------------------------
if [ ! -d node_modules ]; then
  step "Setting things up (this happens once)…"
  npm install --silent
fi

step "Preparing the page behaviour…"
npx tsc

# ---- a quick sanity read of the content -------------------------------
bureaus=$(find content -name '_index.md' | wc -l | tr -d ' ')
pages=$(find content -name 'index.md' | wc -l | tr -d ' ')
photos=$(find content -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) ! -iname 'icon.*' | wc -l | tr -d ' ')
say "Found $bureaus bureaus, $pages projects, $photos images."

# Languages. Untranslated is fine — this says what is left, and the
# command that fills it in, rather than a sentence about it.
langs=$(grep -cE '^\[languages\.[A-Za-z0-9_-]+\]' config.toml || true)
if [ "$langs" -gt 0 ]; then
  if ! python3 tools/i18n.py >/tmp/mybureau-i18n.txt 2>&1; then
    cat /tmp/mybureau-i18n.txt
    die "A string is asked for that nobody wrote. Add it to [translations] in config.toml."
  fi
  gaps=$(grep -c 'absent from\|still in\|MISSING\|no longer in' /tmp/mybureau-i18n.txt || true)
  if [ "$gaps" -gt 0 ]; then
    step "$gaps thing(s) not translated yet. To see them:   python3 tools/i18n.py"
    step "To create the missing files:                      python3 tools/i18n.py --sync"
  fi
fi

PORT=1111
while lsof -i :"$PORT" >/dev/null 2>&1; do PORT=$((PORT + 1)); done

say "Opening http://127.0.0.1:$PORT"
step "The page reloads by itself when you change anything."
step "Press Ctrl-C here to stop."
printf '\n'

( sleep 2; command -v open >/dev/null 2>&1 && open "http://127.0.0.1:$PORT" ) &
exec zola serve --interface 127.0.0.1 --port "$PORT"
