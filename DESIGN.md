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
vocabulary. The accent is teal — chosen because it is not Ooredoo red, not Orange orange and
not Tunisie Telecom blue, so the product cannot be mistaken for any operator's own property.

All values OKLCH.

### Core

| Role | Light | Dark |
|---|---|---|
| `--bg` | `oklch(1 0 0)` — literal white | `oklch(0.19 0.012 210)` |
| `--surface` | `oklch(0.985 0.004 190)` | `oklch(0.235 0.014 210)` |
| `--surface-2` | `oklch(0.965 0.006 190)` | `oklch(0.275 0.016 210)` |
| `--ink` | `oklch(0.22 0.015 210)` | `oklch(0.96 0.004 190)` |
| `--ink-muted` | `oklch(0.46 0.014 210)` | `oklch(0.72 0.012 200)` |
| `--line` | `oklch(0.90 0.006 200)` | `oklch(0.33 0.016 210)` |
| `--primary` | `oklch(0.52 0.10 185)` | `oklch(0.72 0.11 185)` |
| `--primary-ink` | `oklch(0.99 0 0)` | `oklch(0.17 0.02 200)` |

`--ink-muted` is deliberately darker than the usual "elegant grey": 4.6:1 on `--surface` in
light, 4.8:1 in dark. Placeholders use `--ink-muted`, not a lighter step.

### Semantic — rationed on purpose

- `--amber` `oklch(0.76 0.14 75)` — **reserved.** SLA warning and `needs_human_triage`. It
  appears nowhere else, so an amber pixel always means "a human needs to look at this".
- `--danger` `oklch(0.58 0.19 25)` — SLA breach, P1, destructive actions.
- `--success` `oklch(0.60 0.12 155)` — resolved, promoted model.
- `--info` = `--primary`.

### Priority is an intensity ramp, not a rainbow

P1 → P4 walks one hue from saturated red to neutral: `danger` → `danger` at 55% → `ink-muted`
→ `ink-muted` at 60%. Four arbitrary hues would collide with the semantic set and fail for
colour-blind users. Every badge also carries its literal label (`P1 CRITIQUE`), so hue is
reinforcement, never the signal.

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
- Console: fixed 15rem sidebar, fluid content, optional 22rem analysis rail. Collapses to a
  drawer under 1024px; the rail moves below the thread under 1280px.
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
- **Badges** — small caps off; sentence-case labels. Priority, status, SLA and language each
  have a fixed vocabulary.
- **AnalysisPanel** — confidence bar, clickable top-3 alternatives, rule hits as rows of
  `label · matched tokens · weight`, engine + model version in the footer. Amber banner when
  `needs_human_triage`, naming the reason.
- **SLABadge** — green / amber >80% / red breached, with a live countdown and a text state.
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
