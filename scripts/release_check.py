"""Check the tracked release surface without reading runtime or private files."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "api_token": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "aws_access": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "machine_path": re.compile(r"/(?:Users|home)/[^\s\"']+/"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
}


def main():
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    findings = []
    for name in filter(None, files):
        if name.startswith(("runtime/", ".venv/")) or name.endswith((".sqlite", ".sqlite-wal", ".log")) or name == ".env":
            findings.append({"file": name, "kind": "runtime_or_credential_file"})
            continue
        text = (ROOT / name).read_text(encoding="utf-8")
        for kind, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append({"file": name, "kind": kind})
        if name.startswith("examples/") and name.endswith((".json", ".html", ".xml")):
            for url in re.findall(r'https?://[^\s<>"\)]+', text):
                host = urlsplit(url).hostname or ""
                if not any(host == base or host.endswith("." + base) for base in ("example.com", "example.net", "example.org", "www.w3.org")):
                    findings.append({"file": name, "kind": "non_example_fixture_host"})
    print(json.dumps({"tracked_files": len(list(filter(None, files))), "findings": findings,
                      "license_present": (ROOT / "LICENSE").exists(),
                      "scope": "Pattern scan of tracked files only; not an exhaustive credential or ownership audit."}, indent=2))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
