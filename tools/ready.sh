#!/usr/bin/env bash
# Is this copy of the site ready to be somebody's real website?
#
#     ./tools/ready.sh
#
# Run it in whichever repository is about to go live. It compares what
# config.toml claims against what this repository actually is, and says
# what is left.
#
# The one it exists for is base_url. If base_url still names someone
# else's repository, nothing errors and nothing looks wrong — every link
# and every image on the published site just quietly points at the other
# person's GitHub Pages. That is the single most expensive silent
# failure available at handover, and it is one line to fix.
set -uo pipefail
cd "$(dirname "$0")/.."

ok=0; todo=0
good() { printf '  ok    %s\n' "$*"; ok=$((ok + 1)); }
need() { printf '  TODO  %s\n' "$*"; todo=$((todo + 1)); }
note() { printf '          %s\n' "$*"; }

cfg() { grep -m1 "^$1" config.toml | cut -d'"' -f2; }

BASE=$(cfg 'base_url')
LIVE=$(grep -m1 '^live = ' config.toml | awk '{print $3}')
printf '\n  base_url  %s\n  live      %s\n\n' "$BASE" "$LIVE"

# ---- 1. does base_url match the repository it is actually in? --------
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE" ]; then
  need "no git remote — cannot tell whether base_url is right"
else
  # git@github.com:owner/repo.git  or  https://github.com/owner/repo.git
  slug=$(printf '%s' "$REMOTE" | sed -E 's#^.*github\.com[:/]##; s#\.git$##')
  owner=${slug%%/*}
  repo=${slug##*/}

  if [ -f static/CNAME ]; then
    expected="https://$(tr -d ' \t\r\n' < static/CNAME)"
    kind="custom domain (static/CNAME)"
  elif [ "$(printf '%s' "$repo" | tr '[:upper:]' '[:lower:]')" = "$(printf '%s' "$owner" | tr '[:upper:]' '[:lower:]').github.io" ]; then
    expected="https://$(printf '%s' "$owner" | tr '[:upper:]' '[:lower:]').github.io"
    kind="user site — serves at the root"
  else
    expected="https://$(printf '%s' "$owner" | tr '[:upper:]' '[:lower:]').github.io/$repo"
    kind="project site — serves under /$repo"
  fi

  if [ "${BASE%/}" = "${expected%/}" ]; then
    good "base_url matches this repository  ($kind)"
  else
    need "base_url does not match this repository  ($kind)"
    note "config.toml says  $BASE"
    note "this repo serves  $expected"
    note "fix: set base_url in config.toml to the second one"
  fi
fi

# ---- 2. whose site does it say it is? --------------------------------
if [ "$LIVE" = "true" ]; then
  good "live = true — the site carries the real name"
else
  need "live = false — the site still calls itself a demo, and carries noindex"
  note "fix: live = true in config.toml, but ONLY after the placeholders are gone"
fi

# ---- 3. where does the contact form go? ------------------------------
KEY=$(awk '/^\[extra.contact.real\]/{f=1} f&&/^access_key/{print; exit}' config.toml | cut -d'"' -f2)
if [ -n "$KEY" ]; then
  good "the real contact key is set"
else
  need "no access_key under [extra.contact.real] — the form has nowhere to go"
  note "fix: her own Web3Forms key, registered to her address"
fi

# ---- 4. is any of the content still ours? ----------------------------
left=$(python3 tools/placeholders.py --check 2>/dev/null | head -1 | awk '{print $1}')
if [ "${left%%/*}" = "0" ] || [ -z "$left" ]; then
  good "no placeholder photographs left"
else
  need "$left placeholder photographs still present"
  note "fix: python3 tools/placeholders.py --purge, then add the real work"
fi

# ---- 5. the credit the licence asks for ------------------------------
if grep -q 'credit-studio\|site by' templates/base.html; then
  good "the 'site by' credit is still in the template (LICENSE §4)"
else
  need "the 'site by' credit is gone from templates/base.html — LICENSE §4 requires it"
fi

# ---- 6. and the things that are already checked elsewhere ------------
printf '\n'
python3 tools/look.py | sed 's/^/  /'

printf '  %d ready, %d to do\n\n' "$ok" "$todo"
[ "$todo" -eq 0 ] || printf '  Not a problem — this is the handover list, in order.\n  The last one to change is live = true.\n\n'
exit 0
