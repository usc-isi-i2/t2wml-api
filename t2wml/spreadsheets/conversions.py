import re
from typing import Sequence, Union, Tuple, List, Dict, Any

regex_az = re.compile(r'[a-zA-Z]+')
regex_09 = re.compile(r'[0-9]+')

def cell_tuple_to_str(col, row) -> str:
    """
    used exclusively in conversions
    This function converts 0-indexed tuples cell notation
    to the cell notation used by excel (letter + 1-indexed number, in a string)
    Eg: (0,5) to A6, (51, 5) to AZ6
    """
    col = column_index_to_letter(col)
    row = str(int(row) + 1)
    return col + row


def cell_str_to_tuple(cell: str): #aka from excel
    """
    This function converts the cell notation used by excel (letter + 1-indexed number, in a string)
    to 0-indexed tuples cell notation 
    Eg:  A6 to 0,5
    """
    column = regex_az.search(cell).group(0)
    row = regex_09.search(cell).group(0)
    return column_letter_to_index(column), int(row)-1


def column_letter_to_index(column: str) -> int:
    """
    used exclusively in conversions
    This function converts a letter column to its respective 0-indexed column index
    viz. 'A' to 0
    'AZ' to 51

    Returns:
        int: column index
    """
    index = 0
    column = column.upper()
    column = column[::-1]
    for i in range(len(column)):
        index += ((ord(column[i]) % 65 + 1) * (26 ** i))
    return index - 1


def column_index_to_letter(n: int) -> str:
    """
    used elsewhere in the code
    This function converts the 0-indexed column index to column letter
    0 to A,
    51 to AZ, etc
    """
    string = ""
    n = n+1
    while n > 0:
        n, remainder = divmod(n-1, 26)
        string = chr(65 + remainder) + string
    return string


def cell_range_str_to_tuples(cell_range: str) -> Tuple[Sequence[int], Sequence[int]]:
    """
    used elsewhere in the code
    This function parses the cell range and returns 0-index row and column indices
    eg: A4:B5 to (0, 3), (1, 4)
    """
    cells = cell_range.split(":")
    start_cell = cell_str_to_tuple(cells[0])
    end_cell = cell_str_to_tuple(cells[1])
    return start_cell, end_cell


def to_excel(col, row):
    """onverts 0-indexed tuples cell notation
    to the cell notation used by excel (letter + 1-indexed number, in a string)
    Eg: (0,5) to A6, (51, 5) to AZ6"""
    if col is None and row is None:
        return None
    return cell_tuple_to_str(col, row)
