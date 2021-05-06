import warnings
import pandas
import logging
from datetime import datetime
try:
    from etk.wikidata.utils import parse_datetime_string
    has_etk = True
except (ImportError, OSError):
    has_etk = False

VALID_PROPERTY_TYPES=["globecoordinate", "quantity", "time", "string", "monolingualtext",
                        "externalid", "wikibaseitem", "wikibaseproperty", "url"]


def translate_precision_to_integer(precision: str) -> int:
    """
    This function translates the precision value to indexes used by wikidata
    :param precision:
    :return:
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



def parse_datetime(value, additional_formats=None, precisions=None):
    logging.debug("enter parse_datetime")
    used_format=None
    additional_formats=additional_formats or []
    precisions= precisions or []
    # check if additional formats is a string and convert to single entry array:
    if isinstance(additional_formats, str):
        additional_formats = [additional_formats]
    
    precision=None
    if precisions and isinstance(precisions, str):
        precision=translate_precision_to_integer(precisions)
    
    value = str(value)
    if additional_formats: #format/s have been specified. input MUST match a format
        datetime_string=False
        for index, date_format in enumerate(additional_formats):
            try:
                datetime_string = datetime.strptime(value, date_format)
                used_format=date_format
                if not precision:
                    try:
                        precision=translate_precision_to_integer(precisions[index])
                    except IndexError: #no precision defined for that format
                        precision=None
                logging.debug("returning from parse_datetime (if additional formats)")
                return datetime_string.isoformat(), precision, used_format
            except ValueError as e:
                pass
        if not datetime_string:
            logging.debug("raising error from parse_dateime (not datetime string)")
            raise ValueError("Failed to parse datetime string with the provided format/s")
    else: #no format specified. attempt to guess date
        if has_etk:
            logging.debug("enter parse_datetime's if has_etk")
            # use this line to make etk stop harassing us with "no lang features detected" warnings
            with warnings.catch_warnings(record=True) as w:
                datetime_string, precision = parse_datetime_string(
                    value,
                    additional_formats=additional_formats,
                    prefer_language_date_order=False
                )
            if not precision: #only if user didn't hard-define a precision do we take from etk
                precision=int(precision.value.__str__())
            logging.debug("returning from parse_datetime (if has etk)")
            return datetime_string, precision, used_format
        
        try:
            datetime_string = pandas.to_datetime(value, infer_datetime_format=True)
            logging.debug("returning from parse_datetime (default)")
            return datetime_string.isoformat(), precision, used_format
        except:
            logging.debug("raising error from parse_dateime (no date detected)")
            raise ValueError('No date / datetime detected')

