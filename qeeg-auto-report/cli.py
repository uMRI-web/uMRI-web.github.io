from __future__ import annotations

import argparse
from pathlib import Path
from qeeg_core import analyze_m00, build_report

def main() -> None:
    p = argparse.ArgumentParser(description="qEEG .m00 -> Word report")
    p.add_argument("input", type=Path)
    p.add_argument("--name", default="")
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    out = args.output or args.input.with_name(args.input.stem + "_qEEG_report.docx")
    result = analyze_m00(args.input)
    build_report(result, out, input_name=args.name)
    print(out)

if __name__ == "__main__":
    main()
