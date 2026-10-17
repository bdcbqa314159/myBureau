// Contact form: validation and bot defences.
//
// READ THIS BEFORE TRUSTING ANY OF IT.
//
// Every check here runs in the visitor's browser. An attacker does not use
// the form — they POST straight at the endpoint with curl, and none of
// this executes. This is the sign on the door. The lock is whatever
// validates on the receiving side.
//
// What it is genuinely for: catching honest mistakes, telling the sender
// why instead of failing silently, and costing a lazy bot more than it
// wants to spend. Worth having. Not a defence.

export type Check = { ok: true } | { ok: false; reason: string };

const OK: Check = { ok: true };
const no = (reason: string): Check => ({ ok: false, reason });

/** Control characters, except tab and newline which are legal in a body. */
const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/;
const NEWLINE = /[\r\n]/;

/** The shape that turns a contact form into a spam relay: a newline in a
 *  field that lands in a mail header lets an attacker append their own —
 *  "Bcc: <five thousand addresses>" — and the mail goes out in her name. */
const HEADERISH =
  /(^|[\r\n])\s*(bcc|cc|to|from|reply-to|content-type|content-transfer-encoding|mime-version|x-mailer)\s*:/i;

export const LIMITS = { email: 254, subject: 150, message: 4000 } as const;

/** Strip control characters. Never a substitute for rejecting — only to
 *  tidy what has already passed. */
export const clean = (s: string): string =>
  s.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");

/** Exactly one address, and nothing that could become a header. */
export function checkEmail(raw: string): Check {
  const v = raw.trim();
  if (v === "") return no("Il manque ton adresse mail.");
  if (v.length > LIMITS.email) return no("Cette adresse est trop longue.");
  if (NEWLINE.test(v)) return no("Cette adresse n'est pas valide.");
  if (CONTROL.test(v)) return no("Cette adresse n'est pas valide.");
  if (/[,;]/.test(v)) return no("Une seule adresse, merci.");
  if (HEADERISH.test(v)) return no("Cette adresse n'est pas valide.");
  // Shape, deliberately not RFC 5322. A perfect address regex is a famous
  // trap; one @, something either side, a dot in the domain is enough. The
  // control-character ban above is the part that actually matters.
  if (!/^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/.test(v)) {
    return no("Cette adresse n'a pas l'air valide.");
  }
  return OK;
}

/** The subject becomes a mail header, so it gets the same newline ban. */
export function checkSubject(raw: string): Check {
  const v = raw.trim();
  if (v.length > LIMITS.subject) return no("L'objet est trop long.");
  if (NEWLINE.test(v) || CONTROL.test(v)) {
    return no("L'objet contient des caracteres interdits.");
  }
  if (HEADERISH.test(v)) return no("L'objet n'est pas valide.");
  return OK;
}

/** The body is not a header, so injection matters less and volume more. */
export function checkMessage(raw: string): Check {
  const v = raw.trim();
  if (v === "") return no("Il manque ton message.");
  if (v.length > LIMITS.message) return no("Ce message est trop long.");
  if (CONTROL.test(v)) return no("Ce message contient des caracteres interdits.");
  if (HEADERISH.test(v)) return no("Ce message n'est pas valide.");
  const links = v.match(/https?:\/\//gi);
  if (links !== null && links.length > 6) return no("Trop de liens.");
  return OK;
}

export interface Submission {
  email: string;
  subject: string;
  message: string;
}

export function checkAll(s: Submission): Check {
  const email = checkEmail(s.email);
  if (!email.ok) return email;
  const subject = checkSubject(s.subject);
  if (!subject.ok) return subject;
  return checkMessage(s.message);
}

/** Nobody writes an email in under two and a half seconds. Plenty of bots do. */
export const TOO_FAST_MS = 2500;

// ---------------------------------------------------------------------
// Wiring. Guarded so the checks above can be imported and tested in Node,
// where there is no document.
// ---------------------------------------------------------------------

function wire(form: HTMLFormElement): void {
  const opened = Date.now();
  const say = form.querySelector<HTMLElement>("[data-says]");
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]');
  const endpoint = form.getAttribute("action") ?? "";
  const key = form.querySelector<HTMLInputElement>('input[name="access_key"]')?.value ?? "";

  const tell = (msg: string): void => {
    if (say !== null) say.textContent = msg;
  };

  form.addEventListener("submit", (e: Event): void => {
    e.preventDefault();

    // A field no human can see and no screen reader reaches. Filled in
    // means a bot. Say nothing — an error teaches it what tripped it.
    const trap = form.querySelector<HTMLInputElement>('input[name="_trap"]');
    if (trap !== null && trap.value !== "") return;

    if (Date.now() - opened < TOO_FAST_MS) return;

    const data = new FormData(form);
    const submission: Submission = {
      email: String(data.get("email") ?? ""),
      subject: String(data.get("subject") ?? ""),
      message: String(data.get("message") ?? ""),
    };

    const verdict = checkAll(submission);
    if (!verdict.ok) {
      tell(verdict.reason);
      return;
    }

    // No key means no destination. Say so rather than posting into a void.
    if (endpoint === "" || key === "") {
      tell("Le formulaire n'est pas encore relie.");
      return;
    }

    if (button !== null) button.disabled = true;   // one click, one mail
    tell("Envoi...");

    void fetch(endpoint, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: new URLSearchParams({
        access_key: key,
        email: clean(submission.email.trim()),
        subject: clean(submission.subject.trim()),
        message: clean(submission.message.trim()),
      }),
    })
      .then((r) => {
        // Never echo anything the visitor typed back into the page. A
        // "thanks, you said X" confirmation is a stored-XSS vector for free.
        tell(r.ok ? "Message envoye. Merci." : "L'envoi a echoue. Reessaie plus tard.");
        if (!r.ok && button !== null) button.disabled = false;
      })
      .catch(() => {
        tell("L'envoi a echoue. Reessaie plus tard.");
        if (button !== null) button.disabled = false;
      });
  });
}

if (typeof document !== "undefined") {
  document.querySelectorAll<HTMLFormElement>(".contact-form").forEach(wire);
}
