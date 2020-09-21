import re
import string

'''
left: apply the operator starting at the beginning of the value and stop when it can no longer be applied, e.g., remove numbers and stop when a non-number is found
right: apply the operator from the right end of the value
left-and-right: apply if both on the left and the right
everywhere: start on the left and keep applying the operator after skipping the characters where it does not apply, e.g., remove all numbers in a value regardless of where they appear
'''

left="left"
right="right"
left_and_right="left-and-right"
everywhere="everywhere"

'''
Example:
cleaning:
  - strip-whitespace: auto 
    where: left-and-right
  - remove-symbols: auto 
    where: left
  - remove-unicodes: auto
    where: everywhere
  - remove-numbers: auto
    where: right
  - remove-letters: auto
    where: everywhere
  - remove-regex: <regex>
    where: left
  - remove-long: 50
  - normalize-whitespace: auto
  - replace-whitespace: _
  - change-case: sentence
  - pad: 10
    text: 0
    where: left
  - make-numeric: auto
  - fix-url: auto

'''

def strip_whitespace(input, char=None, where=left_and_right):
    """
    strip-whitespace:
    char: default None, removes all whitespace
          can also accept " "space
          or "\t" tab
    """
    if where == left:
        return str(input).lstrip( chars=char)
    if where == right:
        return str(input).rstrip( chars=char)
    if where == left_and_right:
        return str(input).strip( chars=char)
    if where == everywhere:
        return "".join(str(input).split(sep=char))

def remove_symbols(input, to_remove="all", where=left):
    '''remove-symbols:
auto: all symbols but not unicodes
punctuation
parenthesis
 ''' 
    if where=="everywhere": #bunch of really efficient options for this one:
        if to_remove=="all":
            return ''.join(e for e in input if e.isalnum())
        if to_remove=="punctuation":
            return input.translate(str.maketrans('', '', string.punctuation))
        if to_remove=="parenthesis":
            return input.translate(str.maketrans('', '', ["(", ")", "[", "]", "{", "}"]))


def remove_unicodes(input, where=everywhere):
    ''' remove-unicodes:
auto: all non-ascii characters
emoji
''' 
    pass

def remove_numbers(input,  where=right):
    ''' remove-numbers:
auto: all digits
list of specific numbers, e.g., "1, 2, 3, 5, 7, 11, 13, 17"
''' 
    pass

def remove_letters(input, where=everywhere):
    ''' remove-letters:
auto: all letters
list of specific letters, letter ranges or strings, e.g., "a, b, m-p, pedro, szekely"
''' 
    pass

def remove_regex(input, where=left):
    '''remove-regex:
if the regex has no group, it removes the part that matches; if there are groups, it removes all the groups.
where specifies the direction and the number of times it is matched
 ''' 
    pass

def remove_long(input, length):
    ''' remove-long:
delete cell values where the string length is >= the specified number of characters
''' 
    pass

def normalize_whitespace(input ):
    ''' normalize-whitespace:
auto: replaces multiple consecutive whitespace characters by one space
tab: replaces by one tab
''' 
    pass

def replace_whitespace(input ):
    ''' ''' 
    pass

def change_case(input ):
    ''' change-case:
auto: changes the case to sentence case
sentence
lower
upper
title
''' 
    pass

def pad(input,  where=left):
    ''' pad:
the main argument is a length in number of characters
text: what text to add, if the text is longer than one character and the number of characters does not divide exactly then smartly choose depending on whether it is on the left or the right (other values or where are errors)
''' 
    pass

def make_numeric(input ):
    '''make-numeric:
auto: smart function to make the values of a cell numeric
remove leading and trailing non-numeric characters
interprets commas and dots smartly
removes whitespace inside the number
interprets exponential notation
 ''' 
    pass

def fix_url(input ):
    ''' fix-url:
auto: remove leading junk, fix the obnoxious htxxxx prefix that you sometimes get, decode in case it was encoded
''' 
    pass

cleaning_functions_dict=dict(
    strip_whitespace=strip_whitespace,
    remove_symbols=remove_symbols,
    remove_unicodes=remove_unicodes,
    remove_numbers=remove_numbers,
    remove_letters=remove_letters,
    remove_regex=remove_regex,
    remove_long=remove_long,
    normalize_whitespace=normalize_whitespace,
    change_case=change_case,
    pad=pad,
    make_numeric=make_numeric,
    fix_url=fix_url
)