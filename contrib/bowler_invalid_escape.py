#!/usr/bin/env python3
"""Context: https://bugs.python.org/issue27364"""

import enum
import re
import sys

from bowler import Query
from bowler.tests.lib import BowlerTestCase
from bowler.types import TOKEN, Leaf, Node
from fissix.fixer_util import find_root

from bowler_helpers_docstrings import explode_string, maybe_ascii_art, maybe_latex


CAREFUL = True


class InvalidUnicodeTests(BowlerTestCase):
    def test_all(self):
        self.run_bowler_modifiers(
            [
                (r'u"\i"', r'u"\\i"'),
                (r'u"\i\0"', r'u"\\i\0"'),
                (r'b"\i\0"', r'b"\\i\0"'),
                # Left alone out of safety, but should be done in a later version
                (r'"\i\0\u1234"', r'"\i\0\u1234"'),  # left alone
                (r'f"{x}\i"', r'f"{x}\i"'),
                (r'f"{x}\i\0"', r'f"{x}\i\0"'),
                (r'br"\d+"', r'br"\d+"'),
                (r'"\u1234\."', r'"\u1234\."'),
                # (r'"\i"', r'r"\i"'),
                # With unicode_literals, now we're talking
                (
                    'from __future__ import unicode_literals\n"\\u1234\\."',
                    'from __future__ import unicode_literals\n"\\u1234\\\\."',
                ),
                (
                    'from __future__ import unicode_literals\nb"\\u1234\\."',
                    'from __future__ import unicode_literals\nbr"\\u1234\\."',
                ),
                (
                    'from __future__ import unicode_literals\n"{}/\d+"',
                    'from __future__ import unicode_literals\nr"{}/\d+"',
                ),
            ],
            SELECTOR,
            modifier,
        )


SELECTOR = """
STRING
"""

# Reference
# https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals
BYTES_ESCAPES = {
    "\n",
    "\r",  # Seen in the wild
    "\\",
    "'",
    '"',
    "a",
    "b",
    "f",
    "n",
    "r",
    "t",
    "v",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "x",
}
STRING_ESCAPES = {"N", "u", "U"}

ESCAPE_RE = re.compile(r"\\(.)", re.DOTALL)


class StringType(enum.Enum):
    UNKNOWN = 0
    UNICODE = 1
    BYTES = 2


def infer_string_type(str_prefix: str, node: Node) -> StringType:
    """Returns the type of the string literal."""
    if "u" in str_prefix.lower():
        return StringType.UNICODE
    elif "b" in str_prefix.lower():
        return StringType.BYTES
    else:
        # Only one reliable in-file guess we can make here...
        root = find_root(node)
        if "unicode_literals" in root.future_features:
            return StringType.UNICODE
        # TODO(thatch): Upstream some kind of infer-python-version check like looking
        # for typehints or fstrings to know it's 3.6+.  lib2to3 doesn't tell us what
        # version it is compatible with.
        return StringType.UNKNOWN


def count_escapes(str_quote: str, str_inner_data: str):
    """Counts the backslash escapes that are allowed.

    The return keys are 'bytes' (valid in bytes/str), 'string' (only str), and
    'invalid' (neither).
    """
    counts = {"bytes": 0, "string": 0, "invalid": 0}

    for m in ESCAPE_RE.finditer(str_inner_data):
        if m.group(1) == str_quote or m.group(1) in BYTES_ESCAPES:
            counts["bytes"] += 1
        elif m.group(1) in STRING_ESCAPES:
            counts["string"] += 1
        else:
            counts["invalid"] += 1

    return counts


def modifier(node, capture, filename):  # noqa: C901
    str_prefix, str_quote, str_inner_data = explode_string(node.value)

    if "r" in str_prefix.lower():
        return

    if CAREFUL and maybe_ascii_art(node):
        return
    elif CAREFUL and maybe_latex(node):
        return

    str_type = infer_string_type(str_prefix, node)
    if str_type is StringType.UNKNOWN:
        # wontfix, too much risk of messing things up
        return

    old_parsed_str = eval(  # noqa: P204
        str_prefix.replace("f", "").replace("F", "")
        + str_quote
        + str_inner_data
        + str_quote,
        {},
        {},
    )
    counts = count_escapes(str_quote, str_inner_data)

    if str_type is StringType.BYTES:
        counts["invalid"] += counts["string"]
        counts["string"] = 0
        legal_escapes = BYTES_ESCAPES
    else:
        legal_escapes = BYTES_ESCAPES | STRING_ESCAPES

    if not counts["invalid"]:
        return

    def conditionalprefix(m):
        if m.group(1) not in legal_escapes:
            return "\\" + m.group(0)
        return m.group(0)

    if counts["string"] == 0 and counts["bytes"] == 0 and "u" not in str_prefix.lower():
        # Only invalid escapes, trivial to make rawstring
        str_prefix += "r"
    else:
        str_inner_data = ESCAPE_RE.sub(conditionalprefix, str_inner_data)

    # This ensures that they're parsed-identical, not just for the `re` module.
    # Because backslash literals are not allowed inside f-{}, can safely
    # remove the f-prefix to make the eval not fail.
    new_parsed_str = eval(  # noqa: P204
        str_prefix.replace("f", "").replace("F", "")
        + str_quote
        + str_inner_data
        + str_quote,
        {},
        {},
    )

    assert old_parsed_str == new_parsed_str, (
        "\n" + repr(old_parsed_str) + "\n" + repr(new_parsed_str)
    )  # noqa: P204

    return Leaf(
        type=TOKEN.STRING,
        prefix=node.prefix,
        value=str_prefix + str_quote + str_inner_data + str_quote,
    )


def main():
    write_mode = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "w":
            write_mode = True
            sys.argv.pop(1)

    q = (
        Query(sys.argv[1:])
        .select(SELECTOR)
        .modify(modifier)
    )
    if write_mode:
        q.execute(write=True, interactive=False)
    else:
        q.diff()


if __name__ == "__main__":
    main()
