"""Regenerate (or --check) the README "Queries" section from chokepoint/queries.py."""

import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START, END = "<!-- queries:start -->", "<!-- queries:end -->"


def generated() -> str:
    out = subprocess.run([sys.executable, "-m", "chokepoint.cli", "queries", "--markdown"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return f"{START}\n{out.strip()}\n{END}"


def main():
    text = io.open(README, encoding="utf-8").read()
    i, j = text.index(START), text.index(END) + len(END)
    new = text[:i] + generated() + text[j:]
    if "--check" in sys.argv:
        if new != text:
            sys.exit("README queries section is stale: run python scripts/readme_queries.py")
        print("README queries section is up to date")
    else:
        io.open(README, "w", encoding="utf-8").write(new)
        print("README updated")


if __name__ == "__main__":
    main()
