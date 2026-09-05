"""Expose the local backend so Hunar webhooks can reach it.

Starts a cloudflared quick tunnel, writes the public URL into backend/.env as
PUBLIC_BASE_URL, and holds it open until you stop it. Quick tunnels get a fresh
hostname every run, which is why this rewrites the file rather than asking you to.

    uv run python scripts/tunnel.py [--port 8001]

Restart the backend after the URL is written; Settings is read once at startup.
Ctrl-C stops the tunnel and clears PUBLIC_BASE_URL again, so a later local run
falls back to polling instead of pointing Hunar at a hostname that is gone.
"""

from __future__ import annotations

import argparse
import re
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def set_env(key: str, value: str) -> None:
    """Rewrite one key in .env, leaving every other line untouched."""
    if not ENV_PATH.exists():
        sys.exit(f"no {ENV_PATH}; copy .env.example first")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    out, seen = [], False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            seen = True
        else:
            out.append(line)
    if not seen:
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    exe = shutil.which("cloudflared")
    if not exe:
        sys.exit("cloudflared is not on PATH (winget install --id Cloudflare.cloudflared)")

    proc = subprocess.Popen(
        [exe, "tunnel", "--url", f"http://localhost:{args.port}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    found = threading.Event()

    def pump() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            match = URL_RE.search(line)
            if match and not found.is_set():
                url = match.group(0)
                set_env("PUBLIC_BASE_URL", url)
                found.set()
                print(f"\n  tunnel   {url}")
                print(f"  webhook  {url}/webhooks/hunar")
                print("  .env     PUBLIC_BASE_URL written")
                print("\n  Restart the backend to pick it up, then launch a call.")
                print("  Ctrl-C here stops the tunnel and clears the variable.\n", flush=True)

    threading.Thread(target=pump, daemon=True).start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        proc.send_signal(signal.SIGTERM)
        set_env("PUBLIC_BASE_URL", "")
        print("tunnel closed; PUBLIC_BASE_URL cleared, back to polling")


if __name__ == "__main__":
    main()
