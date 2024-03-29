#please note that cleaning functions are documented pretty extensively in grammar.md

import math
import re
import string
import ftfy as FTFY
from t2wml.parsing.classes import ReturnClass, RangeClass
from text_unidecode import unidecode
from string import digits

non_numeric_beginning = re.compile(r"^[^\d.-]*")
non_numeric_ending = re.compile(r"[^\d.]*$")
regex_normalize_whitespace = re.compile(r"\s{1,}")
remove_digits = str.maketrans('', '', digits)

'''
start: apply the operator starting at the beginning of the value and stop when it can no longer be applied, e.g., remove numbers and stop when a non-number is found
end: apply the operator from the end end of the value
start-and-end: apply if both on the start and the end
everywhere: start on the start and keep applying the operator after skipping the characters where it does not apply, e.g., remove all numbers in a value regardless of where they appear
'''

start="start"
end="end"
start_and_end="start_and_end"
everywhere="everywhere"

def string_modifier(func):
    """wrapper function for handling different kinds of inputs (range, str, cell) and standardizing output properly"""
    def wrapper(input, *args, **kwargs):
        where=kwargs.get("where")
        if where:
            if where not in [start, end, start_and_end, everywhere]:
                raise ValueError("Invalid argument for where: "+where)

        if input is not None:  # if value is None, don't modify
            if isinstance(input, RangeClass):  # handle ranges separately:
                for i, val in enumerate(input):
                    if val:
                        input[i] = func(str(input[i]), *args, **kwargs)
            res_string = func(str(input), *args, **kwargs)
            
            try:
                input.value = res_string
                return input
            except:
                return res_string
        return input
    return wrapper

@string_modifier
def ftfy(input):
    """ Uses the ftfy package to clean the input"""
    return FTFY.fix_text(input)

@string_modifier
def strip_whitespace(input, char=None, where=start_and_end):
    """Remove whitespace. By default will remove all whitespace, 
    but if char argument (" " or "\t") is provided, will only remove that."""
    if where == everywhere:
        return "".join(input.split(sep=char))
    if where == start:
        return input.lstrip(char)
    if where == end:
        return input.rstrip(char)
    if where == start_and_end:
        return input.strip(char)

@string_modifier
def replace_regex(input, to_replace, replacement="", count=0):
    """will use to_replace as a regex argument to re.sub"""
    input=re.sub(to_replace, replacement, input, count)
    return input

@string_modifier
def remove_numbers(input, where=everywhere):
    if where==everywhere:
        return input.translate(remove_digits).strip()
    if where==start_and_end:
        return input.strip('0123456789.-').strip()
    if where==start:
        return input.lstrip('0123456789.-').strip()
    if where==end:
        return input.rstrip('0123456789.-').strip()
    return input

@string_modifier
def remove_letters(input, where=everywhere):
    """removes anything that matches the '\D' regex (anything not a digit) from start, end, start and end, or everywhere."""
    regex=r"\D*"
    if where==everywhere:
        input= re.sub(str(regex), "", input)
    if where==start or where==start_and_end:
        sub_string="^"+str(regex)
        input= re.sub(sub_string, "", input)
    if where==end or where ==start_and_end:
        sub_string=str(regex)+"$"
        input= re.sub(sub_string, "", input)
    return input

@string_modifier
def truncate(input, length):
    ''' remove-long:
    delete cell values where the string length is >= the specified number of characters
    ''' 
    if len(input)>length:
        return input[:length]
    return input

@string_modifier
def normalize_whitespace(input, tab=False):
    ''' normalize-whitespace:
    auto: replaces multiple consecutive whitespace characters by one space
    tab: replaces by one tab
    ''' 
    replacement=" "
    if tab:
        replacement="\t"
    return regex_normalize_whitespace.sub(replacement, input)

@string_modifier
def change_case(input, case="sentence"):
    ''' change-case:
    auto: changes the case to sentence case
    sentence
    lower
    upper
    title
    ''' 
    if case=="sentence":
        return input.capitalize()
    if case=="lower":
        return input.lower()
    if case=="upper":
        return input.upper()
    if case=="title":
        return input.title()

@string_modifier
def pad(input, length, pad_text, where=start):
    ''' pad:
    the main argument is a length in number of characters
    text: what text to add, if the text is longer than one character 
    and the number of characters does not divide exactly then smartly choose 
    depending on whether it is on the start or the end 
    (other values or where are errors)
    ''' 
    pad_text=str(pad_text)
    if where not in [start, end]:
        raise ValueError("Only start and end are valid where values for pad")
    if not len(input): #don't pad empty strings
        return input

    pad_length=length-len(input)
    

    if pad_length<1: #input longer than/equal to pad length, don't pad
        return input
    
    pad_times=math.ceil(pad_length/len(pad_text))
    pad_rem=pad_length%len(pad_text)
    padding=pad_text*pad_times
    if len(pad_text)>1 and pad_rem:
        if where == end:
            padding = padding[pad_rem:]
        if where == start:
            padding=padding[:-pad_rem]
    if where == start:
        return padding + input
    if where == end:
        return input+ padding


@string_modifier
def strict_make_numeric(input, decimal="."):
    """a variant of make_numeric that returns an empty cell if it cannot be easily converted to a number
    (so, for example, it will not strip alphabetic character to help force number conversion"""
    try:
        float(input) #don't bother with the rest if it converts to a number fine
        return str(input).strip()
    except:
        pass #continue to the processing
    input=strip_whitespace(str(input), where="everywhere")
    if decimal!=".":
        input=input.replace(".", "")
        input=input.replace(decimal, ".")
    input=input.replace(",", "")
    try:
        float(input)
    except:
        return "" #if it's not numeric, return an empty cell
    return input

@string_modifier
def make_numeric(input, decimal=".", latex=False):
    '''make-numeric:
    auto: smart function to make the values of a cell numeric
    remove leading and trailing non-numeric characters. 
        * leaves - in front and . in front and end
        * non-numeric characters in the middle are not removed, so 10e5 still works, 
        and something like 1dsjf3d4 wouldn't parse
    interprets commas and dots smartly
    removes whitespace inside the number

    ''' 
    try:
        float(input) #don't bother with the rest if it converts to a number fine
        return str(input).strip()
    except:
        pass #continue to the processing
    original_input=str(input)
    input=strip_whitespace(str(input), where="everywhere")
    if decimal!=".":
        input=input.replace(".", "")
        input=input.replace(decimal, ".")
    input=input.replace(",", "")
    input = non_numeric_beginning.sub("", input)
    input = non_numeric_ending.sub("", input)
    try:
        float(input)
    except:
        return "" #if it's not numeric, return an empty cell
    return input

@string_modifier
def make_alphanumeric(input):
    return ''.join(e for e in input if e.isalnum())

@string_modifier
def make_ascii(input, translate=False):
    """either removes all non-ascii non-printable characters 
    or, if translate=true,  uses text-unidecode to translate to closest equivalent"""
    if translate:
        return unidecode(input)
    else:
        #remove non-printable ascii as well
        return ''.join(filter(lambda x: x in string.printable, input))

@string_modifier
def fill_empty(input, replacement):
    """ if a cell is empty (contains only whitespace characters or an empty string), fill it with `replacement`. """
    if "".join(input.split())=="":
        return replacement
    return input


cleaning_functions_dict=dict(
    ftfy=ftfy, #v
    strip_whitespace=strip_whitespace, #v
    remove_numbers=remove_numbers, #v
    remove_letters=remove_letters, #v confirm definition
    replace_regex=replace_regex, #v
    truncate=truncate, #v
    normalize_whitespace=normalize_whitespace, #v
    change_case=change_case, #v
    pad=pad, #v
    make_numeric=make_numeric, #v may want to add additional support
    make_alphanumeric=make_alphanumeric, #v confirm definition
    make_ascii=make_ascii, #v confirm definition
    fill_empty=fill_empty, #v
)

