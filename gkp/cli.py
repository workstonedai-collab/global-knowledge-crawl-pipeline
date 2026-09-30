from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .common import PipelineError
from .config import Config
from .pipeline import export_only, run


def main(argv=None):
    parser = argparse.ArgumentParser(description="Global Knowledge Pipeline (by GKN) | GKN全球信息采集程序")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "validate", "export"):
        command = subs.add_parser(name)
        command.add_argument("config", help="JSON config, or YAML with the yaml extra installed")
        if name != "validate":
            command.add_argument("--workspace", type=Path, help="State and output directory; default runtime/<dataset>")
        if name == "run":
            command.add_argument("--retry-failed", action="store_true", help="Reset exhausted or permanent failures for this contract")
            command.add_argument("--retry-review", action="store_true", help="Discard only current needs_review results and request them again")
            command.add_argument("--no-discovery", action="store_true", help="Process saved candidates without discovering new ones")
    args = parser.parse_args(argv)
    try:
        config = Config(args.config)
        if args.command == "validate":
            print(json.dumps({"valid": True, "dataset": config.dataset, "offline": config.offline, "template_signature": config.signature}))
            return 0
        workspace = (args.workspace or Path("runtime") / config.dataset).resolve()
        if args.command == "export":
            report = export_only(config, workspace)
        else:
            report = run(config, workspace, retry_failed=args.retry_failed, retry_review=args.retry_review, discover=not args.no_discovery)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.command == "export":
            return 0
        return {"paused": 3, "partial": 2}.get(report["status"], 0)
    except PipelineError as error:
        print("GKP error: " + error.code, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Persisted stages will be reused on the next run.", file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        # Do not leak config values, credentials, URLs or provider payloads in a traceback.
        print("GKP error: invalid_configuration_or_local_io", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
