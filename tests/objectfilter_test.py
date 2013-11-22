#!/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for objectfilter.objectfilter."""


import logging
import unittest

from objectfilter import objectfilter


attr1 = "Backup"
attr2 = "Archive"
hash1 = "123abc"
hash2 = "456def"
filename = "yay.exe"


class DummyObject(object):
  def __init__(self, key, value):
    setattr(self, key, value)


class HashObject(object):
  def __init__(self, hash_value=None):
    self.value = hash_value

  @property
  def md5(self):
    return self.value

  def __eq__(self, y):
    return self.value == y

  def __lt__(self, y):
    return self.value < y


class Dll(object):
  def __init__(self, name, imported_functions=None, exported_functions=None):
    self.name = name
    self._imported_functions = imported_functions or []
    self.num_imported_functions = len(self._imported_functions)
    self.exported_functions = exported_functions or []
    self.num_exported_functions = len(self.exported_functions)

  @property
  def imported_functions(self):
    for fn in self._imported_functions:
      yield fn


class DummyFile(object):
  non_callable_leaf = "yoda"

  def __init__(self):
    self.non_callable = HashObject(hash1)
    self.non_callable_repeated = [DummyObject("desmond", ["brotha",
                                                          "brotha"]),
                                  DummyObject("desmond", ["brotha",
                                                          "sista"])]
    self.imported_dll1 = Dll("a.dll", ["FindWindow", "CreateFileA"])
    self.imported_dll2 = Dll("b.dll", ["RegQueryValueEx"])

  @property
  def name(self):
    return filename

  @property
  def attributes(self):
    return [attr1, attr2]

  @property
  def hash(self):
    return [HashObject(hash1), HashObject(hash2)]

  @property
  def size(self):
    return 10

  @property
  def deferred_values(self):
    for v in ["a", "b"]:
      yield v

  @property
  def novalues(self):
    return []

  @property
  def imported_dlls(self):
    return [self.imported_dll1, self.imported_dll2]

  def Callable(self):
    raise RuntimeError("This can not be called.")

  @property
  def float(self):
    return 123.9823


class ObjectFilterTest(unittest.TestCase):
  def setUp(self):
    self.file = DummyFile()
    self.filter_imp = objectfilter.LowercaseAttributeFilterImplementation
    self.value_expander = self.filter_imp.FILTERS["ValueExpander"]

  operator_tests = {
      objectfilter.Less: [
          (True, ["size", 1000]),
          (True, ["size", 11]),
          (False, ["size", 10]),
          (False, ["size", 0]),
          (False, ["float", 1.0]),
          (True, ["float", 123.9824]),
          ],
      objectfilter.LessEqual: [
          (True, ["size", 1000]),
          (True, ["size", 11]),
          (True, ["size", 10]),
          (False, ["size", 9]),
          (False, ["float", 1.0]),
          (True, ["float", 123.9823]),
          ],
      objectfilter.Greater: [
          (True, ["size", 1]),
          (True, ["size", 9.23]),
          (False, ["size", 10]),
          (False, ["size", 1000]),
          (True, ["float", 122]),
          (True, ["float", 1.0]),
          ],
      objectfilter.GreaterEqual: [
          (False, ["size", 1000]),
          (False, ["size", 11]),
          (True, ["size", 10]),
          (True, ["size", 0]),
          # Floats work fine too
          (True, ["float", 122]),
          (True, ["float", 123.9823]),
          # Comparisons works with strings, although it might be a bit silly
          (True, ["name", "aoot.ini"]),
          ],
      objectfilter.Contains: [
          # Contains works with strings
          (True, ["name", "yay.exe"]),
          (True, ["name", "yay"]),
          (False, ["name", "meh"]),
          # Works with generators
          (True, ["imported_dlls.imported_functions", "FindWindow"]),
          # But not with numbers
          (False, ["size", 12]),
          ],
      objectfilter.NotContains: [
          (False, ["name", "yay.exe"]),
          (False, ["name", "yay"]),
          (True, ["name", "meh"]),
          ],
      objectfilter.Equals: [
          (True, ["name", "yay.exe"]),
          (False, ["name", "foobar"]),
          (True, ["float", 123.9823]),
          ],
      objectfilter.NotEquals: [
          (False, ["name", "yay.exe"]),
          (True, ["name", "foobar"]),
          (True, ["float", 25]),
          ],
      objectfilter.InSet: [
          (True, ["name", ["yay.exe", "autoexec.bat"]]),
          (True, ["name", "yay.exe"]),
          (False, ["name", "NOPE"]),
          # All values of attributes are within these
          (True, ["attributes", ["Archive", "Backup", "Nonexisting"]]),
          # Not all values of attributes are within these
          (False, ["attributes", ["Executable", "Sparse"]]),
          ],
      objectfilter.NotInSet: [
          (False, ["name", ["yay.exe", "autoexec.bat"]]),
          (False, ["name", "yay.exe"]),
          (True, ["name", "NOPE"]),
          ],
      objectfilter.Regexp: [
          (True, ["name", "^yay.exe$"]),
          (True, ["name", "yay.exe"]),
          (False, ["name", "^$"]),
          (True, ["attributes", "Archive"]),
          # One can regexp numbers if he's inclined to
          (True, ["size", 0]),
          # But regexp doesn't work with lists or generators for the moment
          (False, ["imported_dlls.imported_functions", "FindWindow"])
          ],
      }

  def testBinaryOperators(self):
    for operator, test_data in self.operator_tests.items():
      for test_unit in test_data:
        logging.debug("Testing %s with %s and %s",
                      operator, test_unit[0], test_unit[1])
        kwargs = {"arguments": test_unit[1],
                  "value_expander": self.value_expander}
        self.assertEqual(test_unit[0], operator(**kwargs).Matches(self.file))

  def testExpand(self):
    # Case insensitivity
    values_lowercase = self.value_expander().Expand(self.file, "size")
    values_uppercase = self.value_expander().Expand(self.file, "Size")
    self.assertListEqual(list(values_lowercase), list(values_uppercase))

    # Existing, non-repeated, leaf is a value
    values = self.value_expander().Expand(self.file, "size")
    self.assertListEqual(list(values), [10])

    # Existing, non-repeated, leaf is iterable
    values = self.value_expander().Expand(self.file, "attributes")
    self.assertListEqual(list(values), [[attr1, attr2]])

    # Existing, repeated, leaf is value
    values = self.value_expander().Expand(self.file, "hash.md5")
    self.assertListEqual(list(values), [hash1, hash2])

    # Existing, repeated, leaf is iterable
    values = self.value_expander().Expand(self.file,
                                          "non_callable_repeated.desmond")
    self.assertListEqual(list(values), [["brotha", "brotha"],
                                        ["brotha", "sista"]])

    # Now with an iterator
    values = self.value_expander().Expand(self.file, "deferred_values")
    self.assertListEqual([list(value) for value in values], [["a", "b"]])

    # Iterator > generator
    values = self.value_expander().Expand(self.file,
                                          "imported_dlls.imported_functions")
    expected = [
        ["FindWindow", "CreateFileA"],
        ["RegQueryValueEx"]]
    self.assertListEqual([list(value) for value in values], expected)

    # Non-existing first path
    values = self.value_expander().Expand(self.file, "nonexistant")
    self.assertListEqual(list(values), [])

    # Non-existing in the middle
    values = self.value_expander().Expand(self.file, "hash.mink.boo")
    self.assertListEqual(list(values), [])

    # Non-existing as a leaf
    values = self.value_expander().Expand(self.file, "hash.mink")
    self.assertListEqual(list(values), [])

    # Non-callable leaf
    values = self.value_expander().Expand(self.file, "non_callable_leaf")
    self.assertListEqual(list(values), [DummyFile.non_callable_leaf])

    # callable
    values = self.value_expander().Expand(self.file, "Callable")
    self.assertListEqual(list(values), [])

    # leaf under a callable. Will return nothing
    values = self.value_expander().Expand(self.file, "Callable.a")
    self.assertListEqual(list(values), [])

  def testGenericBinaryOperator(self):
    class TestBinaryOperator(objectfilter.GenericBinaryOperator):
      values = list()

      def Operation(self, x, _):
        return self.values.append(x)

    # Test a common binary operator
    tbo = TestBinaryOperator(arguments=["whatever", 0],
                             value_expander=self.value_expander)
    self.assertEqual(tbo.right_operand, 0)
    self.assertEqual(tbo.args[0], "whatever")
    tbo.Matches(DummyObject("whatever", "id"))
    tbo.Matches(DummyObject("whatever", "id2"))
    tbo.Matches(DummyObject("whatever", "bg"))
    tbo.Matches(DummyObject("whatever", "bg2"))
    self.assertListEqual(tbo.values, ["id", "id2", "bg", "bg2"])

  def testContext(self):
    self.assertRaises(objectfilter.InvalidNumberOfOperands,
                      objectfilter.Context,
                      arguments=["context"],
                      value_expander=self.value_expander)
    self.assertRaises(objectfilter.InvalidNumberOfOperands,
                      objectfilter.Context,
                      arguments=
                      ["context",
                       objectfilter.Equals(arguments=["path", "value"],
                                           value_expander=self.value_expander),
                       objectfilter.Equals(arguments=["another_path", "value"],
                                           value_expander=self.value_expander)
                      ],
                      value_expander=self.value_expander)
    # "One imported_dll imports 2 functions AND one imported_dll imports
    # function RegQueryValueEx"
    arguments = [
        objectfilter.Equals(["imported_dlls.num_imported_functions", 1],
                            value_expander=self.value_expander),
        objectfilter.Contains(["imported_dlls.imported_functions",
                               "RegQueryValueEx"],
                              value_expander=self.value_expander)]
    condition = objectfilter.AndFilter(arguments=arguments)
    # Without context, it matches because both filters match separately
    self.assertEqual(True, condition.Matches(self.file))

    arguments = [
        objectfilter.Equals(["num_imported_functions", 2],
                            value_expander=self.value_expander),
        objectfilter.Contains(["imported_functions", "RegQueryValueEx"],
                              value_expander=self.value_expander)]
    condition = objectfilter.AndFilter(arguments=arguments)
    # "The same DLL imports 2 functions AND one of these is RegQueryValueEx"
    context = objectfilter.Context(arguments=["imported_dlls", condition],
                                   value_expander=self.value_expander)
    # With context, it doesn't match because both don't match in the same dll
    self.assertEqual(False, context.Matches(self.file))

    # "One imported_dll imports only 1 function AND one imported_dll imports
    # function RegQueryValueEx"
    condition = objectfilter.AndFilter(arguments=[
        objectfilter.Equals(arguments=["num_imported_functions", 1],
                            value_expander=self.value_expander),
        objectfilter.Contains(["imported_functions", "RegQueryValueEx"],
                              value_expander=self.value_expander)])
    # "The same DLL imports 1 function AND it"s RegQueryValueEx"
    context = objectfilter.Context(["imported_dlls", condition],
                                   value_expander=self.value_expander)
    self.assertEqual(True, context.Matches(self.file))

    # Now test the context with a straight query
    query = """
@imported_dlls
(
  imported_functions contains "RegQueryValueEx"
  AND num_imported_functions == 1
)
"""
    self.assertObjectMatches(self.file, query)

  def testRegexpRaises(self):
    self.assertRaises(ValueError, objectfilter.Regexp,
                      arguments=["name", "I [dont compile"],
                      value_expander=self.value_expander)

  def testEscaping(self):
    parser = objectfilter.Parser(r"a is '\n'").Parse()
    self.assertEqual(parser.args[0], "\n")
    # Invalid escape sequence
    parser = objectfilter.Parser(r"a is '\z'")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Can escape the backslash
    parser = objectfilter.Parser(r"a is '\\'").Parse()
    self.assertEqual(parser.args[0], "\\")

    ## HEX ESCAPING
    # This fails as it's not really a hex escaped string
    parser = objectfilter.Parser(r"a is '\xJZ'")
    self.assertRaises(objectfilter.ParseError, parser.Parse)
    # Instead, this is what one should write
    parser = objectfilter.Parser(r"a is '\\xJZ'").Parse()
    self.assertEqual(parser.args[0], r"\xJZ")
    # Standard hex-escape
    parser = objectfilter.Parser(r"a is '\x41\x41\x41'").Parse()
    self.assertEqual(parser.args[0], "AAA")
    # Hex-escape + a character
    parser = objectfilter.Parser(r"a is '\x414'").Parse()
    self.assertEqual(parser.args[0], r"A4")
    # How to include r'\x41'
    parser = objectfilter.Parser(r"a is '\\x41'").Parse()
    self.assertEqual(parser.args[0], r"\x41")

  def ParseQuery(self, query):
    return objectfilter.Parser(query).Parse()

  def assertQueryParses(self, query):
    self.ParseQuery(query)

  def assertParseRaises(self, query, exception=objectfilter.ParseError):
    parser = objectfilter.Parser(query)
    self.assertRaises(exception, parser.Parse)

  def testParse(self):
    # We need to complete a basic expression
    self.assertParseRaises("            ")
    self.assertParseRaises("attribute")
    self.assertParseRaises("attribute is")

    # We have to go from an expression to the ANDOR state
    self.assertParseRaises("attribute is 3 really")
    self.assertParseRaises("attribute is 3 AND")
    self.assertParseRaises("attribute is 3 AND bla")
    self.assertParseRaises("attribute is 3 AND bla contains")

    # Two complete expressions parse fine
    query = "attribute is 3 AND name contains 'atthew'"
    self.assertQueryParses(query)

    # Arguments are either int, float or quoted string
    self.assertQueryParses("attribute == 1")
    self.assertQueryParses("attribute == 0x10")
    self.assertParseRaises("attribute == 1a")
    self.assertQueryParses("attribute == 1.2")
    self.assertParseRaises("attribute == 1.2a3")
    # Scientific notation is not accepted...
    self.assertParseRaises("attribute == 1e3")

    # Test both quoted strings
    self.assertQueryParses("attribute == 'bla'")
    self.assertQueryParses("attribute == \"bla\"")
    # Unquoted strings fail
    self.assertParseRaises("something == red")

    # Can't start with AND
    self.assertParseRaises("and something is 'Blue'")

    # Need to match parentheses
    self.assertParseRaises("(a is 3")
    self.assertParseRaises("((a is 3")
    self.assertParseRaises("((a is 3)")
    self.assertParseRaises("a is 3)")
    self.assertParseRaises("a is 3))")
    self.assertParseRaises("(a is 3))")
    # Need to put parentheses in the right place
    self.assertParseRaises("()a is 3")
    self.assertParseRaises("(a) is 3")
    self.assertParseRaises("(a is) 3")
    self.assertParseRaises("a (is) 3")
    self.assertParseRaises("a is() 3")
    self.assertParseRaises("a is (3)")
    self.assertParseRaises("a is 3()")
    self.assertParseRaises("a (is 3 AND) b is 4 ")
    # In the right places, parentheses are accepted
    self.assertQueryParses("(a is 3)")
    self.assertQueryParses("(a is 3 AND b is 4)")

    # Context Operator alone is not accepted
    self.assertParseRaises("@attributes")
    # Accepted only with braces (not necessary but forced by the grammar
    # to be explicit)
    objectfilter.Parser("@attributes( name is 'adrien')").Parse()
    # Not without them
    self.assertParseRaises("@attributes name is 'adrien'")
    # Or in the wrong place
    self.assertParseRaises("@attributes (name is) 'adrien'")
    # Can nest context operators
    query = "@imported_dlls( @imported_function( name is 'OpenFileA'))"
    self.assertQueryParses(query)
    # Can nest context operators and mix braces without it messing up
    query = "@imported_dlls( @imported_function( name is 'OpenFileA'))"
    self.assertQueryParses(query)

    query = """
@imported_dlls
(
  @imported_function
  (
    name is 'OpenFileA'
  )
)
"""
    self.assertQueryParses(query)

    # Mix context and binary operators
    query = """
@imported_dlls
(
  @imported_function
  (
    name is 'OpenFileA'
  ) AND num_functions == 2
)
"""
    self.assertQueryParses(query)

    # Also on the right
    query = """
@imported_dlls
(
  num_functions == 2 AND
  @imported_function
  (
    name is 'OpenFileA'
  )
)
"""
    query = "b is 3 AND c is 4 AND d is 5"
    self.assertQueryParses(query)
    query = "@a(b is 3) AND @b(c is 4)"
    self.assertQueryParses(query)
    query = "@a(b is 3) AND @b(c is 4) AND @d(e is 5)"
    self.assertQueryParses(query)
    query = "@a(@b(c is 3)) AND @b(d is 4)"
    self.assertQueryParses(query)

    query = """
@imported_dlls( @imported_function ( name is 'OpenFileA' ) )
AND
@imported_dlls(
  name regexp '(?i)advapi32.dll'
  AND @imported_function ( name is 'RegQueryValueEx' )
)
AND @exported_symbols(name is 'inject')
"""
    self.assertQueryParses(query)

    self.assertQueryParses("a is ['blue', 'dot']")
    self.assertQueryParses("a is ['blue', 1]")
    self.assertQueryParses("a is [1]")
    # This is an empty list
    self.assertQueryParses("a is []")
    # While weird, the current parser allows this. Same as an empty list
    self.assertQueryParses("a is [,,]")
    # Unifinished expressions shouldn't parse
    self.assertParseRaises("a is [")
    self.assertParseRaises("a is [,,")
    self.assertParseRaises("a is [,']")
    # Malformed expressions shouldn't parse
    self.assertParseRaises("a is [[]")
    self.assertParseRaises("a is []]")
    # We do not support nested lists at the moment
    self.assertParseRaises("a is ['cannot', ['nest', 'lists']]")

  def assertObjectMatches(self, obj, query, match_is=True):
    parser = self.ParseQuery(query)
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), match_is)

  def testCompile(self):
    obj = DummyObject("something", "Blue")

    query = "something == 'Blue'"
    self.assertObjectMatches(obj, query)

    query = "something == 'Red'"
    self.assertObjectMatches(obj, query, match_is=False)

    query = "something == \"Red\""
    self.assertObjectMatches(obj, query, match_is=False)

    obj = DummyObject("size", 4)
    parser = objectfilter.Parser("size < 3").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), False)
    parser = objectfilter.Parser("size == 4").Parse()
    filter_ = parser.Compile(self.filter_imp)
    self.assertEqual(filter_.Matches(obj), True)

    query = "something is 'Blue' and size notcontains 3"
    self.assertObjectMatches(obj, query, match_is=False)

    query = """
@imported_dlls
(
  name is 'a.dll'
  AND imported_functions contains 'CreateFileA'
)
AND name is "yay.exe"
AND size is 10
"""
    self.assertObjectMatches(self.file, query)

    query = """
@imported_dlls
(
  name is 'a.dll'
  AND imported_functions contains 'CreateFileB'
)
AND name is "yay.exe"
AND size is 10
"""
    self.assertObjectMatches(self.file, query, match_is=False)

    obj = DummyObject("list", [1,2])
    self.assertObjectMatches(obj, "list is [1,2]")
    self.assertObjectMatches(obj, "list is [5,6]", match_is=False)
    self.assertObjectMatches(obj, "list isnot [1,3]")
    self.assertObjectMatches(obj, "list inset [1,2,3]")
    obj = DummyObject("list", [])
    self.assertObjectMatches(obj, "list is []")
    self.assertObjectMatches(obj, "list inset []")
    # An empty set [] is a subset of any set. Hence this is False.
    self.assertObjectMatches(obj, "list notinset [2]", match_is=False)
    obj = DummyObject("single_element", 1)
    self.assertObjectMatches(obj, "single_element inset [1,2,3]")
    # 1 != [1]
    self.assertObjectMatches(obj, "single_element isnot [1]")
    obj = DummyObject("os", "windows")
    self.assertObjectMatches(obj, 'os inset ["windows", "mac"]')
    # "a" != ["a"]
    self.assertObjectMatches(obj, 'os isnot ["windows"]')