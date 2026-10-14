"""Board topology and legal moves, transcribed from the supplied handout.

Two disjoint 23-bit integers hold White and Black pieces. Successors are
deterministic: source index, neighbor order below, then captured-piece index.
"""

from dataclasses import dataclass
from typing import Iterator

SIZE = 23
FULL = (1 << SIZE) - 1
COORDINATES = (
    "a0", "d0", "g0", "b1", "d1", "f1", "c2", "e2", "a3", "b3",
    "c3", "e3", "f3", "g3", "c4", "d4", "e4", "b5", "d5", "f5",
    "a6", "d6", "g6",
)
NEIGHBORS = (
    (1, 3, 8), (0, 4, 2), (1, 5, 13), (0, 4, 6, 9), (1, 3, 5),
    (2, 4, 7, 12), (3, 7, 10), (5, 6, 11), (0, 9, 20),
    (3, 8, 10, 17), (6, 9, 14), (7, 12, 16), (5, 11, 13, 19),
    (2, 12, 22), (10, 15, 17), (14, 16, 18), (11, 15, 19),
    (9, 14, 18, 20), (15, 17, 19, 21), (12, 16, 18, 22),
    (8, 17, 21), (18, 20, 22), (13, 19, 21),
)
MILLS = (
    (0, 1, 2), (3, 4, 5), (8, 9, 10), (11, 12, 13),
    (14, 15, 16), (17, 18, 19), (20, 21, 22),
    (0, 8, 20), (3, 9, 17), (6, 10, 14), (7, 11, 16),
    (5, 12, 19), (2, 13, 22), (15, 18, 21),
    (0, 3, 6), (2, 5, 7), (14, 17, 20), (16, 19, 22),
)
NEIGHBOR_MASKS = tuple(sum(1 << j for j in row) for row in NEIGHBORS)
MILL_MASKS = tuple(sum(1 << j for j in row) for row in MILLS)
MILLS_AT = tuple(tuple(mask for mask in MILL_MASKS if mask & (1 << i))
                 for i in range(SIZE))


def indices(mask: int) -> Iterator[int]:
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


@dataclass(frozen=True, slots=True)
class Board:
    white: int
    black: int

    def __post_init__(self) -> None:
        if (self.white < 0 or self.black < 0 or
                (self.white | self.black) & ~FULL or self.white & self.black):
            raise ValueError("Board masks must be disjoint, nonnegative 23-bit values")

    @classmethod
    def parse(cls, text: str) -> "Board":
        if not isinstance(text, str):
            raise ValueError("Board position must be a string")
        text = text.strip()
        if len(text) != SIZE or any(c not in "WBx" for c in text):
            raise ValueError("A board must contain exactly 23 characters from W, B, x")
        return cls(sum(1 << i for i, c in enumerate(text) if c == "W"),
                   sum(1 << i for i, c in enumerate(text) if c == "B"))

    def __str__(self) -> str:
        return "".join("W" if self.white & (1 << i) else
                       "B" if self.black & (1 << i) else "x" for i in range(SIZE))

    def swapped(self) -> "Board":
        return Board(self.black, self.white)

    def pieces(self, side: str) -> int:
        if side not in ("W", "B"):
            raise ValueError("Side must be W or B")
        return self.white if side == "W" else self.black


def opponent(side: str) -> str:
    if side not in ("W", "B"):
        raise ValueError("Side must be W or B")
    return "B" if side == "W" else "W"


def closes_mill(pieces: int, location: int) -> bool:
    return any(pieces & mill == mill for mill in MILLS_AT[location])


def protected_pieces(pieces: int) -> int:
    protected = 0
    for mill in MILL_MASKS:
        if pieces & mill == mill:
            protected |= mill
    return protected


def _captured_positions(own: int, other: int, destination: int):
    if closes_mill(own, destination):
        removable = other & ~protected_pieces(other)
        if removable:
            for i in indices(removable):
                yield own, other ^ (1 << i)
            return
    # PDF p.4: when all opponents are in mills, keep the board unchanged.
    yield own, other


def generate_moves(board: Board, side: str, opening: bool) -> list[Board]:
    """Handout move generators; terminal adjudication belongs to search.

    Opening deliberately has no nine-piece limit: the assignment CLI supplies
    a phase, not placement history. Tournament search supplies that history.
    """
    own = board.pieces(side)
    other = board.pieces(opponent(side))
    empty = FULL ^ (own | other)
    moves = []
    if opening:
        candidates = ((own | (1 << dst), dst) for dst in indices(empty))
    elif own.bit_count() == 3:
        candidates = ((own ^ (1 << src) | (1 << dst), dst)
                      for src in indices(own) for dst in indices(empty))
    else:
        candidates = ((own ^ (1 << src) | (1 << dst), dst)
                      for src in indices(own) for dst in NEIGHBORS[src]
                      if empty & (1 << dst))
    for moved, dst in candidates:
        for left, right in _captured_positions(moved, other, dst):
            moves.append(Board(left, right) if side == "W" else Board(right, left))
    return moves


def mobility(pieces: int, empty: int) -> int:
    if pieces.bit_count() == 3:
        return 3 * empty.bit_count()
    return sum((NEIGHBOR_MASKS[i] & empty).bit_count() for i in indices(pieces))


def game_winner(board: Board, side_to_move: str) -> str | None:
    """Call only AFTER opening. No premature losses during placement."""
    own, other = board.pieces(side_to_move), board.pieces(opponent(side_to_move))
    if own.bit_count() <= 2:
        return opponent(side_to_move)
    if other.bit_count() <= 2:
        return side_to_move
    if not mobility(own, FULL ^ (own | other)):
        return opponent(side_to_move)
    return None
