#!/usr/bin/env bash
# See your site, on this machine, before anyone else does.
#
#   ./preview.sh          — or double-click preview.command in Finder
#
# Leave it running while you work. Add a folder, drop in photos, save a
# text file: the page in your browser reloads by itself. Press Ctrl-C in
# this window to stop.
#
# This needs ONE thing installed, and it offers to install it for you.
# Nothing else — macOS already ships the rest.
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\n  %s\n' "$*"; }
step() { printf '  %s\n' "$*"; }
die()  { printf '\n  %s\n\n' "$*" >&2; exit 1; }

say "myBureau — starting a preview of your site"

# ---- the one thing this needs -----------------------------------------
# Zola builds the site. The compiled JavaScript is in the repository
# already, so there is no Node, no npm and no build step here — see
# "Why the compiled JS is in the repo" in README.
if ! command -v zola >/dev/null 2>&1; then
  step "Zola is not installed yet — it is the program that builds the site."
  if command -v brew >/dev/null 2>&1; then
    step "Installing it now. This happens once and takes about a minute."
    brew install zola
  else
    printf '\n  Homebrew is missing, and it is how Zola gets installed.\n'
    printf '  Copy this line, paste it into Terminal, press Return, and\n'
    printf '  follow what it asks. Then run this again.\n\n'
    printf '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n\n'
    exit 1
  fi
fi

if ! command -v python3 >/dev/null 2>&1; then
  die "python3 is missing, which is unusual on macOS. Tell Bernardo."
fi

# ---- a quick look at what is in the site ------------------------------
bureaus=$(find content -name '_index.md' | wc -l | tr -d ' ')
pages=$(find content -name 'index.md' | wc -l | tr -d ' ')
photos=$(find content -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) ! -iname 'icon.*' | wc -l | tr -d ' ')
say "Found $bureaus bureaus, $pages projects, $photos images."

# Languages. Untranslated is not an error — this says what is left, and
# the command that fills it in, rather than a sentence about it.
langs=$(grep -cE '^\[languages\.[A-Za-z0-9_-]+\]' config.toml || true)
if [ "$langs" -gt 0 ]; then
  if ! python3 tools/i18n.py >/tmp/mybureau-i18n.txt 2>&1; then
    cat /tmp/mybureau-i18n.txt
    die "A word is asked for that nobody wrote. Add it to [translations] in config.toml."
  fi
  gaps=$(grep -c 'absent from\|still in\|MISSING\|no longer in' /tmp/mybureau-i18n.txt || true)
  if [ "$gaps" -gt 0 ]; then
    step "$gaps thing(s) not translated yet. To see them:   python3 tools/i18n.py"
    step "To create the missing files:                      python3 tools/i18n.py --sync"
  fi
fi

# ---- things that build fine and then quietly do nothing ---------------
python3 tools/look.py

# ---- build once, so a mistake is reported here and not in silence -----
if ! zola build >/tmp/mybureau-build.txt 2>&1; then
  printf '\n  The site did not build. Zola says:\n\n'
  sed 's/^/    /' /tmp/mybureau-build.txt
  printf '\n  Nothing is broken on the published site — this is only your copy.\n'
  printf '  Undo the last thing you changed, or send these lines to Bernardo.\n\n'
  exit 1
fi

PORT=1111
while lsof -i :"$PORT" >/dev/null 2>&1; do PORT=$((PORT + 1)); done

say "Opening http://127.0.0.1:$PORT"
step "The page reloads by itself when you change anything."
step "Press Ctrl-C here to stop."
printf '\n'

( sleep 2; command -v open >/dev/null 2>&1 && open "http://127.0.0.1:$PORT" ) &
exec zola serve --interface 127.0.0.1 --port "$PORT"
