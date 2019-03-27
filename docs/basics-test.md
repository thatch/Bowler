---
id: basics-test
title: Testing
---

## Test-driven development

Developing a bowler refactor can be daunting at first, especially because errors
are simplified in the normal `bowler run` environment.	By writing tests that
define our behavior first, we can iterate faster and provide more verbose
debugging facilities.

For this tutorial, let's say you want to ensure that all calls to `re.compile`
take rawstrings as the first positional argument.

## Writing your TestCase

Start by importing the necessary bits, and defining your BowlerTestCase
subclass.


```python
from bowler import Query
from bowler.tests.lib import BowlerTestCase

class MyTests(BowlerTestCase):
		pass
```

It has a couple of ways to run your tests, check out docs/api-tests
for more on that.		We'll use the side-by-side comment format, as it's easy to
read for multiline tests.

```python
class MyTests(BowlerTestCase):

		def build_query(self, filenames):
				return Query(filename).select(SELECTOR).modify(modifier)

		def test_empty_string(self):
				self.do('''
						re.compile('')		 #+ re.compile(r'')
						''')

		def test_backslashes(self):
				self.do(r'''
						re.compile(r'\s+')
						re.compile('\\s+') #+ re.compile(r'\s+')
						''')
```

We haven't defined `SELECTOR` or `modifier` yet, but we will in a second.  Each
of these tests contains a multiline string, which will be run through as input
with the fluent chain described in `build_query`.  This format is pretty
straightforward -- it basically follows the indentation rules of docstrings, and
if a line should be modified in the output, give the new version in a comment
starting with `#+`.

Let's go through writing the rest.	To make your selector, a simple way is to
write an example file and use `bowler dump` on it.

```
$ echo "re.compile('')" > t.py
$ bowler dump t.py
/home/foo/t.py
[file_input] ''
.  [simple_stmt] ''
.  .	[power] ''
.  .	.  [NAME] '' 're'
.  .	.  [trailer] ''
.  .	.  .	[DOT] '' '.'
.  .	.  .	[NAME] '' 'compile'
.  .	.  [trailer] ''
.  .	.  .	[LPAR] '' '('
.  .	.  .	[STRING] '' "''"
.  .	.  .	[RPAR] '' ')'
.  .	[NEWLINE] '' '\n'
.  [ENDMARKER] '' ''
```

In order to match this, you could use `select_method('compile')` or write it
yourself.  Converting this to lib2to3 format, we have

```
SELECTOR = '''
power <
	're'
	trailer <
		'.'
		'compile'
	>
	trailer <
		'('
		firstarg=STRING
		any*
	>
	any *
>
'''
```

Let's add a simple no-op modifier, and watch things fail.

```
def modifier(node, capture, filename=None):
		pass
```

```
$ python3 -m unittest demo.py
FF
======================================================================
FAIL: test_backslashes (demo.MyTests)
----------------------------------------------------------------------
Traceback (most recent call last):
	File "/home/foo/code/Bowler/demo.py", line 18, in test_backslashes
		''')
	File "/home/foo/code/Bowler/bowler/tests/lib.py", line 117, in do
		self.assertEqual("\n".join(right) + "\n", fr.read())
AssertionError: "re.compile(r'\\s+')\nre.compile(r'\\s+')\n\n" != "re.compile(r'\\s+')\nre.compile('\\\\s+')\n\n"
	re.compile(r'\s+')
- re.compile(r'\s+')
?						 -
+ re.compile('\\s+')
?							+
	


======================================================================
FAIL: test_empty_string (demo.MyTests)
----------------------------------------------------------------------
Traceback (most recent call last):
	File "/home/foo/code/Bowler/demo.py", line 12, in test_empty_string
		''')
	File "/home/foo/code/Bowler/bowler/tests/lib.py", line 117, in do
		self.assertEqual("\n".join(right) + "\n", fr.read())
AssertionError: "re.compile(r'')\n\n" != "re.compile('')\n\n"
- re.compile(r'')
?						 -
+ re.compile('')
	


----------------------------------------------------------------------
Ran 2 tests in 0.120s

FAILED (failures=2)
```

The displayed format is a unified diff, but most people probably aren't
familiar with the `?` lines which show you the characters added or removed in
the line.

We don't yet know that the selector matched anything or the modifier took
effect.  So let's write the modifier.

```
from bowler.types import TOKEN, Leaf

def modifier(node, capture, filename=None):
		return Leaf(type=TOKEN.STRING, value="'foo'")
```

This might produce a more interesting failure.	It replaces the *entire* match,
but we don't want that.  We just want to replace the arg.  So let's try:

```python
def modifier(node, capture, filename=None):
		new_str = Leaf(type=TOKEN.STRING, value="'foo'")
		capture["firstarg"].replace(new_str)
```

In particular, note that we didn't return anything.  The `replace` method does
an in-place modification, while returning something is equivalent to
`node.replace(return_value)`.

Now let's figure out how to deal with the string transform we want to do.  There's a core library called `bowler.strings` that has some helpers.

```python
import re
from bowler.strings import explode_string

ESCAPE_RE = re.compile(r'\.', re.DOTALL)  # non-strict, and match newline


def modifier(node, capture, filename=None):
		type, quote, body = explode_string(capture["firstarg"].value)

		if "f" in type.lower():
				return  # Leave f-strings as they are for now, they're tricky.
		elif "r" in type.lower():
				return  # If it's already raw, great.

		



