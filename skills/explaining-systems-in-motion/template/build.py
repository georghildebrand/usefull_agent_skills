"""Inline index.html and all its <script src> files into one offline file: explainer.html.

Run: python3 build.py   (after bash tools/fetch-three.sh). The result opens from disk, a USB stick or an email.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "explainer.html"
LIMIT = 1_000_000  # bytes; three.min.js alone is about 0.6 MB


def main() -> int:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    def inline(match: re.Match) -> str:
        src = match.group(1)
        path = ROOT / src
        if not path.exists():
            sys.exit(f"missing {src} (for vendor/three.min.js run: bash tools/fetch-three.sh)")
        code = path.read_text(encoding="utf-8").replace("</script", "<\\/script")
        return f"<script>\n/* {src} */\n{code}\n</script>"

    out = re.sub(r'<script src="([^"]+)"></script>', inline, html)
    OUT.write_text(out, encoding="utf-8")
    size = OUT.stat().st_size
    print(f"{OUT} {size} bytes")
    if "<script src=" in out:
        print("a script tag was not inlined", file=sys.stderr)
        return 1
    if size > LIMIT:
        print(f"too large: {size} > {LIMIT}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
