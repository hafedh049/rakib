# Product

## Register

product

## Users

Three populations, on opposite sides of the same complaint, in very different conditions.

**Claimants** — Tunisian telecom customers, on a phone, usually annoyed and often mid-problem
(no network, a bill they think is wrong, a recharge that vanished). They write in French, in
Arabic, or in Latin-script derja, frequently in one sentence and rarely with a reference number
to hand. Many have no email address; a phone number is their identity. Their job: report the
problem, get proof it was received, and be able to check on it later without creating an
account. They visit two or three times and leave.

**Agents** — Operator staff in a queue-driven job, working the same console for eight hours,
in French, on a desktop, with a target on their handling time. Their job: understand a
complaint in seconds, know why it landed on their desk, answer, and move on. Density is a
feature. Every extra click is paid a hundred times a day.

**Supervisors and admins** — Watching SLA breaches, triage quality and the model itself. Their
job: see what is about to breach, correct what the engine got wrong, and tune the rules that
decide priority. They need to argue with the system, which means the system must show its work.

## Product Purpose

Rakib (رقيب) receives complaints, classifies and prioritises them, routes them to the right
team, flags duplicates, and drafts replies — entirely on local hardware, with no external
inference service.

Success is measured three ways: a complaint is triaged, routed and visible in an agent's queue
in under a second; an agent can see *why* it was prioritised, in tokens they can read; and a
supervisor who disagrees can correct it in one click, with that correction becoming training
data. The system is not trying to be right unsupervised — it is trying to be fast, legible,
and correctable.

## Brand Personality

**Composed, accountable, unshowy.**

Rakib means "monitor" or "watchman". The interface should feel like a competent duty officer:
it tells you what it saw, what it decided, and how sure it was — then gets out of the way. It
never performs confidence it does not have. When it is unsure it says so plainly and asks a
human, and that admission is designed as a first-class state rather than an error.

Voice: plain administrative French, the register of a well-run public service. No exclamation
marks, no "Oops!", no apologising for the customer's problem in the UI chrome.

## Anti-references

- **The three Tunisian operators' identities.** Not Ooredoo red, not Orange orange, not
  Tunisie Telecom blue. This is not their product and must not borrow their equity.
- **shadcn/ui straight out of the box.** Slate-and-blue defaults, uniform card grids, the same
  rounded rectangle for everything. Competent and completely forgettable.
- **The dashboard-hero template.** Four big gradient stat tiles above the fold with no
  supporting context. If a number is on screen it must be actionable.
- **Government-portal brutalism.** Tunisian public-sector web has a real aesthetic — dense
  tables, tiny type, no states. Familiar is not an excuse for illegible.
- **AI mysticism.** No sparkle icons, no "AI-powered" badges, no glow. The intelligence here is
  TF-IDF and weighted rules; the UI should describe it as plainly as that.

## Design Principles

1. **Show the work.** Every automated decision carries its evidence: which rules fired, on
   which tokens, with what weight, from which model version. An unexplained priority badge is
   a bug.
2. **Two registers, one system.** The public portal is calm and generous because the person
   using it is stressed and infrequent. The console is dense and keyboard-first because the
   person using it lives there. Same tokens, deliberately different feel.
3. **Uncertainty is a designed state, not an error.** `needs_human_triage` gets a real
   treatment — amber, named reason, one-click correction — because it is the system working
   correctly, not failing.
4. **Arabic is not an afterthought.** RTL, Arabic typography and Arabic drafts are built from
   the first component, not retrofitted. A platform for Tunisia that renders Arabic badly has
   failed at its stated purpose.
5. **Density where it is earned.** The console shows a lot at once because agents need it. The
   portal shows one thing at a time because claimants do not.

## Accessibility & Inclusion

- **WCAG 2.1 AA.** Body text ≥ 4.5:1, large text and UI boundaries ≥ 3:1, including in dark
  mode and including placeholders.
- **Full RTL** on the claimant portal: logical properties throughout, `dir` on the document,
  mirrored chevrons, Arabic face bundled and self-hosted (no CDN — the system must run with no
  internet).
- **Never colour alone.** Priority, SLA state and triage state each carry a shape, a label or
  an icon in addition to hue. Amber SLA warnings must be distinguishable without colour vision.
- **Keyboard-complete console.** Every agent action reachable without a mouse; visible focus
  rings that survive both themes.
- **`prefers-reduced-motion`** honoured on every transition, with a crossfade or instant
  fallback.
- **Low-bandwidth reality.** The portal must be usable on a poor mobile connection: no
  blocking fonts, no large payloads on the submission path.
