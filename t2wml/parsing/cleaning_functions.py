import re
import ftfy as FTFY
from t2wml.parsing.classes import ReturnClass, RangeClass


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
    def wrapper(input, *args, **kwargs):
        where=kwargs.get("where")
        if where:
            if where not in [start, end, start_and_end, everywhere]:
                raise ValueError("Invalid argument for where: "+where)
        if input:  # if value is None, don't modify
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

@string_modifier
def ftfy(input):
    return FTFY.fix_text(input)

@string_modifier
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

@string_modifier
def replace_regex(input, regex, replacement="", count=0):
    input=re.sub(regex, replacement, input, count)
    return input

@string_modifier
def remove_numbers(input, where=everywhere):
    regex="\d*"
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
def wip_remove_letters(input, where=everywhere):
    regex= "[a-zA-Z]"
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
    if len(str(input))>length:
        return str(input)[:length]
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
    return re.sub("\s{1,}", replacement, input)

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
        return str(input).capitalize()
    if case=="lower":
        return str(input).lower()
    if case=="upper":
        return str(input).upper()
    if case=="title":
        return str(input).title()

@string_modifier
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
    if not len(input): #don't pad empty strings
        return input

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

@string_modifier
def make_numeric(input, decimal=".", latex=False):
    '''make-numeric:
    auto: smart function to make the values of a cell numeric
    remove leading and trailing non-numeric characters
    interprets commas and dots smartly
    removes whitespace inside the number
    interprets exponential notation
    ''' 
    
    original_input=str(input)
    if decimal!=".":
        input=input.replace(decimal, ".")
    re.sub("[^\d.|^\de\d|-]", "", input)
    try:
        input=float(input)
    except:
        print("Failed to make numeric: "+original_input)
        return original_input
    return str(input)

@string_modifier
def make_alphanumeric(input):
    return ''.join(e for e in input if e.isalnum())

@string_modifier
def make_ascii(input, convert=False):
    if convert:
        pass
    else:
        pass

cleaning_functions_dict=dict(
    ftfy=ftfy,
    strip_whitespace=strip_whitespace, #v
    remove_numbers=remove_numbers,
    #remove_letters=remove_letters,
    replace_regex=replace_regex,
    truncate=truncate, #v
    normalize_whitespace=normalize_whitespace, #v
    change_case=change_case, #v
    pad=pad, #TODO: uneven padding
    make_numeric=make_numeric,
    #make_alphanumeric=make_alphanumeric,
    #make_ascii=make_ascii,

)


