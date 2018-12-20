#!/usr/bin/env python3
#
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""A pure-Python implementation of the patch command.

This is intended to only work on well-formed unified diffs, such as those produced by
`difflib.unified_diff`.  In the interest of making this implementation very small, it
does not handle:

* When the line offsets are incorrect ("Offset n lines")
* When edits have been made after the diff produced ("Fuzz")
* "No newline at end of file"
* File I/O
* Timestamps and permission bits
"""

import re
from typing import List

from .types import Hunk

POSITION_LINE_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffHunkException(Exception):
    """Exception raised on malformed hunks"""


def _parse_position_line(position_line: str) -> List[int]:
    """Given an `@@` line, return the four numbers within."""
    match = POSITION_LINE_RE.match(position_line)
    if not match:
        raise DiffHunkException(f"Position line {position_line!r} failed to parse")
    return [
        int(match.group(1)),
        int(match.group(2) or "1"),
        int(match.group(3)),
        int(match.group(4) or "1"),
    ]


def patch_hunks_single_file(
    patch_hunks: List[Hunk], target_lines: List[str]
) -> List[str]:
    """
    Applies the given hunks to the lines, and returns the new lines.

    A hunk is a sequence of lines starting with a position line (`@@`) and followed by
    an appropriate number of context, additions, or removals.  Notably, this does not
    include the file header (`---`, `+++`, or any extra text).

    Args:
        patch_hunks: The hunks to apply.  They must be in order, but you are free to
            omit ones and the positions will be fine.
        target_lines: The lines to apply them to.  Lines and hunk lines are all presumed
            to have the same kind of newlines, and every line end with one.

    Returns:
        The new list of lines on success, or raises an Exception.
    """

    work: List[str] = target_lines[:]
    # file_offset is the sum of delta counts (that is, added - removed) seen so far, and
    # on an unmodified diff will match (pos[2]-pos[0]) at start of hunk.
    file_offset = 0

    # This could be done as a streaming operation to avoid list modification overhead,
    # but this is simpler and far quicker than the cst operations that bowler also
    # performs.

    for hunk in patch_hunks:
        pos = _parse_position_line(hunk[0])
        # Don't trust pos[2:] because hunks may have been removed after calculating it
        cur_line = pos[0] + file_offset - 1
        for line in hunk[1:]:
            if line.startswith("-"):
                if line[1:] != work[cur_line]:
                    raise DiffHunkException(f"DELETE {line[1:]!r} {work[cur_line]!r}")
                del work[cur_line]
            elif line.startswith("+"):
                work.insert(cur_line, line[1:])
                cur_line += 1
            elif line.startswith(" "):
                if line[1:] != work[cur_line]:
                    raise DiffHunkException(f"EQUAL {line[1:]!r} {work[cur_line]!r}")
                cur_line += 1
            elif line.startswith("?"):
                pass  # human readable line
            else:
                raise DiffHunkException("Unknown line type {line}")
        file_offset += pos[3] - pos[1]

    return work


def split_hunks(diff_lines: List[str]) -> List[Hunk]:
    """
    Splits unified diff lines (after the file header) into hunks.

    Args:
        diff_lines: The lines of the diff, with newlines.

    Returns:
        A list of hunks of diff lines.
    """
    # TODO: This is very similar to code in bowler/tool inside processed_file, we should
    # unify.
    hunks: List[List[str]] = []
    hunk: List[str] = []
    for line in diff_lines:
        if line.startswith("@@"):
            if hunk:
                hunks.append(hunk)
                hunk = []
        hunk.append(line)
    if hunk:
        hunks.append(hunk)

    return hunks
