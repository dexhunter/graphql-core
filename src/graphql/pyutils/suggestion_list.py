"""List with suggestions"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .natural_compare import natural_comparison_key

if TYPE_CHECKING:
    from collections.abc import Collection

__all__ = ["suggestion_list"]


def suggestion_list(input_: str, options: Collection[str]) -> list[str]:
    """Get list with suggestions for a given input.

    Given an invalid input string and list of valid options, returns a filtered list
    of valid options sorted based on their similarity with the input.
    """
    options_by_distance = {}
    lexical_distance = LexicalDistance(input_)

    threshold = int(len(input_) * 0.4) + 1
    for option in options:
        distance = lexical_distance.measure(option, threshold)
        if distance is not None:
            options_by_distance[option] = distance

    return sorted(
        options_by_distance,
        key=lambda option: (
            options_by_distance.get(option, 0),
            natural_comparison_key(option),
        ),
    )


class LexicalDistance:
    """Computes the lexical distance between strings A and B.

    The "distance" between two strings is given by counting the minimum number of edits
    needed to transform string A into string B. An edit can be an insertion, deletion,
    or substitution of a single character, or a swap of two adjacent characters.

    This distance can be useful for detecting typos in input or sorting.
    """

    _input: str
    _input_lower_case: str
    _rows: list[list[int]]

    def __init__(self, input_: str) -> None:
        self._input = input_
        self._input_lower_case = input_.lower()
        row_size = len(input_) + 1

        self._rows = [[0] * row_size, [0] * row_size, [0] * row_size]

    def measure(self, option: str, threshold: int) -> int | None:
        if self._input == option:
            return 0

        option_lower_case = option.lower()

        # Any case change counts as a single edit
        if self._input_lower_case == option_lower_case:
            return 1

        a, b = option_lower_case, self._input_lower_case
        a_len, b_len = len(a), len(b)
        if a_len < b_len:
            a, b = b, a
            a_len, b_len = b_len, a_len

        if a_len - b_len > threshold:
            return None

        rows = self._rows
        for j in range(b_len + 1):
            rows[0][j] = j

        # Common suffix and prefix characters need no edits
        while b_len and a[a_len - 1] == b[b_len - 1]:
            a_len -= 1
            b_len -= 1
        start = 0
        while start < b_len and a[start] == b[start]:
            start += 1
        a, b = a[start:a_len], b[start:b_len]
        a_len -= start
        b_len -= start

        # Each character of a missing from b needs at least one edit
        if len(set(a).difference(b)) > threshold:
            return None

        up_row, current_row, double_up_row = rows
        prev_a_char = None
        for i, a_char in enumerate(a, 1):
            left_cell = current_row[0] = i
            diagonal_cell = up_row[0]
            prev_b_char = None
            for j, b_char in enumerate(b, 1):
                up_cell = up_row[j]
                if a_char == b_char:
                    # Equal characters never cost more than the diagonal
                    current_cell = diagonal_cell
                else:
                    current_cell = min(up_cell, left_cell, diagonal_cell) + 1
                    if a_char == prev_b_char and prev_a_char == b_char:
                        # transposition
                        current_cell = min(current_cell, double_up_row[j - 2] + 1)

                current_row[j] = left_cell = current_cell
                diagonal_cell = up_cell
                prev_b_char = b_char

            # Early exit, since distance can't go smaller than smallest element
            # of the previous row.
            if i > threshold and min(current_row[: b_len + 1]) > threshold:
                return None

            prev_a_char = a_char
            double_up_row, up_row, current_row = up_row, current_row, double_up_row

        distance = up_row[b_len]
        return distance if distance <= threshold else None
