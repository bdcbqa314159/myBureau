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

  # RENAMING A REPOSITORY DOES NOT CHANGE THE LOCAL REMOTE. GitHub keeps
  # serving the old address by redirect, so pushing carries on working
  # and nothing announces that the name has moved — which would make
  # this check confidently compare against a name that no longer exists.
  # So ask GitHub what the repository is called now, when we can.
  truth=""
  if command -v gh >/dev/null 2>&1; then
    truth=$(gh api "repos/$slug" --jq .full_name 2>/dev/null || true)
  fi
  if [ -n "$truth" ] && [ "$truth" != "$slug" ]; then
    printf '  note  this repository has been renamed since it was cloned\n'
    printf '          the remote still says  %s\n' "$slug"
    printf '          GitHub now calls it    %s\n' "$truth"
    printf '          harmless — pushing still works — but tidy it with:\n'
    printf '          git remote set-url origin git@github.com:%s.git\n\n' "$truth"
    slug="$truth"
  fi

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

  # If Pages is already switched on, its own URL beats anything derived
  # from the name — it accounts for a custom domain already attached and
  # for anything about Pages we have guessed wrong.
  if command -v gh >/dev/null 2>&1; then
    live_url=$(gh api "repos/$slug/pages" --jq .html_url 2>/dev/null || true)
    if [ -n "$live_url" ]; then
      expected="${live_url%/}"
      kind="GitHub Pages says so"
    fi
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

# ---- 6. is about me.txt actually about her? --------------------------
# Both halves are silent when missing: the window opens, looks right, and
# says nothing. Nobody notices until a visitor does.
if ls content/about.* >/dev/null 2>&1; then
  good "about me.txt has her portrait"
else
  need "no portrait in about me.txt"
  note "fix: drop content/about.jpg — or the home desk in the panel"
fi
if grep -q 'à venir' content/_index.md; then
  need "the about text is still the placeholder one"
  note "fix: the words under the +++ in content/_index.md, and _index.en.md"
else
  good "the about text has been written"
fi

# ---- 7. and the things that are already checked elsewhere ------------
printf '\n'
python3 tools/look.py | sed 's/^/  /'

printf '  %d ready, %d to do\n\n' "$ok" "$todo"
[ "$todo" -eq 0 ] || printf '  Not a problem — this is the handover list, in order.\n  The last one to change is live = true.\n\n'
exit 0
