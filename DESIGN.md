# Design

## Theme

**Scene, portal:** a woman standing outside an agency in Sfax at 11am, phone in one hand,
bright sun, no network, mildly furious, wanting to be done in ninety seconds. Bright ambient
light, small screen, one thing at a time. → **Light.**

**Scene, console:** an agent in an operator back-office, eight hours in the same window,
forty complaints in the queue, screen brightness turned down by 3pm. → **Dark by default**,
with a light theme shipped and `prefers-color-scheme` respected.

Both registers share one token set. The portal spends the space; the console spends the
density.

## Color

Strategy: **Restrained.** Tinted neutrals plus one accent, with a strictly rationed semantic
vocabulary.

The bank's identity is black and red, which creates the one conflict this product cannot
afford: red already means *danger*. The resolution separates them by **role and placement**,
not only by hue.

- **Interactive is graphite**, never red. Buttons, focus rings and active states run on
  near-black. That is the *noir*, and it reads institutional rather than alarming.
- **Brand red is chrome only** — the mark, the masthead rule, the active nav indicator. It
  never lands on a datum or a state.
- **Danger is oxblood**, darker and less saturated than the brand red, so the two are
  distinguishable even side by side.

Because brand red never appears on a state and danger never appears on chrome, position alone
disambiguates them before colour is even considered. On dark, `--primary` inverts to near-white:
a red button would fight the breach badges sitting beside it in the queue.

Neutrals carry a 0.004–0.008 chroma bias toward the brand's own red so they read as chosen.
They are **not** warmed by default — the bias points at the identity, nothing else.

All values OKLCH.

### Core

| Role | Light | Dark |
|---|---|---|
| Role | Light | Dark |
|---|---|---|
| `--bg` | `oklch(1 0 0)` — literal white | `oklch(0.165 0.006 25)` |
| `--surface` | `oklch(0.985 0.003 25)` | `oklch(0.208 0.008 25)` |
| `--surface-2` | `oklch(0.962 0.005 25)` | `oklch(0.252 0.010 25)` |
| `--ink` | `oklch(0.19 0.008 25)` | `oklch(0.96 0.003 25)` |
| `--ink-muted` | `oklch(0.45 0.010 25)` | `oklch(0.72 0.008 25)` |
| `--line` | `oklch(0.89 0.005 25)` | `oklch(0.31 0.010 25)` |
| `--primary` (graphite) | `oklch(0.22 0.010 25)` | `oklch(0.95 0.004 25)` |
| `--primary-ink` | `oklch(0.99 0 0)` | `oklch(0.17 0.008 25)` |
| `--brand` (chrome only) | `oklch(0.55 0.215 27)` | `oklch(0.63 0.21 27)` |

`--ink-muted` is deliberately darker than the usual "elegant grey": 4.6:1 on `--surface` in
light, 4.8:1 in dark. Placeholders use `--ink-muted`, not a lighter step.

### Semantic — rationed on purpose

- `--amber` `oklch(0.76 0.14 75)` — **reserved** for `needs_human_triage`. It appears nowhere
  else, so an amber pixel always means "a human needs to look at this".
- `--danger` `oklch(0.44 0.16 25)` light / `oklch(0.66 0.17 25)` dark — rejection and
  destructive actions. Oxblood, deliberately not the brand red.
- `--success` `oklch(0.50 0.12 155)` — resolved and closed.
- `--info` = `--primary`.

### Arabic type

No webfont is bundled. The system is required to run fully offline, which rules
out a CDN-hosted face; and a self-hosted woff2 would add weight to a portal whose
users are often on a phone and a poor connection, in order to replace faces that
already render Arabic correctly on every platform we target. `--font-arabic`
therefore names the good local faces in preference order and falls through to the
platform default — Segoe UI on Windows, Geeza Pro on Apple, Noto Naskh on
Android.

If the bank later supplies a licensed face, self-host it and prepend it to that
one token; nothing else changes.

### The mark

The official artwork is a registered trademark and is **not** committed. `Brandmark`
loads `public/brand/uib.svg` and falls back to a typographic composition when it is
absent, so the repository can be shared and archived without redistributing it.

A permanent, non-dismissible notice sits above the masthead on the portal. The site
wears a real institution's identity and collects contact details from the public;
without that line a visitor arriving from a search engine cannot tell it from the
official form. It is not dismissible on purpose — a notice you can close is a notice
nobody reads.

## Typography

**One family per script.** No display/body pairing — this is product UI.

- **Latin:** `system-ui` stack. Zero bytes, zero network requests, familiar at every size.
  The offline constraint is real and a webfont on the submission path is a cost with no
  matching benefit.
- **Arabic:** **IBM Plex Sans Arabic**, self-hosted woff2, subset. System Arabic fallbacks are
  genuinely poor at UI sizes, and PRODUCT.md commits to Arabic not being an afterthought. Applied
  via `:lang(ar)` and `[dir="rtl"]`.

Fixed rem scale, ratio ~1.2 — not fluid. A clamp-sized heading that shrinks inside a console
panel looks worse, not better.

`12 · 13 · 14 · 16 · 18 · 21 · 26 · 32 px` → `0.75 · 0.8125 · 0.875 · 1 · 1.125 · 1.3125 · 1.625 · 2 rem`

Console body sits at 14px, portal body at 16px. Tabular figures (`font-variant-numeric:
tabular-nums`) on every number that appears in a column: refs, amounts, counts, countdowns.

## Layout

- Portal: single column, `max-width: 34rem` for forms, `65ch` for prose.
- Console: fixed 15rem sidebar, fluid content, 22rem analysis rail. Collapses to a drawer
  under 1024px; the rail moves below the thread under 1280px.
- Spacing scale `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`. Rhythm varies by register: the portal
  uses 24–48, the console 8–16.
- Radii: `6px` controls, `10px` panels, `999px` pills only.
- One shadow, used sparingly: `0 1px 2px oklch(0 0 0 / 0.06), 0 4px 12px oklch(0 0 0 / 0.05)`.
  Elevation is carried by `--surface-2` and `--line`, not by stacked shadows.
- Z-index scale is named: `dropdown 10 · sticky 20 · backdrop 30 · modal 40 · toast 50 ·
  tooltip 60`.

## Components

Every interactive element ships default / hover / focus-visible / active / disabled, and
loading + error where it applies.

- **Buttons** — one shape. Primary (filled teal), secondary (outlined), ghost, danger. 32px
  console, 40px portal.
- **Badges** — small caps off; sentence-case labels. Status, channel and language each have a
  fixed vocabulary.
- **AnalysisPanel** — evidence bar, the terms that actually fired, clickable top-3
  alternatives, engine and engine version in the footer. Amber line naming the reason when the
  engine abstained.
- **Skeletons** for loading, never a centred spinner inside content.
- **Empty states teach**: what this queue is, why it is empty, what to do next.

## Motion

150–250ms, `cubic-bezier(0.16, 1, 0.3, 1)`. Motion conveys state only: row entering a queue,
SSE-driven badge change, panel expand, toast. No page-load choreography — the console loads
into a task.

`prefers-reduced-motion: reduce` collapses every transition to a 1ms crossfade.

## RTL

Logical properties everywhere (`margin-inline`, `padding-inline`, `inset-inline`, `border-
inline`). No `left`/`right` in component CSS. Chevrons mirror via `[dir="rtl"] .chevron
{ scale: -1 1 }`. Numbers, refs and Latin brand names stay LTR inside RTL text via
`unicode-bidi: isolate`.
