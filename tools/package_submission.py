"""Package required entry points WITH the shared modules they import."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    required = [
        "MiniMaxOpening.py", "MiniMaxGame.py", "ABOpening.py", "ABGame.py",
        "MiniMaxOpeningBlack.py", "MiniMaxGameBlack.py", "MiniMaxOpeningImproved.py",
        "MiniMaxGameImproved.py", "TournamentAgent.py", "Examples.txt",
        "MyStaticEstimation.txt", "README.md",
    ]
    paths = [ROOT / name for name in required]
    for pattern in ("morris/*.py", "tests/*.py", "tests/fixtures/*.txt", "tools/*.py",
                    "benchmarks/*.json", "benchmarks/RESULTS.md"):
        paths.extend(ROOT.glob(pattern))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise SystemExit("Missing submission files: " + ", ".join(missing))
    output = ROOT / "dist" / "MorrisAI-submission.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path, path.relative_to(ROOT))
    print(f"Created {output} ({len(set(paths))} files)")


if __name__ == "__main__":
    main()
