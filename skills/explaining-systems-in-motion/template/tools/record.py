#!/usr/bin/env python3
"""Record the explainer page frame by frame with headless Chrome, then (optionally) encode an MP4.

How it works:
  1. A small http.server on 127.0.0.1 serves the template folder (so the page, vendor/,
     src/ and out/audio/ share one origin: no CORS, no file:// limits) and receives frames.
  2. Headless Chrome opens  http://127.0.0.1:<port>/<page>?record&w=&h=&fps=&fmt=&start=&timing=
     The page does not use wall-clock time. For frame n it sets t = n*1000/fps, renders,
     draws the WebGL canvas plus the overlays onto a 2D canvas and POSTs /frame/<n+1>.
     The page decides the frame count: the timing file (from tools/narrate.sh), or without
     one each scene's anim + hold.
  3. The page POSTs /log (printed), then /done (or /fail). The receiver stops, the script stops Chrome.
  4. With --mp4, ffmpeg joins the frames (and --audio, if given) into an H.264 + AAC MP4.

Usage (from the template folder):
  python3 tools/record.py --out out/frames --w 1280 --h 720 --fps 30 \
      [--timing out/audio/durations.json] [--fmt png|jpeg] [--gl swiftshader|metal] \
      [--audio out/audio/narration.wav --mp4 out/explainer.mp4]
Env: CHROME=/path/to/chrome (default: Google Chrome on macOS, else google-chrome or chromium on PATH).
Exit code 0 only when every frame arrived and (if asked) the MP4 was written.
"""
import argparse
import http.server
import json
import os
import pathlib
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def chrome_path() -> str:
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    if pathlib.Path(MAC_CHROME).exists():
        return MAC_CHROME
    for name in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit("no Chrome found: set CHROME=/path/to/chrome")
GL_FLAGS = {
    "swiftshader": ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
    "metal": ["--use-angle=metal", "--ignore-gpu-blocklist", "--enable-gpu"],
}


class State:
    def __init__(self, out: pathlib.Path, ext: str):
        self.out, self.ext = out, ext
        self.done = threading.Event()
        self.error = None
        self.count = 0
        self.t_first = None
        self.t_last = None
        self.viewport = None


# A page that reports the size of its viewport. Headless Chrome keeps part of the window for its own bar
# (87 px in height with Chrome 155), so the window must be larger than the video by that amount.
VIEWPORT_PAGE = (b"<!doctype html><script>fetch('/viewport',{method:'POST',body:innerWidth+' '+innerHeight})"
                 b".then(()=>fetch('/done',{method:'POST',body:'{}'}))</script>")


def make_handler(state: State, serve_root: pathlib.Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve_root), **kw)

        def log_message(self, *a):  # keep the console quiet
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self):
            if urllib.parse.urlparse(self.path).path == "/__viewport":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(VIEWPORT_PAGE)
                return
            super().do_GET()

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if path.startswith("/frame/"):
                n = int(path.rsplit("/", 1)[1])
                (state.out / f"{n:06d}.{state.ext}").write_bytes(body)
                now = time.monotonic()
                state.t_first = state.t_first or now
                state.t_last = now
                state.count += 1
                if n % 150 == 0:
                    print(f"  frame {n}", flush=True)
            elif path == "/viewport":
                state.viewport = tuple(int(v) for v in body.split())
            elif path == "/log":
                for line in body.decode("utf-8", "replace").splitlines():
                    print(f"  page: {line}", flush=True)
            elif path == "/done":
                state.done.set()
            elif path == "/fail":
                state.error = body.decode("utf-8", "replace")
                state.done.set()
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(204)
            self.end_headers()

    return Handler


def encode(frames: pathlib.Path, ext: str, fps: int, audio, mp4: pathlib.Path) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-framerate", str(fps), "-i", str(frames / f"%06d.{ext}")]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-movflags", "+faststart", str(mp4)]
    print("  " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def frames_on_disk(out: pathlib.Path, ext: str) -> int:
    """Number of frames 1..k that exist without a gap."""
    k = 0
    while (out / f"{k + 1:06d}.{ext}").exists():
        k += 1
    return k


def launch(a, state: State, target: str, window, timeout: float):
    """Serve --serve-root, open http://127.0.0.1:<port>/<target> in headless Chrome and wait for /done or /fail.
    Returns (wall seconds, None | "timeout" | "stall")."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state, pathlib.Path(a.serve_root)))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/{target}"
    profile = tempfile.mkdtemp(prefix="record-chrome-")
    cmd = [chrome_path(), "--headless=new", f"--user-data-dir={profile}", "--no-first-run",
           "--no-default-browser-check", "--mute-audio", "--hide-scrollbars",
           f"--window-size={window[0]},{window[1]}", "--force-device-scale-factor=1",
           "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
           "--disable-backgrounding-occluded-windows", *GL_FLAGS[a.gl], url]
    t0 = time.monotonic()
    chrome = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    why = None
    try:
        while not state.done.wait(1.0):
            now = time.monotonic()
            if now - t0 > timeout:
                why = "timeout"
                break
            if now - (state.t_last or t0) > a.stall:
                why = "stall"
                break
    finally:
        chrome.terminate()
        try:
            chrome.wait(10)
        except subprocess.TimeoutExpired:
            chrome.kill()
        server.shutdown()
        server.server_close()
        shutil.rmtree(profile, ignore_errors=True)
    return time.monotonic() - t0, why


def window_for(a):
    """The window size whose viewport is exactly --w x --h."""
    st = State(None, None)
    launch(a, st, "__viewport", (a.w, a.h), 60)
    if not st.viewport:
        print("  viewport probe gave no answer; window = video size", file=sys.stderr, flush=True)
        return (a.w, a.h)
    win = (2 * a.w - st.viewport[0], 2 * a.h - st.viewport[1])
    if win != (a.w, a.h):
        print(f"  window {win[0]}x{win[1]} (Chrome keeps {win[0] - a.w}x{win[1] - a.h} px for itself)", flush=True)
    return win


def run_once(a, out: pathlib.Path, ext: str, start: int, window):
    """One Chrome run that writes frames start+1..end.
    Returns (state, wall seconds, None | "timeout" | "stall")."""
    if start == 0 and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    state = State(out, ext)
    q = f"record&w={a.w}&h={a.h}&fps={a.fps}&fmt={a.fmt}&start={start}"
    if a.timing:
        q += "&timing=" + urllib.parse.quote(a.timing)
    if a.query:
        q += "&" + a.query
    print(f"recording from frame {start + 1}: {a.w}x{a.h} @{a.fps} fps ({a.fmt}, gl={a.gl})", flush=True)
    print(f"  {a.page}?{q}", flush=True)
    wall, why = launch(a, state, f"{a.page}?{q}", window, a.timeout)
    return state, wall, why


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="index.html", help="page path relative to --serve-root")
    ap.add_argument("--serve-root", default=str(ROOT))
    ap.add_argument("--out", required=True, help="frame folder (emptied first)")
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--timing", default="", help="durations.json from tools/narrate.sh, relative to --serve-root")
    ap.add_argument("--fmt", choices=["png", "jpeg"], default="png")
    ap.add_argument("--gl", choices=sorted(GL_FLAGS), default="swiftshader")
    ap.add_argument("--query", default="", help="extra query string, e.g. 'scene=2'")
    ap.add_argument("--timeout", type=float, default=7200, help="seconds before giving up")
    ap.add_argument("--stall", type=float, default=90,
                    help="give up when no frame arrives for this many seconds")
    ap.add_argument("--retries", type=int, default=1, help="new Chrome start after a stall")
    ap.add_argument("--resume", action="store_true", help="keep frames on disk, continue after them")
    ap.add_argument("--audio")
    ap.add_argument("--mp4")
    a = ap.parse_args()

    out = pathlib.Path(a.out).resolve()
    ext = "jpg" if a.fmt == "jpeg" else "png"
    start = frames_on_disk(out, ext) if a.resume else 0
    window = window_for(a)
    for attempt in range(a.retries + 1):
        state, wall, why = run_once(a, out, ext, start, window)
        if why != "stall":
            break
        start = frames_on_disk(out, ext)
        print(f"  stall on attempt {attempt + 1}, {start} frames on disk, "
              f"restarting Chrome from frame {start + 1}", file=sys.stderr, flush=True)
    have = frames_on_disk(out, ext)
    if why:
        print(f"{why}: {have} frames on disk (rerun with --resume)", file=sys.stderr)
        return 1
    if state.error:
        print("page failed: " + " | ".join(state.error.splitlines()), file=sys.stderr)
        return 1
    if have != len(list(out.glob(f"*.{ext}"))):
        print(f"a gap in the frames: only 1..{have} are complete", file=sys.stderr)
        return 1
    print(f"  {have} frames in {out}", flush=True)
    if state.count < 2:
        print("stats unavailable: fewer than 2 frames in the last run", flush=True)
        return 0 if not a.mp4 else (encode(out, ext, a.fps, a.audio, pathlib.Path(a.mp4).resolve()) or 0)
    per = (state.t_last - state.t_first) / (state.count - 1)
    startup = wall - (state.t_last - state.t_first)
    stats = {"frames": state.count, "w": a.w, "h": a.h, "fps": a.fps, "fmt": a.fmt, "gl": a.gl,
             "wall_s": round(wall, 2), "startup_s": round(startup, 2),
             "s_per_frame": round(per, 4)}
    print("stats " + json.dumps(stats), flush=True)
    if a.mp4:
        encode(out, ext, a.fps, a.audio, pathlib.Path(a.mp4).resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
