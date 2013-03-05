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

def SmartUnicode(string):
    """Returns a unicode object.

    This function will always return a unicode object. It should be used to
    guarantee that something is always a unicode object.

    Blatantly stolen from GRR: http://code.google.com/p/grr .

    Args:
      string: The string to convert.

    Returns:
      a unicode object.
    """
    if type(string) != unicode:
        try:
            return string.__unicode__()
        except (AttributeError, UnicodeError):
            return str(string).decode("utf8", "ignore")

    return string