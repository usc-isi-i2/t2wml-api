#please note that template functions are documented pretty extensively in grammar.md

import re
from t2wml.utils.date_utils import parse_datetime
from SPARQLWrapper import SPARQLWrapper, JSON
from t2wml.utils.bindings import bindings
from t2wml.settings import t2wml_settings
from t2wml.parsing.classes import ReturnClass, RangeClass
from t2wml.parsing.cleaning_functions import string_modifier

def boolean_modifer(func): #uses OR, not AND, logic for determining true/false
    def wrapper(input, *args, **kwargs):
        if input:  # if value is not None
            if isinstance(input, RangeClass):  # handle ranges separately:
                for i, val in enumerate(input):
                    if val:
                        flag = func(input[i], *args, **kwargs)
                        if flag == True:
                            return True
                return False
            return func(input, *args, **kwargs)
        return False
    return wrapper


@boolean_modifer
def contains(input, section):
    return section in str(input)


@boolean_modifer
def starts_with(input, section):
    return str(input).startswith(section)


@boolean_modifer
def ends_with(input, section):
    return str(input).endswith(section)


@boolean_modifer
def instance_of(input, qnode):
    """send a query to the t2wml_settings sparql endpoint checking if input has an instance of relationship with qnode"""
    query = "ASK {wd:"+str(input)+" wdt:P31/wdt:P279* wd:" + str(qnode) + "}"
    sparql = SPARQLWrapper(t2wml_settings.sparql_endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results['boolean']








@string_modifier
def split_index(input, character, i):
    # split a cell on some character and return the i-th value
    # e.g., if D3 has “paul, susan, mike” then index(value(D/3), “,”, 3) returns mike
    # this is a primitive version of a much more sophisticated feature we need to add later to deal with
    # cells that contain lists.
    vals = str(input).split(character)
    return vals[i-1]  # 1-indexed to 0-indexed


@string_modifier
def substring(input, start, end=None):
    # 1-based indexing
    # substring("platypus", 3, 5) would be "aty" and substring(pirate, 2, -2) would return "irat"

    # adjust to 0-indexing
    if start < 0:
        start += 1
    else:
        start -= 1
    if end < 0:
        end += 1
    return str(input)[start-1:end]


@string_modifier
def extract_date(input, date_format):
    date_str, precision, used_format = parse_datetime(str(input),
                                         additional_formats=date_format)
    return date_str


@string_modifier
def regex(input, pattern, i=1):
    # extract a substring using a regex. The string is the regex and the result is the value of the first group in
    # the regex. If the regex contains no group, it is the match of the regex.
    # regex(value[], "regex") returns the first string that matches the whole regex
    # regex(value[]. regex, i) returns the value of group i in the regex
    # The reason for the group is that it allows more complex expressions. In our use case we could do a single expression as we cannot fetch more than one
    # common use case "oil production in 2017 in cambodia"
    match = re.search(pattern, input)
    if match:
        try:
            return match.group(i)
        except IndexError as e:
            if i==1:
                return match.group(0)
            raise e


def concat(*args):
    # concatenate a list of expression, e.g., concat(value(D, $row), “, “, value(F, $row))
    # ranges are concatenated in row-major order
    # the last argument is the separator
    # this is not a string modifier function. it does not change values in place, it creates a new return object
    sep = args[-1]
    args = args[:-1]
    return_str = ""
    for arg in args:
        if isinstance(arg, RangeClass):
            for thing in arg:
                if thing: #skip empty values
                    return_str += str(thing)
                    return_str += sep
        else:
            if arg:  # skip empty values:
                return_str += str(arg)
                return_str += sep

    # remove the last sep
    length = len(sep)
    return_str = return_str[:-length]

    r = ReturnClass(None, None, return_str)
    return r


def t_var_sheet_end():
    return bindings.excel_sheet.row_len


def t_var_sheet_name():
    return bindings.excel_sheet.name


def t_var_sheet_file_name():
    return bindings.excel_sheet.data_file_name


functions_dict = dict(
    contains=contains,
    starts_with=starts_with,
    ends_with=ends_with,
    instance_of=instance_of,
    split_index=split_index,
    substring=substring,
    extract_date=extract_date,
    regex=regex,
    concat=concat,
    t_var_sheet_end=t_var_sheet_end,
    t_var_sheet_name=t_var_sheet_name,
    t_var_sheet_file_name=t_var_sheet_file_name
)  