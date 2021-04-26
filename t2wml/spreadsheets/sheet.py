from pathlib import Path
import pandas as pd
import json
from t2wml.settings import t2wml_settings
from t2wml.spreadsheets.utilities import PandasLoader
from t2wml.spreadsheets.caching import PickleCacher, FakeCacher
from t2wml.spreadsheets.conversions import to_excel
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from collections.abc import Mapping
from io import StringIO

def get_cache_class():
    cache_class = FakeCacher
    if t2wml_settings.cache_data_files:
        cache_class = PickleCacher
    return cache_class


class SpreadsheetFile(Mapping):
    """ A mapping class (immutable dict) for accessing sheets within a single file.
    All immutable dict methods are available (access by key, iteration, len, etc)
    Keys are sheet names, values are initialized Sheet instances.
    """
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
            cache_class = get_cache_class()
            sc = cache_class(data_file_path, sheet_name)
            self.raw_data = sc.get_sheet()
    
    @property
    def data(self):
        if self.cleaned_data is not None:
            return self.cleaned_data
        return self.raw_data

    def __getitem__(self, params):
        try:
            return self.data.iloc[params]
        except IndexError:
            raise T2WMLExceptions.CellOutsideofBoundsException(
                "Cell " + to_excel(params[1], params[0]) + " is outside the bounds of the current data file")

    @property
    def row_len(self):
        return self.data.shape[0]

    @property
    def col_len(self):
        return self.data.shape[1]
    
    def to_json(self):
        if self.cleaned_data is not None:
            cleaned=json.loads(self.cleaned_data.to_json(orient='values'))
        else:
            cleaned=None
        return dict(cleaned=cleaned, 
                    data=json.loads(self.data.to_json(orient='values')),
                    data_file_path=self.data_file_path, 
                    sheet_name=self.name)

    @staticmethod
    def from_json(in_json):
        cleaned=in_json.pop("cleaned")
        if cleaned:
            cleaned=pd.DataFrame(cleaned)
        data=in_json.pop("data")
        if data:
            data=pd.DataFrame(data)
        s=Sheet(data=data, **in_json)
        s.cleaned_data=cleaned
        return s

    @classmethod
    def load_sheet_from_csv_string(cls, csv_string, data_file_path="", sheet_name=""):
        df=pd.read_csv(StringIO(csv_string))
        return cls(data_file_path=data_file_path, sheet_name=sheet_name, data=df)

