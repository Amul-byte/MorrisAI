"""Fixed-depth cold-cache comparison of tournament transposition caching."""

import json
from pathlib import Path
import platform

from morris.board import Board
from morris.evaluation import improved
from morris.tournament import TournamentSearch


def main():
    rows = []
    for label, board, placements in (
        ("empty-opening", Board(0, 0), 18),
        ("handout-game", Board.parse("xxxxxBxWWWWWBBBBxxxxxxx"), 0),
    ):
        scores = []
        for enabled in (False, True):
            improved.cache_clear()
            engine = TournamentSearch(use_table=enabled)
            result = engine.choose(board, "W", placements, time_limit=30, max_depth=6)
            if result.depth != 6:
                raise RuntimeError("Benchmark did not complete the required depth")
            scores.append(result.score)
            rows.append({"position": label, "input": str(board), "transpositions": enabled,
                         "depth": result.depth, "nodes": result.nodes,
                         "evaluations": result.evaluations, "table_hits": engine.hits,
                         "seconds": round(result.elapsed, 4), "score": result.score,
                         "selected": str(result.board)})
        assert scores[0] == scores[1]
    report = {"python": platform.python_version(), "platform": platform.platform(), "runs": rows}
    output = Path(__file__).resolve().parents[1] / "benchmarks" / "search-performance.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
