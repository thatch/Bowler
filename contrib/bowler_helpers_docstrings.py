#!/usr/bin/env python3

import re
import unittest

from bowler.types import TOKEN, Leaf


QUOTE_RE = re.compile(r"\A([rfub]*)('''|'|\"\"\"|\")(.*)\2\Z", re.I | re.DOTALL)


class ExplodeStringtests(unittest.TestCase):
    def test_explode_string(self):
        self.assertEqual(("", "'", "foo"), explode_string("'foo'"))
        self.assertEqual(("Rb", "'", "foo"), explode_string("Rb'foo'"))


def explode_string(value):
    # returns: prefix, quote, inner data
    try:
        return QUOTE_RE.match(value).groups()
    except AttributeError:
        raise ValueError(value)


LATEX_MATH = re.compile(r"\\[a-z]{3,}")
BOX_RUN = re.compile(r"[|=-]{5,}")
LINE_CHAR = re.compile(r"\s([/|\\]|->)\s")
# Need a threshold for "most" of a line, for a min number of lines


def maybe_ascii_art(leaf):
    """
    Returns whether a given string has a reasonable likelihood of having ASCII art.

    This is intended to flag long strings that contain a small amount of ASCII art as well.
    """
    # Just runs of dashes aren't enough; this needs to find at least 4 lines of
    # mostly "unnecessary" formatting.
    # Boxes
    if len(BOX_RUN.findall(leaf.value)) >= 4 and "|" in leaf.value:
        return True

    # Just lines (this will find tables as well as trees)
    if len(LINE_CHAR.findall(leaf.value)) > 4:
        return True

    return False


def maybe_latex(leaf):
    """
    Returns whether a given string might contain LaTeX math.
    """
    return bool(LATEX_MATH.search(leaf.value))


class DetectorTests(unittest.TestCase):
    def test_ascii_art(self):
        t = Leaf(TOKEN.STRING, '""" foo """')
        self.assertFalse(maybe_ascii_art(t))

        t = Leaf(
            TOKEN.STRING,
            '''"""
        ---------    ---------
        |  box  | -> | arrow |
        ---------    ---------
        """''',
        )
        self.assertTrue(maybe_ascii_art(t))

        t = Leaf(
            TOKEN.STRING,
            r'''"""
            a
          / | \
         /  |  \
        b   c   d
        """''',
        )
        self.assertTrue(maybe_ascii_art(t))

        t = Leaf(TOKEN.STRING, '"a -> b -> c -> d -> e -> f"')
        self.assertTrue(maybe_ascii_art(t))

        t = Leaf(
            TOKEN.STRING,
            r'''"""
                 /----/
                /     ---
               /     ___/
              /     /
             /_____/

        """''',
        )
        self.assertTrue(maybe_ascii_art(t))

    def test_latex(self):
        t = Leaf(TOKEN.STRING, '""" foo """')
        self.assertFalse(maybe_latex(t))

        t = Leaf(TOKEN.STRING, r'""" \s \sa """')
        self.assertFalse(maybe_latex(t))

        t = Leaf(TOKEN.STRING, r'""" \sum_{i=1} """')
        self.assertTrue(maybe_latex(t))

        t = Leaf(
            TOKEN.STRING,
            r'''"""\sum_i(i+1)"""''',
        )
        self.assertTrue(maybe_latex(t))
