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
    Args:
        input ([type]): [description]
        char ([type], optional): [description]. Defaults to None- remove all whitespace. Can also accept " " space or "\t" tab
        where (["left", "right", "left_and_right", "everywhere"], optional): [description]. Defaults to left_and_right.

    Returns:
        [type]: [description]
    """
    if where == everywhere:
        return "".join(str(input).split(sep=char))
    if where == left:
        return str(input).lstrip(char)
    if where == right:
        return str(input).rstrip(char)
    if where == left_and_right:
        return str(input).strip(char)

def remove_symbols(input, to_remove="all", where=left):
    """[summary]

    Args:
        input ([type]): [description]
        to_remove (["all", "parenthesis", "punctuation"], optional): [description]. Defaults to "all".
        where (["left", "right", "left_and_right", "everywhere"], optional): [description]. Defaults to left.

    Returns:
        str: modified string
    """
    input=str(input)

    if to_remove=="parentheses":
        forbidden="()[]{}"
    elif to_remove=="punctuation":
        forbidden=string.punctuation
    elif to_remove=="all":
        forbidden=None #use a different mechanism
    else:
        raise ValueError("to_remove must be all, parentheses, or punctuation")
    
    if where==everywhere: #bunch of really efficient options for this one:
        if to_remove=="all":
            raise NotImplementedError
        else:
            return input.translate(str.maketrans('', '', forbidden))
    

    if where==left or where == left_and_right:
        if to_remove=="all":
            while not input[0].isalnum():
                input=input[1:]
        else:
            while input[0] in forbidden:
                input=input[1:]

    if where==right or where == left_and_right:
        if to_remove=="all":
            while not input[-1].isalnum():
                input=input[:-2]
        else:
            while input[-1] in forbidden:
                input=input[:-2]
    
    return input





def remove_unicode(input, to_remove="all", where=everywhere):
    """[summary]

    Args:
        input ([type]): [description]
        to_remove (str, optional): [description]. Defaults to "all"- all non-ascii characters
        where ([type], optional): [description]. Defaults to everywhere.

    Returns:
        [type]: [description]
    """
    if where==everywhere:
        if to_remove=="all":
            return ''.join(e for e in input if e.isalnum())

def remove_numbers(input, numbers=None,  where=right):
    ''' remove-numbers:
    auto: all digits
    list of specific numbers, e.g., "1, 2, 3, 5, 7, 11, 13, 17"
    '''
    if numbers:
        numbers = sorted(numbers, key=lambda num:int(num))[::-1] #search for larger numbers first
    else:
        numbers=["\d*"]
    for num in numbers: #if it was limited to single digits, easier, but since it needs to be specific numbers...
        if where==everywhere:
            input= re.sub(str(num), "", input)
        if where==right or where ==left_and_right:
            sub_string="^"+str(num)
            input= re.sub(sub_string, "", input)
        if where==left or where==left_and_right:
            sub_string=str(num)+"$"
            input= re.sub(sub_string, "", input)
    return input


def remove_letters(input, letters=None, where=everywhere):
    ''' remove-letters:
    auto: all letters
    list of specific letters, letter ranges or strings, e.g., "a, b, m-p, pedro, szekely"
    ''' 
    pass

def remove_regex(input, regex, where=left):
    '''remove-regex:
    if the regex has no group, it removes the part that matches; if there are groups, it removes all the groups.
    where specifies the direction and the number of times it is matched
    ''' 
    pass

def remove_long(input, length):
    ''' remove-long:
    delete cell values where the string length is >= the specified number of characters
    ''' 
    if len(str(input))>length:
        return ""
    return input

def normalize_whitespace(input, tab=False):
    ''' normalize-whitespace:
    auto: replaces multiple consecutive whitespace characters by one space
    tab: replaces by one tab
    ''' 
    replacement=" "
    if tab:
        replacement="\t"
    return re.sub("\s{2,}", replacement, input)

def replace_whitespace(input ):
    ''' ''' 
    pass

def change_case(input, case="sentence"):
    ''' change-case:
    auto: changes the case to sentence case
    sentence
    lower
    upper
    title
    ''' 
    if case=="sentence":
        return str(input).capitalize()
    if case=="lower":
        return str(input).lower()
    if case=="upper":
        return str(input).upper()
    if case=="title":
        return str(input).title()

def pad(input,  where=left):
    ''' pad:
    the main argument is a length in number of characters
    text: what text to add, if the text is longer than one character and the number of characters does not divide exactly then smartly choose depending on whether it is on the left or the right (other values or where are errors)
    ''' 
    pass

def make_numeric(input):
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
    remove_unicode=remove_unicode,
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


