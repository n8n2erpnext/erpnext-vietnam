#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(cmd: list[str], *, cwd: Path | None = None) -> str:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if proc.returncode:
        raise SystemExit(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip()


def doctor(bench: Path, site: str) -> dict:
    raw = run(["bench", "--site", site, "execute", "erpnext_vietnam.diagnostics.release_doctor.run"], cwd=bench)
    data = json.loads(raw.splitlines()[-1])
    if data.get("status") != "PASS":
        raise SystemExit("ERPNext Vietnam release doctor did not PASS: " + raw)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="ERPNext Vietnam release smoke runner for an existing disposable/test site")
    parser.add_argument("--bench", required=True, type=Path)
    parser.add_argument("--site", required=True)
    parser.add_argument("--migrate", action="store_true", help="Explicitly run bench migrate before the second doctor pass")
    args = parser.parse_args()
    bench = args.bench.resolve()
    app = bench / "apps" / "erpnext_vietnam"
    site = bench / "sites" / args.site
    if not app.is_dir() or not site.is_dir():
        raise SystemExit("Bench app/site path is missing; provision the disposable site separately")

    run([str(bench / "env" / "bin" / "python"), "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=app)
    before = doctor(bench, args.site)
    if args.migrate:
        run(["bench", "--site", args.site, "migrate"], cwd=bench)
    after = doctor(bench, args.site)
    print(json.dumps({
        "site": args.site,
        "migrate_executed": bool(args.migrate),
        "before_status": before["status"],
        "after_status": after["status"],
        "versions": after.get("versions", {}),
        "result": "PASS",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
