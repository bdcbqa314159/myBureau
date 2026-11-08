#!/usr/bin/env node
// Does the contact form reject what it must?
//
//     npx tsc && node tools/contact-check.mjs
//
// Runs the real validators against a table of hostile inputs. The ones
// that matter are the header-injection cases: a newline in a field that
// lands in a mail header is what turns a contact form into a spam relay.

import { checkEmail, checkSubject, checkMessage, LIMITS, clean }
  from "../static/js/contact.js";

const CTRL = String.fromCharCode(7);

const cases = [
  // [ what, which check, input, must be rejected? ]
  ["plain address",            checkEmail,   "valentina@studio-s.fr",            false],
  ["address with a plus",      checkEmail,   "val+site@studio-s.fr",             false],
  ["subdomain",                checkEmail,   "val@mail.studio-s.fr",             false],

  ["NEWLINE injection",        checkEmail,   "a@b.fr\nBcc: victim@x.com",        true],
  ["CARRIAGE RETURN",          checkEmail,   "a@b.fr\r\nBcc: victim@x.com",      true],
  ["bare Bcc header",          checkEmail,   "a@b.fr\nBcc: x@y.z",               true],
  ["Content-Type injection",   checkEmail,   "a@b.fr\nContent-Type: text/html",  true],
  ["comma list",               checkEmail,   "a@b.fr,c@d.fr",                    true],
  ["semicolon list",           checkEmail,   "a@b.fr;c@d.fr",                    true],
  ["control character",        checkEmail,   "a" + CTRL + "@b.fr",               true],
  ["no @",                     checkEmail,   "not-an-address",                   true],
  ["two @",                    checkEmail,   "a@b@c.fr",                         true],
  ["no dot in domain",         checkEmail,   "a@localhost",                      true],
  ["empty",                    checkEmail,   "",                                 true],
  ["over 254 chars",           checkEmail,   "a".repeat(250) + "@b.fr",          true],

  ["ordinary subject",         checkSubject, "Projet pour janvier",              false],
  ["empty subject is allowed", checkSubject, "",                                 false],
  ["newline in subject",       checkSubject, "Hello\nBcc: x@y.z",                true],
  ["header in subject",        checkSubject, "\nContent-Type: text/html",        true],
  ["subject too long",         checkSubject, "x".repeat(LIMITS.subject + 1),     true],

  ["ordinary message",         checkMessage, "Bonjour, j'aimerais te parler.",   false],
  ["message with newlines",    checkMessage, "Bonjour,\n\nVoici mon projet.",    false],
  ["message with a tab",       checkMessage, "Bonjour,\tvoici.",                 false],
  ["one link is fine",         checkMessage, "vois https://studio-s.fr",         false],
  ["empty message",            checkMessage, "   ",                              true],
  ["message too long",         checkMessage, "x".repeat(LIMITS.message + 1),     true],
  ["control char in message",  checkMessage, "hello" + CTRL + "world",           true],
  ["headers in message",       checkMessage, "hi\nBcc: a@b.c\nhello",            true],
  ["link spam",                checkMessage, Array(8).fill("https://x.cc").join(" "), true],
];

let failed = 0;
for (const [name, check, input, mustReject] of cases) {
  const verdict = check(input);
  const rejected = !verdict.ok;
  const pass = rejected === mustReject;
  if (!pass) failed += 1;
  const want = mustReject ? "reject" : "accept";
  const got = rejected ? "rejected" : "accepted";
  console.log(
    `  ${pass ? "ok  " : "FAIL"}  ${name.padEnd(26)} want ${want}, ${got}` +
    (rejected && pass && mustReject ? `  (${verdict.reason})` : ""),
  );
}

// clean() must remove control characters but keep newline and tab
const dirty = "a" + CTRL + "b\nc\td";
if (clean(dirty) !== "ab\nc\td") {
  failed += 1;
  console.log("  FAIL  clean() must strip control chars but keep \\n and \\t");
} else {
  console.log("  ok    clean() strips control chars, keeps newline and tab");
}

// --- a translation blob that does not parse --------------------------
// contact.ts reads its strings at MODULE SCOPE, so a blob that throws
// takes the validators with it: the form would stop refusing anything
// because nothing got wired, which is worse than a dead button.
//
// The static import at the top of this file runs with no `document` at
// all, so it takes the early return and NEVER REACHES the parse. That
// is why the guard needs exercising here, with a document given to it
// and the module imported again — otherwise this file would report a
// parse it has never once run.
let extra = 0;
for (const [what, bad] of [
  ["torn off halfway", '{"form_sent":"Env'],
  ["not json at all", "<!doctype html>"],
  ["empty", ""],
]) {
  // The module wires every .contact-form at load, so the stub needs
  // that too — a stub thinner than the code it loads reports a failure
  // that belongs to the stub.
  globalThis.document = {
    body: { dataset: { i18n: bad } },
    querySelectorAll: () => [],
  };
  let held = true;
  try {
    const again = await import(`../static/js/contact.js?blob=${encodeURIComponent(what)}`);
    // say() falling back to the key is what makes an empty table
    // survivable, so that is the thing asserted — not merely that the
    // import resolved.
    held = typeof again.say === "function" && again.say("form_sent") === "form_sent";
  } catch {
    held = false;
  }
  extra += 1;
  if (!held) failed += 1;
  console.log(`  ${held ? "ok  " : "FAIL"}  the form still loads when the blob is ${what}`);
}
delete globalThis.document;

console.log(
  failed === 0
    ? `\n  all ${cases.length + 1 + extra} checks passed\n`
    : `\n  ${failed} FAILED\n`,
);
process.exit(failed === 0 ? 0 : 1);
