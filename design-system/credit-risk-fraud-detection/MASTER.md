# Design system: Credit Risk & Fraud Detection

The source of truth for how the interface looks and moves. Values live in
`app/static/css/tokens.css`; this page explains them. Page-specific overrides, if any are ever
needed, go in `pages/<page>.md` next to this file.

## Idea

The interface borrows from the craft of stopping fraud on paper: the engraved guilloche line-work of
banknotes and cheques, eye-ease ledger paper, and two rubber-stamp inks. Blue ink means an
application was **cleared**, red ink means it was **flagged**. The boldness is spent in one place,
the line-work and the stamp; everything around them is quiet: hairline rules, white cards,
restrained radii.

## Tokens

Three layers, each referring only to the one above it. Components never use a primitive or a raw
colour.

| Layer | Example | Changes when |
| --- | --- | --- |
| Primitive | `--blue-600: #2055be`, `--space-4: 1rem` | Rarely |
| Semantic | `--color-accent`, `--color-risk`, `--text-body` | The theme changes |
| Component | `--button-bg`, `--field-border`, `--gauge-track` | One component needs tuning |

Light and dark values sit side by side in `light-dark()`, so a theme is a single `color-scheme`
switch. The toggle sets `data-theme` on `<html>`; without a choice the system theme applies.

### Colour

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| Page | ink-50 `#f2f7f4` | pine-950 `#0b120e` | Ledger-paper background |
| Surface | white | pine-900 `#121b16` | Cards |
| Text | ink-950 `#0e130f` | ink-50 | 17:1 on the page |
| Muted text | ink-600 `#5a635c` | ink-400 `#97a19a` | 5.7:1 and 7.1:1 |
| Control border | ink-450 `#8a948d` | pine-500 `#5f6d65` | 3:1 against the surface |
| Accent, cleared | blue-600 `#2055be` | blue-300 `#91b7fe` | Actions, links, cleared verdicts |
| Risk, flagged | red-600 `#c3321e` | red-400 `#f7745f` | Flagged verdicts, errors |
| Caution | amber-700 `#795200` | amber-300 `#f6bc5d` | Warnings |

Ramps were derived in OKLCH (ink hue 155, blue 262, red 31, amber 78) and every text pair was checked
against WCAG AA. A verdict never relies on colour alone: it always carries a word and an icon.

### Charts

Bars and segments use `--color-data-clear` and `--color-data-risk` (blue-500 and red-500 in light,
blue-450 and red-450 in dark). The pair passes a colour-vision-deficiency check in both themes
(worst simulated difference ΔE 23, against a floor of 8). Bars are thin with a rounded value end and
a square baseline, values sit at the bar tip, and every chart has a table view.

### Type

IBM Plex Sans, self-hosted as one variable file (weight 100-700, width 75-100%). Display sizes use
the 82% width; everything else the normal width. Its figures are already equal-width, so numbers line
up in tables without a monospace face. IBM Plex Mono appears only for code and the card number.

| Role | Size | Notes |
| --- | --- | --- |
| Display | 40-68px, fluid | Semibold, condensed, -0.02em |
| Title | 32-40px, fluid | Semibold, condensed |
| Heading | 21px | Semibold |
| Body | 16px / 1.55 | |
| Label | 14px | Medium |
| Caption | 12px | |

### Space, shape, elevation

4px base scale (`--space-1` 4px to `--space-24` 96px). Radii by hierarchy: 4px marks, 8px controls,
12px cards, full for chips. Shadows are sparse and tinted with ink: `sm` for cards, `lg` for toasts,
menus and the illustration.

## Components

Buttons (primary, secondary, ghost, icon; sizes sm, md, lg; a busy state that swaps the label for a
spinner without changing size), fields with help text and an error slot tied by
`aria-describedby`, segmented controls (radio groups with a sliding thumb), selects, badges, inline
alerts, toasts, stat rows, tables, meters, filter chips, view switches, horizontal bar charts, the
share bar, the confusion matrix, the risk gauge, the stamp and the dropzone. Main controls are 44px
tall and secondary ones 36px; nothing interactive is smaller than 24px, and everything shows a 2px
focus ring.

## Motion

Timing tokens: instant 90ms (press), fast 150ms (hover, exits), base 240ms, slow 420ms (entrances),
slower 720ms (gauge, bars), draw 1400ms (line-work). Curves: `--ease-out` to arrive, `--ease-in` to
leave, `--ease-spring` for the toggles, `--ease-thump` for the stamp.

Rules:

- Only transform, opacity, clip-path and stroke-dashoffset animate, so nothing reflows mid-motion.
- Leaving takes about 60% as long as arriving.
- One orchestrated moment per page on load; everything else answers something the person did.
- Anything that starts hidden is gated on `html.js`, and a fallback timer shows everything if the
  script never runs.
- With reduced motion, every element arrives in its final state at once. The only motion kept is a
  busy spinner, because it carries information.

The moments:

| Where | What happens |
| --- | --- |
| Home | The rosette's lines are drawn ring by ring; the card and the statement rise in; a beam reads the statement, ticks pop in, and the FLAGGED stamp lands on the new-car row, which turns red. Plays once, about three seconds. |
| Sign in | The rosette behind the card is drawn. |
| Predict | Loading an example lights up each field it fills. On submit the dial's needle sweeps to the score while the number counts with it, then the stamp comes down and the slip takes the knock. |
| Results | Counters roll up; the share bar wipes in; filtered rows fade in, the first fourteen one after another. |
| Analytics | Bars grow from the baseline, and grow again when the grouping changes. |
| Performance | Switching between the weighted and unweighted model rolls every figure from its old value to its new one and re-tints the confusion matrix. |
| Everywhere | Pages cross-fade and the navigation underline slides to the new page (View Transitions); switching theme spreads the new colours out from the toggle. |

## Accessibility

Skip link, one `h1` per page, labelled landmarks, visible labels on every field, errors announced
and linked from a summary that takes focus, results and toast messages announced through a polite
live region, scrollable tables reachable by keyboard, charts with text labels and a table view, and
no information carried by colour alone.
