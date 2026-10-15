# Design review: outside voice (Claude design subagent, 2026-10-02)

The findings were integrated into `docs/PLAN.md` Part C. The one exception: the subagent proposed a dark `#0E1116` theme with Inter and red cut edges, and that was rejected in DR-10 (light IBM Plex theme, cobalt cut edges).

## Findings

**1. The first screen isn't defined (critical).** The answer card only exists after an LLM run, so before that the page is an empty input box: the generic chat UI the plan wants to avoid.
**Fix:** show the F-1 finding header and a "Triage F-1" button. Run the deterministic tools first, with no LLM, so numbers appear in under 1s. *Adopted as DR-1.*

**2. During loading, the step log comes before the answer (high).**
**Fix:** a card skeleton that fills in as each tool's result arrives. The step log goes in the evidence drawer. *Adopted as DR-5.*

**3. No visual anchor for the hero number (high).** "Cost 3 vs naive 9" is the whole pitch, but it has no visual treatment.
**Fix:** a large numeral with the naive cost struck through. *Adopted as DR-3, at 40px.*

**4. The graph geometry is ambiguous (high).**
**Fix:** a dagre layout running left to right, showing only the exposure subgraph, with distinct cut, accepted and structural edge styles, and a 60/40 split between graph and side panel. *Adopted as DR-2/DR-10. Cut edges are cobalt, not red.*

**5. Demo beats 4–7 have no UI (critical).**
**Fix:**
- an inline "Accept risk" control with a rationale field
- the previous cut kept visible, struck through
- a "New session" control plus a memory chip
- a "Simulate change" strip

*Adopted as DR-4.*

**6. Missing states (high).** Not covered:
- owners and tickets
- the NEEDS_REVIEW and SUPERSEDED badges
- the non-unique cut
- the Claude outage, 429 and read-only banners
- graph unavailable
- timeouts
- the numeric-guard marker
- truncated `ask_graph` results
- "no revocable cut"

*Adopted as the DR-5 state matrix.*

**7. Nothing concrete is specified (critical).** No fonts, sizes, colours, spacing or viewport.
*Adopted as DR-10, with a different palette and typeface: light theme, IBM Plex.*

**8. The copy will cause trouble later (medium).** The metric label is too long, and hops vs grants is confusing.
**Fix:** "7 independent routes" with a tooltip, and count grants only. *Adopted as DR-9.*

**9. The input model is undefined (medium).**
**Fix:** chips plus free text. *Adopted as DR-8.*

## Litmus checks (before fixes)

| Check | Answer |
|---|---|
| Product unmistakable on the first screen? | NO |
| One visual anchor? | NO |
| Scannable by headings? | NO |
| One job per section? | YES, mostly |
| Cards necessary? | Only the answer card |
| Motion improves hierarchy? | NO |
| Premium without shadows? | NO (no visual system yet) |

**Hard-rejection risk:** "app UI as stacked cards". Fixed by the DR-2 layout.
