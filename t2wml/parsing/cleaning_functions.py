import re

left="left"
right="right"
left_and_right="left-and-right"
everywhere="everywhere"


def strip_whitespace(input, char=None, where=left_and_right):
    if where == left:
        return str(input).lstrip(chars=char)
    if where == right:
        return str(input).rstrip(chars=char)
    if where == left_and_right:
        return str(input).strip(chars=char)
    if where == everywhere:
        return "".join(str(input).split(sep=char))

def remove_symbols( where=left):
    pass

def remove_unicodes( where=everywhere):
    pass

def remove_numbers( where=right):
    pass

def remove_letters( where=everywhere):
    pass

def remove_regex( where=left):
    pass

def remove_long():
    pass

def normalize_whitespace():
    pass

def replace_whitespace():
    pass

def change_case():
    pass

def pad( where=left):
    pass

def make_numeric():
    pass

def fix_url():
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