"""English voice-over for the demo via Gemini TTS, one clip per scene → video/out/vo/NN.wav + timing.json.

  ../.venv/Scripts/python make_vo.py            # all lines
  ../.venv/Scripts/python make_vo.py 7 8        # only re-generate lines 7 and 8
  ../.venv/Scripts/python make_vo.py --check    # ONE Gemini call: transcribe every wav, flag lines that drifted

Each line has the scene start (seconds on the video timeline) and the max length it may take.
Grant ids are spelled out ("G one-oh-two") so the TTS reads them the way the UI shows them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
OUT = HERE / "out" / "vo"
MODEL = os.getenv("VO_MODEL", "gemini-3.8-flash-tts")
VOICE = os.getenv("VO_VOICE", "Fenrir")
CHECK_MODEL = os.getenv("VO_CHECK_MODEL", "gemini-3.5-flash")

# (start_seconds, max_seconds, text). Scene starts come from src/Root.tsx.
LINES: list[tuple[float, float, str]] = [
    (0.3, 5.4, "A deploy token just leaked. Forty alerts. One question: what do you cut?"),
    (6.3, 3.9, "Meet Chokepoint."),
    (10.8, 8.4, "Revoke everything, and the company breaks. Take the cheapest cut, and disaster recovery breaks. "
                "You need the cheapest cut that's safe."),
    (19.8, 6.3, "One app, one FalkorDB graph, three tracks: an agent, a memory, and a company brain."),
    (26.3, 4.6, "Step one: pure graph maths. Max-flow finds the cheapest cut."),
    (31.3, 9.5, "Then Gemini reads the runbooks. G one-oh-two runs disaster recovery, so it asks the graph "
                "for a plan that keeps it. Cost six, every route cut."),
    (41.2, 4.9, "Every claim links to its real source. Invented citations get rejected."),
    (46.5, 11.8, "Under the hood, grants are nodes, and FalkorDB's max-flow finds the minimum cut. "
                 "The model never computes a cut. It asks, and the server proves zero routes remain."),
    (59.0, 7.6, "Why does this access exist? The ticket, who asked, who approved, and the chat that says it can go."),
    (67.0, 5.6, "A person accepts the risk, with a reason and a review date. The graph remembers."),
    (73.0, 7.2, "Then the world changes. Deployer gets payroll access, and the old decision flags itself for review."),
    (80.5, 10.6, "Ask a question in plain English. The remembered decision already shapes the new plan, "
                 "and the answer cites the ticket and the chat."),
    (91.7, 7.4, "Nothing is hidden. Every Cypher query and every max-flow call is right there."),
    (99.5, 9.4, "A hundred and twenty-eight tests on a real FalkorDB, and six out of six live Gemini runs kept recovery safe."),
    (109.5, 6.0, "Chokepoint. Find the cut. Prove it. Remember why."),
]


def tts(client: genai.Client, text: str) -> bytes:
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE))),
    )
    for attempt in range(4):
        try:
            r = client.models.generate_content(model=MODEL, contents=text, config=cfg)
            return r.candidates[0].content.parts[0].inline_data.data
        except Exception as e:  # noqa: BLE001 (rate limits / transient errors: back off and retry)
            print(f"   retry {attempt + 1}: {type(e).__name__}: {str(e)[:120]}")
            time.sleep(8 * (attempt + 1))
    raise SystemExit(f"TTS failed for: {text[:60]}")


def write_wav(path: Path, pcm: bytes) -> float:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return len(pcm) / 2 / 24000


def trim_and_fit(src: Path, dst: Path, max_s: float) -> float:
    """Trim silence at both ends; speed up (≤ 1.25×) only if the line would overrun its scene."""
    tmp = dst.with_suffix(".trim.wav")
    trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", trim, str(tmp)], check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(tmp)]))
    tempo = max(1.0, dur / max_s)
    if tempo > 1.25:
        print(f"   ⚠️ {dst.name}: {dur:.1f}s for a {max_s}s slot, even 1.25× overruns; shorten the text")
        tempo = 1.25
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", f"atempo={tempo:.3f}", "-ar", "44100", str(dst)], check=True)
    tmp.unlink()
    return dur / tempo


def words(t: str) -> list[str]:
    return re.findall(r"[a-z]+", t.lower().replace("one-oh-two", "102"))


def check(client: genai.Client) -> None:
    """Transcribe all lines in a single request and flag any whose words drifted from the script."""
    parts = [types.Part(text="Transcribe each of the following audio clips verbatim. Reply with only a JSON array of strings, one per clip, in order.")]
    for i in range(1, len(LINES) + 1):
        parts.append(types.Part.from_bytes(data=(OUT / f"{i:02d}.wav").read_bytes(), mime_type="audio/wav"))
    r = client.models.generate_content(model=CHECK_MODEL, contents=[types.Content(role="user", parts=parts)],
                                       config=types.GenerateContentConfig(response_mime_type="application/json"))
    heard = json.loads(r.text)
    bad = []
    for i, ((_, _, text), got) in enumerate(zip(LINES, heard), 1):
        want, have = set(words(text)), set(words(got))
        score = len(want & have) / max(1, len(want))
        flag = "OK " if score >= 0.85 else "BAD"
        if flag == "BAD":
            bad.append(i)
        print(f"{flag} {i:02d} {score:.2f}  {got}")
    print("regenerate:", " ".join(map(str, bad)) if bad else "nothing")


def main(only: set[int]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    timing_path = OUT / "timing.json"
    timing = json.loads(timing_path.read_text()) if timing_path.exists() else {}
    for i, (start, max_s, text) in enumerate(LINES, 1):
        if only and i not in only:
            continue
        raw = OUT / f"{i:02d}.raw.wav"
        final = OUT / f"{i:02d}.wav"
        print(f"{i:02d} @ {start:6.1f}s  {text[:70]}")
        write_wav(raw, tts(client, text))
        dur = trim_and_fit(raw, final, max_s)
        raw.unlink()
        timing[f"{i:02d}"] = {"start": start, "dur": round(dur, 2), "max": max_s}
        print(f"   → {dur:.1f}s (slot {max_s}s)")
        time.sleep(1.5)
    timing_path.write_text(json.dumps(timing, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--check" in sys.argv:
        check(genai.Client(api_key=os.environ["GEMINI_API_KEY"]))
    else:
        main({int(a) for a in sys.argv[1:]})
