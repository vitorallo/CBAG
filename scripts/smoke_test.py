#!/usr/bin/env python3
"""CBAG bootstrap smoke test — checks every service health endpoint over HTTP.

Run on the GB10 (localhost) or from the Mac (--host <GB10-IP>) to prove the
stack is up, services bind 0.0.0.0, and the GPU is visible inside the model
service containers.
"""
import argparse
import json
import sys
import urllib.request


def get(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost", help="GB10 host/IP (default localhost)")
    ap.add_argument("--job", action="store_true", help="also run a text-only pipeline job end to end")
    args = ap.parse_args()
    h = args.host

    checks = [
        ("backend", f"http://{h}:8000/health"),
        ("backend/services", f"http://{h}:8000/health/services"),
        ("llm (host ollama)", f"http://{h}:11434/api/tags"),
        ("tts", f"http://{h}:8100/health"),
        ("video", f"http://{h}:8200/health"),
    ]

    ok = True
    for name, url in checks:
        try:
            code, body = get(url)
            tag = "OK" if code == 200 else f"HTTP {code}"
            print(f"[{tag}] {name:18} {url}")
            if name in ("tts", "video"):
                print(f"         gpu: {body.get('gpu')}")
            if name == "backend/services":
                print(f"         {body.get('services')}")
            if code != 200:
                ok = False
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name:18} {url} -> {exc}")
            ok = False

    if args.job:
        import json as _json
        import time as _time
        import urllib.parse as _parse
        try:
            req = urllib.request.Request(
                f"http://{h}:8000/api/jobs",
                data=_parse.urlencode({"topic": "smoke test", "length": "short", "text_only": "true"}).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            jid = _json.loads(urllib.request.urlopen(req, timeout=30).read())["job_id"]
            status = "running"
            for _ in range(60):
                _, body = get(f"http://{h}:8000/api/jobs/{jid}")
                status = body["status"]
                if status in ("completed", "failed"):
                    break
                _time.sleep(1)
            tag = "OK" if status == "completed" else f"status={status}"
            print(f"[{tag}] {'job (text-only)':18} {jid}")
            if status != "completed":
                ok = False
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {'job (text-only)':18} -> {exc}")
            ok = False

    print()
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
