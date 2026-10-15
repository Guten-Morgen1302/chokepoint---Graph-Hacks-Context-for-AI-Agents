#!/usr/bin/env bash
# Cuts video/raw/demo-raw.mp4 (the 2 Oct live run, recorded by Playwright at 1440×900) into the sped-up clips the video uses.
# Footage is never edited, only cut and sped up. Nothing private is on screen (synthetic Northwind data), so no blur pass.
# name  source-start  source-end  speed
set -euo pipefail
cd "$(dirname "$0")"
IN="raw/demo-raw.mp4"
mkdir -p public/clips
cut() { ffmpeg -v error -y -ss "$2" -to "$3" -i "$IN" -an -vf "setpts=PTS/$4,fps=30,scale=1440:900" \
  -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "public/clips/$1.mp4"; }
cut c1_triage   3.7  8.7  1     # Triage F-1 → graph-only cheapest cut appears
cut c2_agent    8.7  26.2 1.75  # Gemini reads records, what_if keep G-102, P1 chosen, severed
cut c3_cite     27.2 32.4 1     # click doc:dr-runbook → the quoted runbook text
cut c4_brain    32.4 42.0 1.2   # "Why does G-101 exist?" → ticket, people, chat, who knows
cut c5_accept   42.0 51.0 1.5   # accept risk on kept G-102: reason, review date, sources → Memory: 1
cut c6_recheck  53.6 61.1 1     # simulate: deployer READS hr-payroll-db → NEEDS REVIEW
cut c7_ask      62.4 84.8 2     # ask "why does ci-deploy have deployer?" → cited answer
cut c8_evidence 85.4 93.2 1     # evidence drawer: every Cypher query, maxFlow calls, timings
for f in public/clips/*.mp4; do printf '%s %s\n' "$(basename "$f")" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"; done
