"""python -m screen FILE...: screen JATS (.xml) or text files, printing what is flagged; exits 1 if anything is.
python -m screen --preflight: check the screen against its planted and clean fixtures; exits 1 on any mistake.
python -m screen --pin: the classifier's newest upstream revision and file hashes, to update injection.py by hand."""

import argparse
from pathlib import Path

from screen import preflight, screen_jats, screen_text
from screen.injection import ProtectAI, pin


def main(argv: list[str] | None = None, classify=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m screen", description="Flag hidden text before a model reads a paper.")
    parser.add_argument("files", nargs="*", type=Path, help="JATS .xml or plain-text files")
    parser.add_argument("--preflight", action="store_true", help="check the screen against its own fixtures")
    parser.add_argument("--pin", action="store_true", help="print the classifier's newest revision and file hashes")
    args = parser.parse_args(argv)
    if args.pin:
        print(pin())
        return 0
    if not args.files and not args.preflight:
        parser.error("give files to screen, or --preflight")
    classify = classify or ProtectAI()
    flagged = 0
    if args.preflight:
        problems = preflight(classify)
        print("\n".join(problems) if problems else "preflight: every planted fixture flagged, no clean one")
        flagged += len(problems)
    for path in args.files:
        data = path.read_bytes()
        result = screen_jats(data, classify) if path.suffix == ".xml" else screen_text(data.decode("utf-8"), classify)
        print(f"{path}: {'FLAGGED' if result.flagged else 'clean'}")
        for finding in result.findings:
            print(f"  {finding.layer}: {finding.detail}: {finding.excerpt}")
        flagged += result.flagged
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
