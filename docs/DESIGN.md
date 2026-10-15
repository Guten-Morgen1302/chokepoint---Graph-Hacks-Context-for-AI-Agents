# DESIGN.md: Chokepoint

The source is `docs/PLAN.md` Part C (DR-1 … DR-12), from `/plan-design-review` on 2026-10-02.

**Mode:** OPERATE (app UI). One page.

**Use scene:** judges watch a screen recording, or open the URL on a laptop in daylight. The theme is light, and a dark theme is out of scope.

## Type

- **UI and body:** IBM Plex Sans (self-hosted woff2), weights 400, 500 and 600.
- **Code, evidence and grant IDs:** IBM Plex Mono, weight 400.
- **Tabular numerals everywhere:** `font-variant-numeric: tabular-nums`.

| Role | Size | Line height | Weight | Notes |
|---|---|---|---|---|
| Meta | 13px | 1.4 | 400 | Must still meet 4.5:1 contrast |
| Body | 15px | 1.45 | 400 | The minimum size for body text |
| Section heading | 18px | 1.3 | 600 | 24px of space above it, 8px below |
| Hero | 40px | 1.15 | 600 | Used **only** for the answer strip sentence |

Nothing other than the hero goes above 20px.

## Color (CSS variables)

```css
:root {
  --paper:  #FBFBFA;  /* background (neutral, not cream) */
  --ink:    #15181C;  /* text */
  --muted:  #5B636E;  /* secondary text, on-route edges */
  --line:   #E3E5E8;  /* hairlines, default edges, scrollbar */
  --accent: #2443D9;  /* cobalt: interactive + CUT edges (the remedy) */
  --danger: #B42318;  /* crown jewels + exposure only */
  --warn:   #B54708;  /* accepted risk, NEEDS REVIEW */
  --ok:     #1F7A4D;  /* HOLDS */
}
::selection { background: color-mix(in srgb, var(--accent) 20%, transparent); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

**Contrast:**

- All text meets 4.5:1 on `--paper`.
- The cut edge meets 3:1.
- Colour is never the only signal: badges always carry text and a shape.

## Spacing and layout

- **Spacing scale:** a 4px base, using 4, 8, 12, 16, 24, 32 and 48.
- **Design frame:** 1440×900, with 32px page gutters.
- **Regions:**

  | Region | Size |
  |---|---|
  | Top bar | 56px tall |
  | Finding header | full width |
  | Chips + input | full width |
  | Answer strip (hero) | full width |
  | Graph | 60% |
  | Right rail | 40%: Revocation plan, then Decisions, then Simulate change |
  | Evidence drawer | collapsed, built with `<details>` |

- **Radius:** 4px on interactive controls only. Containers are square and separated by hairlines.
- **Containers:** no cards and no shadows.
- **Responsive:**
  - 1024–1279px: the rail is 360px wide.
  - Below 1024px: the graph is replaced by the route list, sections stack, and targets are at least 44px.

## Graph (Cytoscape + dagre, left to right, rank separation 72px)

| Element | Style |
|---|---|
| Node | 28px circle, `--ink`, with a 13px label below |
| Finding | 32px diamond, `--ink` |
| Crown jewel | 32px square, `--danger` |
| Edge (default) | 1px, `--line` |
| Edge on a route to a jewel | 1.5px, `--muted` |
| **Cut edge** | 3px, `--accent`, dashed 6/4, with ✂ at the midpoint |
| **Accepted edge** | 2px, `--warn`, with a lock icon at the midpoint |

## Badges

| Badge | Colour | Shape |
|---|---|---|
| HOLDS | `--ok` | ● |
| HOLDS · exposure shrank | `--ok` | ● |
| NEEDS REVIEW | `--warn` | ▲ |
| STALE | `--muted` | ○ |
| SUPERSEDED | `--muted` | ○ |

## Motion

There is one authored moment: cut edges draw in over 400ms, `cubic-bezier(.2,.7,.2,1)`, after the graph is visible. Skeletons don't shimmer. Under `prefers-reduced-motion`, there is no animation.

## Bans (DR-7)

- No centred text blocks.
- No gradients, glows or halos.
- No pulsing dots or blinking cursors.
- No icon tiles and no emoji.
- No uniform large radius.
- No kicker labels above headings.
- No modals; the ticket draft opens as a right-side drawer.
- No shadows.

## Round-2 components (final; from `PLAN.md` Part C2, DR2-1 … DR2-7)

### Answer strip: 4 slots, max 200px, full width

| Slot | Spec |
|---|---|
| 1 Hero | Interim state: `Cheapest: Revoke 2 grants · cost 3`, 40px `--muted`, with `Agent checking company records…` underneath at 15px `--muted`. Final state: `Agent's plan: Revoke 3 grants · cost 5`, 40px `--ink`. The final text replaces the interim instantly, with no count-up. |
| 2 Proof | `✓ Severed: 0 routes remain (algo.maxFlow = 0)`, 15px `--ok`. Set in Sans, except `algo.maxFlow = 0`, which is Mono. The line links to its row in the evidence drawer. |
| 3 Why | Exactly one line, 15px `--ink`. Priority: fallback > override > tie. Override copy names what the extra cost saves: `+2 cost keeps DR failover working · …`. Never write "conflicts with". |
| 4 Metrics | 13px `--muted`. Example: `2 jewels reachable · 2 independent routes · shortest: 3 grants · cheapest: cost 3` |

- No narrative paragraph. That prose now lives in the Why line and in Agent review.

### Agent review: right rail, above "Revocation plan"

- Heading "Agent review", 18px.
- One line per plan, for example `A · cost 3 · ✗ revokes DR failover's grant [doc · DR Runbook §3]`.
- Rejected constraints show as `▲ rejected: <reason>` in `--muted`.
- Accessibility: `role="log"` with `aria-live="polite"`. Lines are appended only once complete. The hero announces after the log finishes.
- The raw step log stays in the evidence drawer.

### Glyphs and tokens (no collisions)

| Meaning | Glyph | Token |
|---|---|---|
| Conflict | ✗ | `--ink` |
| Rejected | ▲ | `--muted` |
| Does not sever | ✗ | `--danger` |
| Verified / severed / HOLDS | ✓ / ● | `--ok` |
| NEEDS REVIEW, accepted risk, agent-proposed | ▲ / lock | `--warn`, reserved for these three |
| Policy violation | ■ `POLICY VIOLATION` | `--danger` |
| Not reviewed / STALE / SUPERSEDED | ○ | `--muted` |

The icon allow-list (DR-7) adds ✓, ✗ and ■.

### Citations and provenance drawer

- **Citations** are underlined `--accent` links with a type prefix: `doc ·`, `ticket ·` or `msg ·`.
- **Opening a citation** opens the 480px right drawer, scrolled to the quoted text. That text gets a 2px `--accent` left rule and quotation marks, so it reads as source evidence.
- **The drawer** is non-modal and does not trap focus. On open, focus goes to the drawer heading. Esc closes it and returns focus to the link that opened it. Only one drawer is open at a time.
- **Gap rows** are highlighted, for example `No approver on record`.
- **Policy violation badge:** ■ in `--danger`.

### Accept-risk form

- Opens inline in the plan row.
- Fields: rationale, `review_by` (a date, default +30 days), and source chips. Each chip is a button labelled "Remove SEC-488". Sources are added through a combobox labelled "Add source".
- Errors: `Add at least one source.` and `Review date must be after today.`, linked with `aria-describedby`.
- **When the agent proposes it:**
  - The row gets a 2px `--warn` left rule and the label `▲ Proposed by agent · not saved` (13px `--warn`).
  - Fields are pre-filled. The `review_by` hint reads `(agent suggested)`.
  - Buttons: **Confirm acceptance** and **Discard**.
  - Nothing changes in the graph or in Decisions until the user confirms.
  - Focus never moves to the form automatically.

### Other states (final copy)

| State | Copy |
|---|---|
| Escalate | Hero `No conflict-free fix` · Why `All 3 plans break something on record` · button `Review proposed risk acceptance` |
| Fallback | Why `○ Not reviewed by agent · timed out after 60 s`. The reason variants are `declined`, `stopped after 12 steps`, `demo busy (read-only)` and `explanations offline`. |
| Budget used | `Agent tried 3 alternatives; showing the cheapest verified plan` |
| Does not sever | `✗ Plan B does not sever: 1 route remains (algo.maxFlow = 1)` in `--danger`. The hero falls back to P0. |
| Read-only proof | `✓ Severed (min-cut theorem: cut = maxFlow)` |
| Live-ingest fallback | `Ingested 1 message · 2 mentions (pre-extracted, not live)` |
| Tie | `1 of 2 equally cheap plans · chosen: stops the attacker 2 hops earlier` (15px, shown in the Why slot) |

- **Badges added:** `NEEDS REVIEW · review date passed` (▲ `--warn`) and `STALE · cited source removed` (○ `--muted`).
- **Cost breakdown:** shown inline when a plan row is expanded, not in a hover tooltip. Example: `cost 9 = base 1 + used 142×/30d (+8)`, then on a separate line `breaks: none on record`.
