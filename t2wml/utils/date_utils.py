import warnings
import pandas
from datetime import datetime
try:
    from etk.wikidata.utils import parse_datetime_string
    has_etk = True
except (ImportError, OSError):
    has_etk = False
from t2wml.utils.debug_logging import basic_debug


parsed_date_cache={}


def translate_precision_to_integer(precision: str) -> int:
    """This function translates the precision value to indexes used by wikidata
    Args:
        precision (str): [description]

    Returns:
        int: wikidata index for precision
    """
    if isinstance(precision, int):
        return precision
    precision_map = {
        "gigayear": 0,
        "gigayears": 0,
        "100 megayears": 1,
        "100 megayear": 1,
        "10 megayears": 2,
        "10 megayear": 2,
        "megayears": 3,
        "megayear": 3,
        "100 kiloyears": 4,
        "100 kiloyear": 4,
        "10 kiloyears": 5,
        "10 kiloyear": 5,
        "millennium": 6,
        "century": 7,
        "10 years": 8,
        "10 year": 8,
        "years": 9,
        "year": 9,
        "months": 10,
        "month": 10,
        "days": 11,
        "day": 11,
        "hours": 12,
        "hour": 12,
        "minutes": 13,
        "minute": 13,
        "seconds": 14,
        "second": 14
    }
    return precision_map[precision.lower()]


#@basic_debug
def parse_datetime(value, additional_formats=None, precisions=None):
    """given a string, parse it to a datetime

    Args:
        value (str): date string
        additional_formats (str or list of str, optional): REQUIRED formats for the string to match one of them. Defaults to None.
        precision (string/int or list of same, optional): wikidata precision. Defaults to None.

    Raises:
        ValueError: Failed to parse datetime string with the provided format/s
        ValueError: No date / datetime detected

    Returns:
        string: datetime_string.isoformat()
        int (or None): precision
        str or None: format used
    """
    used_format=None
    additional_formats=additional_formats or []
    # check if additional formats is a string and convert to single entry array:
    if isinstance(additional_formats, str):
        additional_formats = [additional_formats]
    
    precision=None
    if precisions:
        if not isinstance(precisions, list):
            precision = translate_precision_to_integer(precisions)
    
    value = str(value)

    cache_key= value+str(additional_formats)

    if cache_key in parsed_date_cache:
        if isinstance(parsed_date_cache[cache_key], ValueError):
            raise parsed_date_cache[cache_key]
        return parsed_date_cache[cache_key]

    if additional_formats: #format/s have been specified. input MUST match a format
        datetime_string=False
        for index, date_format in enumerate(additional_formats):
            try:
                datetime_string = datetime.strptime(value, date_format)
                used_format=date_format
                if precisions and precision is None:
                    try:
                        precision=translate_precision_to_integer(precisions[index])
                    except IndexError: #no precision defined for that format
                        precision=None
                parsed_date_cache[cache_key] = datetime_string.isoformat(), precision, used_format
                return parsed_date_cache[cache_key]
            except ValueError as e:
                pass
        if not datetime_string:
            parsed_date_cache[cache_key] = ValueError("Failed to parse datetime string with the provided format/s")
            raise parsed_date_cache[cache_key]
    else: #no format specified. attempt to guess date
        if has_etk:
            # use this line to make etk stop harassing us with "no lang features detected" warnings
            with warnings.catch_warnings(record=True) as w:
                datetime_string, precision = parse_datetime_string(
                    value,
                    additional_formats=additional_formats,
                    prefer_language_date_order=False
                )
            if not precision: #only if user didn't hard-define a precision do we take from etk
                precision=int(precision.value.__str__())
            parsed_date_cache[cache_key] = datetime_string.isoformat(), precision, used_format
            return parsed_date_cache[cache_key]
        
        try:
            datetime_string = pandas.to_datetime(value, infer_datetime_format=True)
            parsed_date_cache[cache_key] = datetime_string.isoformat(), precision, used_format
            return parsed_date_cache[cache_key]
        except:
            parsed_date_cache[cache_key] = ValueError('No date / datetime detected')
            raise parsed_date_cache[cache_key]

