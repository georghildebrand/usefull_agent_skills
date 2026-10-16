"""Inline index.html and all its <script src> files into one offline file: explainer.html.

Run: python3 build.py   (after bash tools/fetch-three.sh). The result opens from disk, a USB stick or an email.

python3 build.py --voice  writes explainer-voice.html instead: the same page plus the spoken line of every scene.
  It needs the voice from tools/narrate.sh (out/audio/sceneNN.wav and durations.json; tools/render.sh makes them).
  Each scene WAV is encoded to Opus (mono, about 24 kb/s; AAC in .m4a when ffmpeg has no libopus) and embedded as a
  base64 data URI, with the timing table, so each scene lasts as long as its line. Options: --audio DIR, --out FILE.
"""
import argparse
import base64
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
LIMIT = 1_000_000  # bytes; three.min.js alone is about 0.6 MB
VOICE_LIMIT = 4_000_000  # bytes; Opus at 24 kb/s in base64 is about 40 KB per 10 s of speech
MAIN = '<script src="src/main.js"></script>'


def has_libopus() -> bool:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return " libopus " in out


def voice_script(audio: pathlib.Path) -> str:
    """One <script> that sets EX.TIMING and EX.VOICE (one data URI per scene)."""
    timing_file = audio / "durations.json"
    if not timing_file.exists():
        sys.exit(f"missing {timing_file}: make the voice first (bash tools/render.sh, or tools/narrate.sh)")
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found: it encodes the voice for the page")
    timing = json.loads(timing_file.read_text(encoding="utf-8"))
    wavs = [audio / f"scene{k:02d}.wav" for k in range(1, len(timing["scenes"]) + 1)]
    missing = [str(w) for w in wavs if not w.exists()]
    if missing:
        sys.exit("missing scene WAVs: " + ", ".join(missing))
    opus = has_libopus()
    codec = ["-c:a", "libopus", "-b:a", "24k", "-f", "ogg"] if opus else ["-c:a", "aac", "-b:a", "32k", "-f", "mp4"]
    mime = "audio/ogg;codecs=opus" if opus else "audio/mp4"
    uris = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, wav in enumerate(wavs, 1):
            dst = pathlib.Path(tmp) / f"scene{k:02d}.{'ogg' if opus else 'm4a'}"
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-ac", "1", *codec, str(dst)],
                           check=True)
            uris.append(f"data:{mime};base64," + base64.b64encode(dst.read_bytes()).decode("ascii"))
    print(f"voice: {len(uris)} scenes as {'Opus' if opus else 'AAC (no libopus in this ffmpeg)'}, "
          f"{sum(len(u) for u in uris)} bytes of data URIs")
    keep = {k: timing[k] for k in ("fps", "total_frames", "total_s") if k in timing}
    keep["scenes"] = [{k: s[k] for k in ("text", "frames", "start_frame") if k in s} for s in timing["scenes"]]
    return ("<script>\n/* voice: made by build.py --voice from " + audio.name + "/ */\n"
            "self.EX = self.EX || {};\nEX.TIMING = " + json.dumps(keep).replace("</", "<\\/") + ";\nEX.VOICE = " + json.dumps(uris) + ";\n</script>")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the single offline file.")
    ap.add_argument("--voice", action="store_true", help="embed the spoken lines (explainer-voice.html)")
    ap.add_argument("--audio", default=str(ROOT / "out" / "audio"), help="folder with sceneNN.wav and durations.json")
    ap.add_argument("--out", help="output file (default: explainer.html, or explainer-voice.html with --voice)")
    a = ap.parse_args()
    out_file = pathlib.Path(a.out) if a.out else ROOT / ("explainer-voice.html" if a.voice else "explainer.html")
    limit = VOICE_LIMIT if a.voice else LIMIT

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if a.voice:
        if MAIN not in html:
            sys.exit(f"index.html has no {MAIN}: the voice script goes right before it")
        html = html.replace(MAIN, voice_script(pathlib.Path(a.audio)) + "\n" + MAIN)

    def inline(match: re.Match) -> str:
        src = match.group(1)
        path = ROOT / src
        if not path.exists():
            sys.exit(f"missing {src} (for vendor/three.min.js run: bash tools/fetch-three.sh)")
        code = path.read_text(encoding="utf-8").replace("</script", "<\\/script")
        return f"<script>\n/* {src} */\n{code}\n</script>"

    out = re.sub(r'<script src="([^"]+)"></script>', inline, html)
    out_file.write_text(out, encoding="utf-8")
    size = out_file.stat().st_size
    print(f"{out_file} {size} bytes")
    if "<script src=" in out:
        print("a script tag was not inlined", file=sys.stderr)
        return 1
    if size > limit:
        print(f"too large: {size} > {limit}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
