from pathlib import Path
import pandas as pd
from t2wml.utils.debug_logging import basic_debug

def post_process_data(data):
    return data
    #the below code was added to enable yaml conditional ==, in particular for issue #111
    #however, it creates performance issues on large files and may no longer be needed
    data = data.fillna("")
    data = data.replace(r'^\s+$', "", regex=True)
    return data

def load_pickle(pickle_path):
    data = pd.read_pickle(pickle_path)
    return post_process_data(data)

class PandasLoader:
    # a wrapper to centralize and make uniform any loading of data files/sheets from pandas
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_extension = Path(file_path).suffix.lower()
        self.is_excel = True if self.file_extension in [".xlsx", ".xls"] else False
        self.pd_args = dict(dtype=str, header=None)

    @basic_debug
    def load_sheet(self, sheet_name):
        """
        returns a single sheet's data frame
        """
        if self.is_excel:
            data = pd.read_excel(
                self.file_path, sheet_name=sheet_name, **self.pd_args)     
        else:
            if self.file_extension == ".csv":
                data = pd.read_csv(self.file_path, **self.pd_args)
            elif self.file_extension == ".tsv":
                data = pd.read_csv(self.file_path, sep="\t", **self.pd_args)
            else: #attempt to parse type using csv sniffer
                data = pd.read_table(self.file_path, sep=None, **self.pd_args)
        return post_process_data(data)
    
    @property
    def non_excel_sheet_name(self):
        return Path(self.file_path).name


    @basic_debug
    def load_file(self):
        """
        returns a dictionary of sheet_names and their data frames
        """
        if self.is_excel:
            return_dict = {}
            loaded_file = pd.read_excel(
                self.file_path, sheet_name=None, **self.pd_args)
            for sheet_name in loaded_file:
                data = loaded_file[sheet_name]
                data = post_process_data(data)
                return_dict[sheet_name] = data
            return return_dict
        else:
            data = self.load_sheet(None)
            sheet_name = self.non_excel_sheet_name
            return {sheet_name: data}


    @basic_debug
    def get_sheet_names(self):
        if self.is_excel:
            xl = pd.ExcelFile(self.file_path)
            return xl.sheet_names
        else:
            return [self.non_excel_sheet_name]
    



def get_first_sheet_name(file_path: str):
    """
    This function returns the first sheet name of the excel file
    :param file_path:
    :return:
    """
    pw = PandasLoader(file_path)
    return pw.get_sheet_names()[0]
