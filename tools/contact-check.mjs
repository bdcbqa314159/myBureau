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

console.log(
  failed === 0
    ? `\n  all ${cases.length + 1} checks passed\n`
    : `\n  ${failed} FAILED\n`,
);
process.exit(failed === 0 ? 0 : 1);
