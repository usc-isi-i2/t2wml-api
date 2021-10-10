# bindings represents information used by classes/functions available in the t2wml parser
# This class is HIGHLY PROBLEMATIC for multi-user systems. It should be combined with T2WMLSettings, 
# and some method of passing along both to the parser without using a global function needs to be implemented

class BindingsClass:
    def __init__(self):
        self.item_table = None
        self.excel_sheet = None


bindings = BindingsClass()


def update_bindings(sheet=None, item_table=None) -> None:
    """updates the bindings dictionary with the excel_file and item table
    """
    if sheet:
        bindings.excel_sheet = sheet
    if item_table:
        bindings.item_table = item_table
