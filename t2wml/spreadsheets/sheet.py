from pathlib import Path
import pandas as pd   
from t2wml.spreadsheets.utilities import PandasLoader, post_process_data
from t2wml.spreadsheets.conversions import to_excel
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from collections.abc import Mapping
from io import StringIO
from t2wml.utils.debug_logging import basic_debug


class SpreadsheetFile(Mapping):
    """ A mapping class (immutable dict) for accessing sheets within a single file.
    All immutable dict methods are available (access by key, iteration, len, etc)
    Keys are sheet names, values are initialized Sheet instances.
    """
    #@basic_debug
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.dict = {}
        pandas_loader = PandasLoader(file_path)
        pandas_data = pandas_loader.load_file()
        for sheet_name in pandas_data:
            self.dict[sheet_name] = Sheet(
                self.file_path, sheet_name, pandas_data[sheet_name])

    @property
    def sheet_names(self):
        return list(self.dict.keys())

    def __iter__(self):
        return iter(self.dict)

    def __getitem__(self, sheet_name):
        return self.dict[sheet_name]

    def __len__(self):
        return len(self.dict)


class Sheet:
    # all access to spreadsheet goes through here
    #@basic_debug
    def __init__(self, data_file_path: str, sheet_name: str, data=None):
        """[summary]

        Args:
            data_file_path (str): location of sheet file
            sheet_name (str): name of sheet. for csv files, name of sheet file
            data (dataframe, optional): dataframe of contents of sheet. For creating a sheet from already loaded data.
                                        Defaults to None.
        """
        self.data_file_path = str(data_file_path)
        self.data_file_name = Path(data_file_path).name
        self.name = sheet_name

        self.cleaned_data=None #this is set from outside the class, if cleaning is run

        if data is not None:
            self.raw_data = data
        else:
            self.raw_data = PandasLoader(self.data_file_path).load_sheet(self.name)
    
    @property
    def data(self):
        if self.cleaned_data is not None:
            return self.cleaned_data
        return self.raw_data
    
    @property
    def _data_values(self): #added this property because creating .values takes too long
        if self.cleaned_data is not None:
            try:
                return self._cleaned_data_values
            except:
                self._cleaned_data_values = self.cleaned_data.values
                return self._cleaned_data_values
        else:
            try:
                return self._raw_data_values
            except:
                self._raw_data_values = self.raw_data.values
                return self._raw_data_values


    def __getitem__(self, params):
        try:
            return self._data_values[params]
        except IndexError:
            raise T2WMLExceptions.CellOutsideofBoundsException(
                "Cell " + to_excel(params[1], params[0]) + " is outside the bounds of the current data file")
    
    @property
    def row_len(self): 
        # number of rows
        return self.data.shape[0]

    @property
    def col_len(self):
        # number of columns
        return self.data.shape[1]

    @classmethod
    def load_sheet_from_csv_string(cls, csv_string, data_file_path="", sheet_name="", **pandas_options):
        #convenience method, especially for tests
        df=pd.read_csv(StringIO(csv_string), **pandas_options)
        df=post_process_data(df)
        return cls(data_file_path=data_file_path, sheet_name=sheet_name, data=df)

