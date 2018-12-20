#!/usr/bin/env python3
#
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import difflib

from ..patch import patch_hunks_single_file, split_hunks
from .lib import BowlerTestCase

POSSIBLE_LINE_COUNT = 12
POSSIBLE_LINES = [chr(ord("a") + i) + "\n" for i in range(POSSIBLE_LINE_COUNT)]


class PatcherTest(BowlerTestCase):
    def test_only_context(self):
        hunk = "@@ -1,2 +1,2 @@\n a\n b\n".splitlines(True)
        input = "a\nb\n".splitlines(True)
        output = patch_hunks_single_file([hunk], input)
        self.assertEqual(input, output)

    def test_replace_line(self):
        hunk = "@@ -1,3 +1,3 @@\n a\n-b\n+x\n c\n".splitlines(True)
        input = "a\nb\nc\n".splitlines(True)
        expected = "a\nx\nc\n".splitlines(True)
        output = patch_hunks_single_file([hunk], input)
        self.assertEqual(expected, output)

    def test_difflib_exhaustive(self):
        # Tests all possible combinations of lines before/after to ensure that we can
        # handle whatever difflib throws at us.
        left_file = ["a\n", "b\n", "g\n"]
        for i in range(2 ** 12):
            right_file = []
            for j in range(POSSIBLE_LINE_COUNT):
                if i & (2 << j):
                    right_file.append(POSSIBLE_LINES[j])
            print(left_file)
            print(right_file)
            diff_lines = list(difflib.unified_diff(left_file, right_file))
            del diff_lines[:2]
            print(diff_lines)
            print()
            output = patch_hunks_single_file(split_hunks(diff_lines), left_file)
            self.assertEqual(right_file, output)
