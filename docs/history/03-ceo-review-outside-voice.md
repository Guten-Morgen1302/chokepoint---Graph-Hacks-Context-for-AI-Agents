# Cold read: Chokepoint working plan

## 1. The FREE/FORCED rule does not match npm, and the oracle it chose will prove it
The plan classifies on **the last hop only**: "FREE if the declared range on its last hop admits a fixed version." `npm audit fix` does not work that way. It searches the whole path, bumping *intermediate* packages within their own parents' ranges to releases whose dependency ranges no longer admit the vulnerable version. Paths your rule calls FORCED are routinely fixed by plain `npm audit fix`. So the classification and the chosen oracle (`npm audit --json` `fixAvailable`) compute different functions — you have wired the demo's credibility to a test that will fail on correct-looking data. Related: `npm update` ≠ `npm audit fix` (update won't touch package.json ranges; audit fix will, non-major), yet the demo line is "`npm update` fixes 17." And "with no breaking major" is a no-op: if the declared range admits the fixed version, there is no major bump. `isSemVerMajor` in npm's output is about the *top-level* dep, not the vulnerable one.

## 2. Fix the rule correctly and the hero goes vacuous
Define FORCED properly (no in-range upgrade *anywhere* on the path removes the vuln) and every node on a forced path is, by construction, not in-range upgradeable. Then "change these 2 chokepoint packages" means "force an override or replace a direct dependency" — the min cut's answer collapses back toward "the direct parents," which is R1-4, the exact triviality CEO-1 was supposed to kill. CEO-1 traded one trivial cut for another, one layer deeper. Also note `npm overrides` supports path-scoped keys (`"a > b": "x"`), so the "an override breaks that parent's contract org-wide" premise is a policy assertion, not a technical one, and a judge who knows npm will say so — same failure mode as R2-8, re-created.

## 3. The incident swap orphans the pre-Oct-15 answer key, with no screening method
Repo selection, `notes/oracle/`, and The Assignment are all built around `request`. The new criterion — "≥1 FORCED path in ≥2 services" — cannot be screened with `npm ls`; it needs the classifier, which is product code banned until Oct 15. Chicken-and-egg, unflagged. Worse: `semver` CVE-2022-25883, `minimist`, `json5` are the *most* fixable advisories in existence; on 2023–24 lockfiles the forced set is plausibly **empty**. Your only contingency is an empty state reading "npm update fixes all" — i.e. no hero. No fallback incident, no candidate-pool size, no screening procedure.

## 4. Per-edge ranges make R2-1 worse, and the plan punts it
Classification needs the declared range per edge. Merged `name@version` nodes merge edges whose ranges differ across install paths, so the range is ambiguous before the semver check even runs. CEO-1 deepened a known-open correctness bug and left it in eng's lap without noting the dependency.

## 5. "SCOPE REDUCTION" is cosmetic
Five deferred items were all stretch/speculative. Added: semver lib, per-edge ranges, second oracle, new narration, no-LLM button UI (S1-2, a whole second surface, unbudgeted), repo re-selection. File count unchanged at ~25. Net scope is **up**.

## 6. CUT-1 and CUT-6 contradict each other
Ad-hoc Cypher removed; free-form questions kept. Judges typing their own questions now hit six typed tools and a shrug.

## 7. Track 01 self-harm
The new differentiator (FREE/FORCED) is pure Python semver math — zero graph work — and it *shrinks* the graph the cut runs on. Rule 3 gets weaker, not stronger.

## 8. Track 02 unattended
Beat 6 still uses the svc-docs dev-only HOLDS example that R2-12 proved self-contradictory, and R2-11/13/14 are all punted while the demo's closing beat depends on them.

**Simpler alternative:** drop classification. Keep the cut on the full exposure graph but make capacities encode remediation cost (direct dep = 1, transitive = ∞ unless overrides allowed, toggled per policy). Non-trivial by construction, more graph work, one oracle, no npm-semantics exposure.

Recommendation: **Revise CEO-1 before eng review** because the last-hop FREE/FORCED rule contradicts `npm audit fix`'s actual algorithm and the very oracle chosen to validate it, and fixing the rule correctly makes the forced-residual cut trivial again.