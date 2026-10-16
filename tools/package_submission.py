"""Build the submission folder and ZIP, then run every program from a clean copy.

    python3 -m tools.package_submission

Output: dist/MorrisAI-submission/ and dist/MorrisAI-submission.zip, laid out as

    MiniMaxOpening.py ... MiniMaxGameImproved.py, TournamentAgent.py
    Examples.txt, MyStaticEstimation.txt
    morris/     board, move generator, estimators, command line, tournament search
    assets/     the empty board and the two handout positions
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
NAME = "MorrisAI-submission"
PROGRAMS = [
    "MiniMaxOpening.py", "MiniMaxGame.py", "ABOpening.py", "ABGame.py",
    "MiniMaxOpeningBlack.py", "MiniMaxGameBlack.py", "MiniMaxOpeningImproved.py",
    "MiniMaxGameImproved.py", "TournamentAgent.py",
]
TEXT = ["Examples.txt", "MyStaticEstimation.txt"]
MODULES = ["__init__.py", "board.py", "cli.py", "evaluation.py", "history_io.py", "tournament.py"]
ASSETS = ["empty_board.txt", "handout_position_1.txt", "handout_position_2.txt"]


def files():
    paths = [ROOT / name for name in PROGRAMS + TEXT]
    paths += [ROOT / "morris" / name for name in MODULES]
    paths += [ROOT / "assets" / name for name in ASSETS]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise SystemExit("Missing submission files: " + ", ".join(missing))
    return paths


def smoke_test(folder):
    """Every program must print the three lines and write a legal board, using only the folder."""
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "board2.txt"
        for program in PROGRAMS[:-1]:
            board = "handout_position_2" if "Opening" in program else "handout_position_1"
            run = subprocess.run([sys.executable, program, f"assets/{board}.txt", str(output), "2"],
                                 cwd=folder, capture_output=True, text=True, timeout=60)
            lines = run.stdout.splitlines()
            if (run.returncode or len(lines) != 3 or not lines[0].startswith("Board Position: ")
                    or output.read_text().strip() != lines[0].removeprefix("Board Position: ")):
                raise SystemExit(f"{program} failed in {folder}:\n{run.stdout}{run.stderr}")
        run = subprocess.run([sys.executable, "TournamentAgent.py", "assets/empty_board.txt",
                              str(output), "--side", "W", "--move-number", "1",
                              "--time-limit", "0.2"],
                             cwd=folder, capture_output=True, text=True, timeout=60)
        if run.returncode or "Board Position: " not in run.stdout:
            raise SystemExit(f"TournamentAgent.py failed in {folder}:\n{run.stdout}{run.stderr}")


def main():
    paths = files()
    folder = ROOT / "dist" / NAME
    if folder.exists():
        shutil.rmtree(folder)
    for path in paths:
        target = folder / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    archive = ROOT / "dist" / f"{NAME}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        for path in sorted(paths):
            zipped.write(path, path.relative_to(ROOT))
    with tempfile.TemporaryDirectory() as temp:
        with ZipFile(archive) as zipped:
            zipped.extractall(temp)
        smoke_test(Path(temp))
    print(f"Created {folder} and {archive} ({len(paths)} files); every program ran from the ZIP")


if __name__ == "__main__":
    main()
