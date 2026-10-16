"""Part III: MINIMAX for the opening, playing Black.

    python3 MiniMaxOpeningBlack.py <input board file> <output board file> <depth>

Same input and output as MiniMaxOpening.py, but the move is for Black.
This uses the color-swap method from the Morris handout:

    1. Swap every W and B on the input board, so Black's pieces look White.
    2. Run the White search from MiniMaxOpening.py on the swapped board.
    3. Swap the chosen board back and write it.

The printed estimate is the value of the swapped search, so a larger
number is better for Black.
"""

from morris.cli import read_arguments, report

from MiniMaxOpening import OpeningMinimax


def main():
    parser, board, output, depth = read_arguments()
    search = OpeningMinimax()
    swapped_choice, value = search.best_move(board.swapped(), depth)
    report(parser, output, swapped_choice.swapped(), search.positions_evaluated, value)


if __name__ == "__main__":
    main()
