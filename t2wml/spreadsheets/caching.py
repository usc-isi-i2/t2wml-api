import os
from pathlib import Path
import pandas as pd
from t2wml.spreadsheets.utilities import PandasLoader
from t2wml.settings import t2wml_settings

class FakeCacher:
    def __init__(self, data_file_path, sheet_name):
        self.data_file_path = data_file_path
        self.sheet_name = sheet_name
        self.pandas_wrapper = PandasLoader(self.data_file_path)

    def get_sheet(self):
        return self.pandas_wrapper.load_sheet(self.sheet_name)


class PickleCacher:
    def __init__(self, data_file_path, sheet_name):
        self.data_file_path = data_file_path
        self.sheet_name = sheet_name
        self.pandas_wrapper = PandasLoader(self.data_file_path)
        if not self.pickle_folder.is_dir():
            os.makedirs(self.pickle_folder)

    @property
    def pickle_folder(self):
        storage_folder=Path(t2wml_settings.cache_data_files_folder)
        parts = Path(self.data_file_path).parts
        parts=parts[1:-1]
        underscored="_".join(parts)
        folder_path = storage_folder/underscored
        return folder_path

    @property
    def pickle_file(self):
        path = Path(self.data_file_path)
        filename = path.stem+"_"+self.sheet_name+".pkl"
        return str(self.pickle_folder/filename)

    def fresh_pickle(self):
        # checks if the pickle is "fresh"-- is more newly modified than the datafile
        if os.path.isfile(self.pickle_file):
            if os.path.getmtime(self.pickle_file) > os.path.getmtime(self.data_file_path):
                return True
        return False

    def get_sheet(self):
        if self.fresh_pickle():
            data = self.pandas_wrapper.load_pickle(self.pickle_file)
        else:
            # if not, load the sheet, save the pickle file for future use
            data = self.pandas_wrapper.load_sheet(self.sheet_name)
            self.save_pickle(data)
        return data

    def save_pickle(self, data):
        pd.to_pickle(data, self.pickle_file)
