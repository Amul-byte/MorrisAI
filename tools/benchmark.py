"""Paired local practice games; never reports official tournament results."""

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import random
from time import perf_counter

from morris.board import Board, game_winner, generate_moves, opponent
from morris.evaluation import improved
from morris.tournament import TournamentSearch, position_key


def practice(seed, enhanced_side, seconds, max_depth, max_plies):
    rng = random.Random(seed)
    board, side = Board(0, 0), "W"
    history = []
    # Same six legal opening moves for each color-swapped pair of agents.
    for _ in range(6):
        history.append((board, side))
        board = rng.choice(generate_moves(board, side, True))
        side = opponent(side)
    initial = str(board)
    counts = Counter(position_key(b, s) for b, s in history)
    engines = {s: TournamentSearch(enhanced=s == enhanced_side) for s in ("W", "B")}
    nodes = 0
    depths = []
    max_elapsed = 0.0
    winner = None
    reason = "ply_cap"
    for ply in range(6, max_plies):
        counts[position_key(board, side)] += 1
        winner = game_winner(board, side) if ply >= 18 else None
        if winner:
            reason = "win"
            break
        if counts[position_key(board, side)] >= 3:
            reason = "threefold"
            break
        result = engines[side].choose(board, side, max(0, 18 - ply),
                                      time_limit=seconds, max_depth=max_depth, history=history)
        if result.board not in generate_moves(board, side, ply < 18):
            raise AssertionError("Practice agent returned an illegal move")
        nodes += result.nodes
        depths.append(result.depth)
        max_elapsed = max(max_elapsed, result.elapsed)
        history.append((board, side))
        board, side = result.board, opponent(side)
    else:
        # Adjudicate the final move before calling a game unfinished.
        winner = game_winner(board, side) if max_plies >= 18 else None
        if winner:
            reason = "win"
        elif counts[position_key(board, side)] >= 2:
            reason = "threefold"
    outcome = "unfinished" if reason == "ply_cap" else (
        "draw" if winner is None else "win" if winner == enhanced_side else "loss")
    return {"seed": seed, "improved_side": enhanced_side, "initial": initial,
            "outcome": outcome, "reason": reason, "plies": len(history),
            "mean_depth": round(sum(depths) / len(depths), 2),
            "nodes": nodes, "max_search_seconds": round(max_elapsed, 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=0.03)
    parser.add_argument("--depth", type=int, default=64)
    parser.add_argument("--max-plies", type=int, default=140)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/latest.json"))
    args = parser.parse_args()
    if args.pairs < 1 or args.seconds <= 0 or args.depth < 1 or args.max_plies <= 6:
        parser.error("pairs, seconds, depth must be positive and max-plies must exceed 6")
    games = []
    start = perf_counter()
    for seed in range(args.pairs):
        for side in ("W", "B"):
            improved.cache_clear()
            result = practice(4346 + seed, side, args.seconds, args.depth, args.max_plies)
            games.append(result)
            print(json.dumps(result), flush=True)
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "seconds_per_move": args.seconds, "maximum_depth": args.depth,
              "max_plies": args.max_plies, "elapsed": round(perf_counter() - start, 2),
              "opponent": "same alpha-beta engine with handout baseline evaluation",
              "outcomes_for_improved": dict(Counter(g["outcome"] for g in games)),
              "games": games}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["outcomes_for_improved"]), flush=True)


if __name__ == "__main__":
    main()
