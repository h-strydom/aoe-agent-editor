"""python -m aoe2ed.bank list|show|set|delete|export|import

Reads the most recently used profile's Player.nfp unless --file is given. Commands that write
back up the file first and refuse while the game is running.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import Bank, BankFormatError, GameRunningError, find_profiles, load


def _write(bank: Bank, args) -> None:
    if not bank.changed and not args.out:
        print("no changes", file=sys.stderr)
        return
    if args.dry_run:
        print("dry run: nothing written", file=sys.stderr)
        return
    backup = bank.save(args.out or bank.path, check_game=not args.no_game_check)
    if backup:
        print(f"backup: {backup}", file=sys.stderr)
    print(f"wrote {args.out or bank.path}", file=sys.stderr)


def _int(text: str) -> int:
    return int(text, 0)


def _import_doc(doc) -> dict[str, dict[str, int]]:
    """Accepts export output: {"campaign": c, "keys": {...}} or {"campaigns": {c: {...}}}."""
    if isinstance(doc, dict) and "campaigns" in doc:
        return doc["campaigns"]
    if isinstance(doc, dict) and "campaign" in doc and "keys" in doc:
        return {doc["campaign"]: doc["keys"]}
    raise ValueError('expected {"campaign": ..., "keys": {...}} or {"campaigns": {...}}')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m aoe2ed.bank", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", "-f", type=Path, help="Player.nfp to read (default: latest profile)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("profiles", help="list discovered Player.nfp files")
    p = sub.add_parser("list", help="campaigns in the bank with key counts")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("show", help="keys and values of one campaign")
    p.add_argument("campaign")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("export", help="dump one campaign (or all) as JSON")
    p.add_argument("campaign", nargs="?")
    p.add_argument("--json", action="store_true", help="JSON output (the only format; accepted for clarity)")

    def writer(name: str, help: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help)
        p.add_argument("--out", "-o", type=Path, help="write here instead of back to --file")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--no-game-check", action="store_true",
                       help="skip the AoE2DE_s.exe running check (only for files the game doesn't use)")
        return p

    p = writer("set", "set a key (creates it if missing)")
    p.add_argument("campaign")
    p.add_argument("key")
    p.add_argument("value", type=_int)
    p = writer("delete", "delete a key, or a whole campaign with --all")
    p.add_argument("campaign")
    p.add_argument("key", nargs="?")
    p.add_argument("--all", action="store_true", help="delete every key of the campaign")
    p = writer("import", "apply a JSON file produced by export ('-' for stdin)")
    p.add_argument("json_file")
    p.add_argument("--replace", action="store_true",
                   help="also delete keys of the imported campaigns that the file doesn't list")

    args = ap.parse_args(argv)
    # Official campaign keys aren't all ASCII (3kcam2 "LüBu..."); keep JSON output importable.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.cmd == "profiles":
        for path in find_profiles():
            print(path)
        return 0

    try:
        bank = load(args.file)
    except (FileNotFoundError, BankFormatError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    try:
        if args.cmd == "list":
            counts = {c: len(bank.keys(c)) for c in bank.campaigns()}
            if args.json:
                print(json.dumps({"file": str(bank.path), "campaigns": counts}, indent=2))
            else:
                print(f"# {bank.path}")
                for c, n in counts.items():
                    print(f"{c}\t{n}")
        elif args.cmd == "show":
            keys = bank.keys(args.campaign)
            if not keys:
                print(f"no keys for campaign {args.campaign!r}", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(keys, indent=2, ensure_ascii=False))
            else:
                for k, v in keys.items():
                    print(f"{k}\t{v}")
        elif args.cmd == "export":
            if args.campaign:
                doc = {"campaign": args.campaign, "keys": bank.keys(args.campaign)}
            else:
                doc = {"campaigns": {c: bank.keys(c) for c in bank.campaigns()}}
            print(json.dumps(doc, indent=2, ensure_ascii=False))
        elif args.cmd == "set":
            bank.set(args.campaign, args.key, args.value)
            _write(bank, args)
        elif args.cmd == "delete":
            if args.all == bool(args.key):
                print("error: give a key or --all (not both)", file=sys.stderr)
                return 2
            if args.all:
                print(f"deleted {bank.delete_campaign(args.campaign)} keys", file=sys.stderr)
            elif not bank.delete(args.campaign, args.key):
                print(f"no key {args.campaign}:{args.key}", file=sys.stderr)
                return 1
            _write(bank, args)
        elif args.cmd == "import":
            text = sys.stdin.read() if args.json_file == "-" else Path(args.json_file).read_text("utf-8")
            for campaign, keys in _import_doc(json.loads(text)).items():
                if args.replace:
                    for stale in set(bank.keys(campaign)) - set(keys):
                        bank.delete(campaign, stale)
                for k, v in keys.items():
                    bank.set(campaign, k, v)
            _write(bank, args)
    except (ValueError, TypeError, GameRunningError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
