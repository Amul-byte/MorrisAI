"""Time-bounded iterative-deepening alpha-beta with legal fallback moves.

The search remains full-width MINIMAX with alpha-beta pruning. Ordering and
transposition bounds never discard a branch that could change its value.
Repetition-sensitive cached values include history: identical boards can have
different values when one is approaching a third occurrence.
"""

from collections import Counter
from dataclasses import dataclass
import math
from time import perf_counter
from typing import Callable

from .board import (Board, MILLS_AT, closes_mill, game_winner,
                    generate_moves, opponent)
from .evaluation import WIN, baseline, improved

INF = 10**12
PositionKey = tuple[int, int, str]


@dataclass(slots=True)
class SearchResult:
    board: Board
    score: int
    evaluations: int
    nodes: int
    depth: int
    elapsed: float = 0.0
    timed_out: bool = False


def position_key(board: Board, side: str) -> PositionKey:
    return board.white, board.black, side


@dataclass(slots=True)
class Entry:
    depth: int
    score: int
    flag: str
    move: Board


class SearchTimeout(Exception):
    pass


class TournamentSearch:
    def __init__(self, *, clock: Callable[[], float] = perf_counter,
                 enhanced: bool = True, table_limit: int = 8000,
                 use_table: bool = True):
        self.clock = clock
        self.evaluate = improved if enhanced else baseline
        self.table_limit = table_limit
        self.use_table = use_table
        self.table = {}
        self.preferred = {}
        self.killers = {}
        self.history_scores = Counter()
        self.counts = Counter()
        self.nodes = self.evaluations = self.hits = 0
        self.deadline = float("inf")

    def _check_time(self):
        if self.clock() >= self.deadline:
            raise SearchTimeout

    def _static(self, board: Board, opening: bool, side: str) -> int:
        self.evaluations += 1
        return self.evaluate(board, opening) * (1 if side == "W" else -1)

    @staticmethod
    def _signature(board: Board, child: Board, side: str):
        return (board.pieces(side) ^ child.pieces(side),
                board.pieces(opponent(side)) ^ child.pieces(opponent(side)))

    def _ordered(self, board, moves, side, depth, key):
        preferred = self.preferred.get(key)
        killers = self.killers.get(depth, ())
        other_count = board.pieces(opponent(side)).bit_count()

        def priority(child):
            signature = self._signature(board, child, side)
            if child == preferred:
                return 10**9
            captures = other_count - child.pieces(opponent(side)).bit_count()
            own = child.pieces(side)
            added = own & ~board.pieces(side)
            destination = added.bit_length() - 1
            return (captures * 10**6 + (signature in killers) * 100000
                    + min(self.history_scores[side, signature], 50000)
                    + closes_mill(own, destination) * 1000
                    + len(MILLS_AT[destination]) * 10)

        # Python's stable sort preserves canonical order on equal priorities.
        return sorted(moves, key=priority, reverse=True)

    def _visit(self, board: Board, side: str, placements: int, depth: int,
               alpha: int, beta: int) -> tuple[int, Board]:
        self._check_time()
        self.nodes += 1
        if placements == 0:
            winner = game_winner(board, side)
            if winner:
                return (WIN if winner == side else -WIN), board
        if self.counts[position_key(board, side)] >= 3:
            return 0, board
        if depth == 0:
            return self._static(board, placements > 0, side), board

        key = (board, side, placements)
        # A board with the same side to move cannot recur in fewer than four
        # plies: each side must move out and back. If no position has occurred
        # twice, a third occurrence is impossible within four further plies.
        # Such shallow subtrees can safely share history-independent bounds.
        # Otherwise retain the exact history, never a probabilistic hash.
        context = None
        if self.use_table and (depth > 4 or any(c > 1 for c in self.counts.values())):
            context = frozenset(self.counts.items())
        cache_key = (key, context) if self.use_table else None
        original_alpha, original_beta = alpha, beta
        entry = self.table.get(cache_key)
        if entry is not None and entry.depth == depth:
            self.hits += 1
            if entry.flag == "exact":
                return entry.score, entry.move
            if entry.flag == "lower":
                alpha = max(alpha, entry.score)
            else:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score, entry.move

        moves = generate_moves(board, side, placements > 0)
        if not moves:
            return -WIN, board
        best, chosen = -INF, moves[0]
        next_side = opponent(side)
        for child in self._ordered(board, moves, side, depth, key):
            child_key = position_key(child, next_side)
            self.counts[child_key] += 1
            try:
                score, _ = self._visit(child, next_side, max(0, placements - 1),
                                       depth - 1, -beta, -alpha)
                score = -score
            finally:
                self.counts[child_key] -= 1
                if not self.counts[child_key]:
                    del self.counts[child_key]
            if score > best:
                best, chosen = score, child
            alpha = max(alpha, best)
            if alpha >= beta:
                signature = self._signature(board, child, side)
                self.killers[depth] = (signature,) + tuple(
                    k for k in self.killers.get(depth, ()) if k != signature)[:1]
                self.history_scores[side, signature] += depth * depth
                break
        if len(self.preferred) >= self.table_limit * 4:
            self.preferred.clear()
        self.preferred[key] = chosen
        if self.use_table:
            if len(self.table) >= self.table_limit:
                self.table.clear()
            flag = "upper" if best <= original_alpha else (
                "lower" if best >= original_beta else "exact")
            self.table[cache_key] = Entry(depth, best, flag, chosen)
        return best, chosen

    def choose(self, board: Board, side: str, placements: int, *,
               time_limit: float = 180.0, max_depth: int = 64,
               history: list[tuple[Board, str]] | None = None,
               on_complete: Callable[[SearchResult], None] | None = None) -> SearchResult:
        """History contains states BEFORE this root (not the root itself)."""
        if (not 0 <= placements <= 18 or not 1 <= max_depth <= 100
                or not math.isfinite(time_limit) or time_limit <= 0):
            raise ValueError("Invalid placements, depth, or time budget")
        opponent(side)
        start = self.clock()
        self.deadline = start + time_limit
        self.table.clear()
        self.preferred.clear()
        self.killers.clear()
        self.history_scores.clear()
        self.nodes = self.evaluations = self.hits = 0
        self.counts = Counter(position_key(b, s) for b, s in (history or []))
        self.counts[position_key(board, side)] += 1
        if placements == 0 and game_winner(board, side):
            raise ValueError("The game has already ended; no move should be posted")
        if self.counts[position_key(board, side)] >= 3:
            raise ValueError("This is the third occurrence: the game is a draw")
        moves = generate_moves(board, side, placements > 0)
        if not moves:
            raise ValueError("No legal move is available")
        result = SearchResult(moves[0], 0, 0, 0, 0)
        if on_complete:
            on_complete(result)  # durable legal fallback, even before depth 1
        for depth in range(1, max_depth + 1):
            try:
                score, chosen = self._visit(board, side, placements, depth, -INF, INF)
                self._check_time()
            except (SearchTimeout, KeyboardInterrupt):
                result.timed_out = True
                break
            result = SearchResult(chosen, score, self.evaluations, self.nodes,
                                  depth, self.clock() - start)
            if on_complete:
                on_complete(result)
            if abs(score) == WIN:
                break
        result.elapsed = self.clock() - start
        result.nodes = self.nodes
        result.evaluations = self.evaluations
        return result
