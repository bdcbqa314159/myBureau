#!/usr/bin/env bash
# Does the contact backend strip injected mail headers?
#
#     ./tools/injection-probe.sh
#
# This is the acceptance test for choosing a backend. It bypasses the page
# entirely and POSTs straight at the endpoint with curl — exactly as an
# attacker would — then you read the raw source of what arrives.
#
# WEB3FORMS REFUSES THIS. Every request from curl comes back 403:
#
#   "This method is not allowed. Use our API in client side or contact
#    support with server IP address (Pro plan is required)"
#
# Tested with a browser User-Agent, with a matching Origin, with a Referer,
# and with all three. All 403. That is a real defence against the cheap
# attack — and it also means THIS SCRIPT CANNOT TEST THEM. Only a browser
# can reach them, so see "Testing a browser-only backend" in the README.
#
# The script stays because it is the right test for a backend that does
# accept server-side POSTs — a Cloudflare Worker, for instance.
#
# It sends REAL submissions to whatever address the access key points at.
# Run it against your own address, never a client's.
#
# Every address in the payloads is under example.com / example.net, which
# RFC 2606 reserves for documentation. Nothing can be delivered to them.
set -euo pipefail
cd "$(dirname "$0")/.."

ENDPOINT=$(grep -A2 '^\[extra.contact\]' config.toml | grep '^endpoint' | cut -d'"' -f2)

# Probe whichever key is actually live, so this tests what visitors hit.
LIVE=$(grep '^live = ' config.toml | awk '{print $3}')
if [ "$LIVE" = "true" ]; then
  WHICH="real"
  printf '\n  live = true — this probes the CLIENT inbox. Are you sure?\n' >&2
  printf '  Ctrl-C now, or wait 5 seconds.\n\n' >&2
  sleep 5
else
  WHICH="demo"
fi
KEY=$(awk "/^\\[extra.contact.$WHICH\\]/{f=1} f&&/^access_key/{print; exit}" config.toml | cut -d'"' -f2)

if [ -z "$ENDPOINT" ] || [ -z "$KEY" ]; then
  printf '\n  No endpoint or no %s access_key in config.toml — nothing to probe.\n\n' "$WHICH" >&2
  exit 1
fi

printf '\n  Using the %s key.\n' "$WHICH"

printf '\n  Probing %s\n' "$ENDPOINT"
printf '  Three submissions will be sent. Read the raw source of each.\n\n'

send() {
  local label="$1" email="$2" subject="$3" message="$4"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$ENDPOINT" \
    --data-urlencode "access_key=$KEY" \
    --data-urlencode "email=$email" \
    --data-urlencode "subject=$subject" \
    --data-urlencode "message=$message")
  printf '  [%s]  %s\n' "$code" "$label"
}

# 1. the control: an ordinary submission, so you know delivery works at all
send "control — should arrive normally" \
     "probe@example.com" \
     "PROBE 1 control" \
     "Ordinary message. If this does not arrive, nothing below means anything."

# 2. newline in the address: the classic header injection
send "injection via mail field" \
     $'probe@example.com\nBcc: should-not-exist@example.net' \
     "PROBE 2 bcc via email field" \
     "If the received headers contain a Bcc, this backend is unsafe."

# 3. newline in the subject: the subject IS a header
send "injection via subject field" \
     "probe@example.com" \
     $'PROBE 3 bcc via subject\nBcc: should-not-exist@example.net' \
     "If the received headers contain a Bcc, this backend is unsafe."

cat <<'EOF'

  Now open each message and view its RAW SOURCE:
    Gmail      ... > Show original
    Apple Mail  View > Message > Raw Source

  PASS  only PROBE 1 arrives normally, and probes 2 and 3 either never
        arrive, arrive with the newline stripped or escaped, or are
        rejected outright. No Bcc header you did not write.

  FAIL  any received message carries a Bcc: or Content-Type: header that
        was not ours. Do not use this backend.

  Either way, delete the probe submissions afterwards.

EOF
