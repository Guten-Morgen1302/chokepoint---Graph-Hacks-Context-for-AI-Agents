# Chokepoint demo video

Motion graphics in [Remotion](https://www.remotion.dev) around a real live run of the app recorded on 2 Oct 2026. 1920×1080, 30 fps, 1:57.

```bash
cd video
npm install
bash cut_clips.sh                      # needs raw/demo-raw.mp4 (not in git)
npx remotion studio src/index.ts       # preview + scrub in the browser
npx remotion render src/index.ts Chokepoint out/chokepoint-silent.mp4 --codec=h264 --crf=18
npx remotion still src/index.ts Thumbnail out/thumbnail.png
bash make_music.sh 117.2               # synthesized 120 BPM beat → out/music.wav
../.venv/Scripts/python make_vo.py     # English voice-over via Gemini TTS (voice Fenrir) → out/vo/
../.venv/Scripts/python make_vo.py --check   # one Gemini call: transcribe all lines, flag drift
../.venv/Scripts/python mix_audio.py   # voice + music ducked under it → out/chokepoint.mp4
```

The end-card URL is `END_URL` in `src/theme.ts`.

## How the footage was made

- The raw recording is one continuous Playwright session. It drives the real UI at `localhost:8000`, with the live Gemini agent (`gemini-3.5-flash`) and FalkorDB Cloud (`ap-south-1`).
- Playwright draws a blue cursor ring so viewers can see the clicks. Nothing else is injected.

## Honesty rules

- Every browser frame is unedited footage of that run, only cut and sped up. Each scene shows its speed (1× to 2×).
- The camera zooms and the callout rings are drawn on top and never change the pixels underneath.
- All data is the synthetic Northwind Labs scenario, so nothing is blurred.
- **Animated, not recorded:** the cold open, logo, problem, tracks, min-cut, stats and end card. These use the same numbers as the app: P0 cost 5, P1 cost 6, cost 19 to revoke everything, 888 nodes, 958 attack edges, 1,461 context edges.
- **"6/6 live Gemini runs"** counts every 2 Oct run on F-1 that got a model answer:
  - 1 run on `gemini-2.5-flash` and 5 on `gemini-3.5-flash`;
  - runs cut off by the free-tier quota fell back to the graph's plan and are not counted. The stats card footnote says so.

| Scene | Source | Clip |
|---|---|---|
| Cold open, logo, problem, tracks | animation | |
| Triage: graph-only cheapest cut | 0:03.7–0:08.7 @1× | c1_triage |
| Agent: explain → what_if keep G-102 → P1, severed | 0:08.7–0:26.2 @1.75× | c2_agent |
| Citation → DR runbook quote | 0:27.2–0:32.4 @1× | c3_cite |
| Min-cut under the hood | animation | |
| Company brain: why does G-101 exist? | 0:32.4–0:42.0 @1.2× | c4_brain |
| Memory: accept risk on kept G-102 | 0:42.0–0:51.0 @1.5× | c5_accept |
| Re-check: deployer READS hr-payroll-db → NEEDS REVIEW | 0:53.6–1:01.1 @1× | c6_recheck |
| Ask: why does ci-deploy have deployer? | 1:02.4–1:24.8 @2× | c7_ask |
| Evidence drawer | 1:25.4–1:33.2 @1× | c8_evidence |
| Stats, end card | animation | |

## YouTube

**Title:** Chokepoint: the cheapest safe fix for a leaked token, proven on a FalkorDB graph (Graph Hacks 2026)

**Description:**

> A CI token leaks. Revoking everything breaks the company; the cheapest cut breaks disaster recovery. Chokepoint finds the cheapest cut that's actually safe:
> - FalkorDB's `algo.maxFlow` computes the min cut.
> - A Gemini agent checks it against the company's runbooks, tickets and chat.
> - The server proves zero attack routes remain.
>
> Risk decisions live in the graph and re-check themselves when access changes. Tickets, people, chat and policy are linked to the exact grant they explain.
>
> All three Graph Hacks tracks in one app: an agent that acts on the graph, memory, and a company brain.
>
> Every screen recording is a real live run (2 Oct 2026), only sped up.

**Chapters:**

```
0:00 A token leaked
0:06 Chokepoint
0:10 Cut the attacker off, not the company
0:19 One app, one graph, three tracks
0:26 Step 1: graph maths (algo.maxFlow)
0:31 Step 2: Gemini reviews the cut
0:41 Every claim has a source
0:46 Under the hood: min cut + verify
0:58 Company brain: why does this access exist?
1:06 Memory: a person accepts the risk
1:12 The decision re-checks itself
1:20 Ask anything
1:31 Every query on screen
1:39 Stats
1:49 Find the cut. Prove it. Remember why.
```
