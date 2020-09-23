import re
import string

'''
start: apply the operator starting at the beginning of the value and stop when it can no longer be applied, e.g., remove numbers and stop when a non-number is found
end: apply the operator from the end end of the value
start-and-end: apply if both on the start and the end
everywhere: start on the start and keep applying the operator after skipping the characters where it does not apply, e.g., remove all numbers in a value regardless of where they appear
'''

start="start"
end="end"
start_and_end="start-and-end"
everywhere="everywhere"

'''
Example:
cleaning:
  - strip-whitespace: auto 
    where: start-and-end
  #- remove-symbols: auto 
  #  where: start
  #- remove-unicodes: auto
  #  where: everywhere
  - make_alphanumeric
  - make_ascii
  - remove-numbers: auto
    where: end
  - remove-letters: auto
    where: everywhere
  - remove-regex: <regex>
    where: start
  #- remove-long: 50
  - truncate
  - normalize-whitespace: auto
  - replace-whitespace: _
  - change-case: sentence
  - pad: 10
    text: 0
    where: start
  - make-numeric: auto
  - fix-url: auto

'''

def strip_whitespace(input, char=None, where=start_and_end):
    """
    Args:
        input ([type]): [description]
        char ([type], optional): [description]. Defaults to None- remove all whitespace. Can also accept " " space or "\t" tab
        where (["start", "end", "start_and_end", "everywhere"], optional): [description]. Defaults to start_and_end.

    Returns:
        [type]: [description]
    """
    if where == everywhere:
        return "".join(str(input).split(sep=char))
    if where == start:
        return str(input).lstrip(char)
    if where == end:
        return str(input).rstrip(char)
    if where == start_and_end:
        return str(input).strip(char)


def remove_numbers(input, numbers=None,  where=end):
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
        if where==end or where ==start_and_end:
            sub_string="^"+str(num)
            input= re.sub(sub_string, "", input)
        if where==start or where==start_and_end:
            sub_string=str(num)+"$"
            input= re.sub(sub_string, "", input)
    return input


def remove_letters(input, letters=None, where=everywhere):
    ''' remove-letters:
    auto: all letters
    list of specific letters, letter ranges or strings, e.g., "a, b, m-p, pedro, szekely"
    ''' 
    pass

def remove_regex(input, regex, where=start):
    '''remove-regex:
    if the regex has no group, it removes the part that matches; if there are groups, it removes all the groups.
    where specifies the direction and the number of times it is matched
    ''' 
    pass

def truncate(input, length):
    ''' remove-long:
    delete cell values where the string length is >= the specified number of characters
    ''' 
    if len(str(input))>length:
        return str(input)[:length]
    return input

def normalize_whitespace(input, tab=False):
    ''' normalize-whitespace:
    auto: replaces multiple consecutive whitespace characters by one space
    tab: replaces by one tab
    ''' 
    replacement=" "
    if tab:
        replacement="\t"
    return re.sub("\s{1,}", replacement, input)


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

def pad(input, length, text, where=start):
    ''' pad:
    the main argument is a length in number of characters
    text: what text to add, if the text is longer than one character 
    and the number of characters does not divide exactly then smartly choose 
    depending on whether it is on the start or the end 
    (other values or where are errors)
    ''' 
    if where not in [start, end]:
        raise ValueError("Only start and end are valid where values for pad")

    pad_length=length-len(str(input))
    if pad_length<1:
        return str(input)
    if len(text)>1 and pad_length%len(text):
        raise NotImplementedError("Still need to add support for not evenly divisible padding")
    pad_times=int(pad_length/len(text))
    padding=text*pad_times
    if where==start:
        return padding + str(input)
    if where==end:
        return str(input)+ padding



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
    strip_whitespace=strip_whitespace, #v
    remove_numbers=remove_numbers,
    remove_letters=remove_letters,
    remove_regex=remove_regex,
    truncate=truncate, #v
    normalize_whitespace=normalize_whitespace, #v
    change_case=change_case, #v
    pad=pad, #xv
    make_numeric=make_numeric,
    fix_url=fix_url
)


