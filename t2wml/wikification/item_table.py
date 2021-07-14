import json
import pandas as pd
from pandas import DataFrame
from collections import defaultdict
from t2wml.utils.t2wml_exceptions import ItemNotFoundException
from t2wml.utils.bindings import bindings
from t2wml.utils.debug_logging import basic_debug


class OldItemTable:
    def __init__(self, lookup_table={}):
        self.lookup_table = defaultdict(dict, lookup_table)

    def lookup_func(self, context, file, sheet, column, row, value):
        lookup = self.lookup_table.get(context)
        if not lookup:
            raise ItemNotFoundException(
                "Search for cell item failed. (No values defined for context: {})".format(context))

        # order of priority: cell+value> cell> col+value> col> row+value> row> value
        column = int(column)
        row = int(row)
        tuples = [
            (file, sheet, column, row, value),
            (file, sheet, '', '', value),
            ('', '', column, row, value),
            ('', '', column, row, ''),
            ('', '', column, '', value),
            ('', '', column, '', ''),
            ('', '', '', row, value),
            ('', '', '', row, ''),
            ('', '', '', '', value)
        ]

        for tup in tuples:
            item = lookup.get(str(tup))
            if item:
                return item

        raise ValueError("Not found")

    @basic_debug
    def get_item(self, column:int, row:int, context:str='', sheet=None, value=None):
        if not sheet:
            sheet = bindings.excel_sheet
        file=sheet.data_file_name
        sheet_name=sheet.name
        if value is None:
            value = str(sheet[row, column])
        try:
            item = self.lookup_func(context, file, sheet_name, column, row, value)
            return item
        except ValueError:
            return None  # currently this is what the rest of the API expects. could change later
        #   raise ItemNotFoundException("Item for cell "+to_excel(column, row)+"("+value+")"+"with context "+context+" not found")

    @basic_debug
    def get_item_by_string(self, value: str, context:str=''):
        lookup = self.lookup_table.get(context)
        if not lookup:
            raise ItemNotFoundException(
                "Search for cell item failed. (No values defined for context: {})".format(context))

        item = lookup.get(str(('', '', '', '', value)))
        if item:
            return item
        raise ItemNotFoundException("Could not find item for value: "+value)

    def get_cell_info(self, column, row, sheet):
        # used to serialize table
        bindings.excel_sheet = sheet
        for context in self.lookup_table:
            value= bindings.excel_sheet[row, column]
            item = self.get_item(column, row, context, sheet=sheet, value=value)
            if item:
                return item, context, value
        return None, None, None

    @basic_debug
    def update_table_from_dataframe(self, df: DataFrame):
            df = df.fillna('')
            df = df.replace(r'^\s+$', '', regex=True)
            overwritten = {}
            for entry in df.itertuples():
                column = entry.column
                row = entry.row
                value = str(entry.value)
                context = entry.context
                item = entry.item
                try:
                    file = entry.file
                    sheet= entry.sheet
                except:
                    file=sheet="" #backwards compatible for now

                if not item:
                    raise ValueError("Item definition missing")

                if column=="" and row=="" and value=="":
                    raise ValueError(
                        "at least one of column, row, or value must be defined")

                if column != "":
                    column = int(column)
                if row != "":
                    row = int(row)
                key = str((file, sheet, column, row, value))
                if self.lookup_table[context].get(key):
                    overwritten[key] = self.lookup_table[context][key]
                self.lookup_table[context][key] = item

            if len(overwritten):
                pass #print(f"Wikifier update overwrote {len(overwritten)} existing values")
            return overwritten


class ItemTable:
    def __init__(self, lookup_table={}):
        self.lookup_table = defaultdict(dict, lookup_table)

    def lookup_func(self, context, file, sheet, column, row, value):
        lookup = self.lookup_table.get(context)
        if not lookup:
            raise ItemNotFoundException(
                "Search for cell item failed. (No values defined for context: {})".format(context))

        key = str((file, sheet, column, row, value))
        try:
            return lookup[key]
        except KeyError:
             raise ItemNotFoundException("Not found")
    
    @basic_debug
    def get_item(self, column:int, row:int, context:str='', sheet=None, value=None):
        if not sheet:
            sheet = bindings.excel_sheet
        file=sheet.data_file_name
        sheet_name=sheet.name
        if value is None:
            value = str(sheet[row, column])
        try:
            item = self.lookup_func(context, file, sheet_name, column, row, value)
            return item
        except ItemNotFoundException:
            return None  # currently this is what the rest of the API expects. could change later
        #   raise ItemNotFoundException("Item for cell "+to_excel(column, row)+"("+value+")"+"with context "+context+" not found")

    
    def get_item_by_string(self, value: str, context:str=''):
        raise ValueError("get_item_by_string has been deprecated, if you need to use the old item table use OldItemTable")
    
    def get_cell_info(self, column, row, sheet):
        # used to serialize table
        bindings.excel_sheet = sheet
        for context in self.lookup_table:
            value= bindings.excel_sheet[row, column]
            item = self.get_item(column, row, context, sheet=sheet, value=value)
            if item:
                return item, context, value
        return None, None, None
    
    @basic_debug
    def update_table_from_dataframe(self, df: DataFrame):
            df = df.fillna('')
            df = df.replace(r'^\s+$', '', regex=True)
            overwritten = {}
            for entry in df.itertuples():
                column = entry.column
                row = entry.row
                value = str(entry.value)
                context = entry.context
                item = entry.item
                try:
                    file = entry.file
                    sheet= entry.sheet
                except:
                    raise ValueError("Missing file and sheet. If you are trying to use the old \
                    ItemTable, you will need to use OldItemTable")

                if (column=="" or row=="" or value=="" or file=="" or sheet==""):
                    raise ValueError("All of the fields: column, row, file, sheet, value are required \
                        if you meant to use the old item table, use OldItemTable")
                if not item:
                    raise ValueError("missing item id")


                column = int(column)
                row = int(row)
                key = str((file, sheet, column, row, value))
                if self.lookup_table[context].get(key):
                    overwritten[key] = self.lookup_table[context][key]
                self.lookup_table[context][key] = item

            if len(overwritten):
                pass #print(f"Wikifier update overwrote {len(overwritten)} existing values")
            return overwritten



class Wikifier:
    def __init__(self):
        self.wiki_files = []
        self._data_frames = []
        self._item_table = ItemTable()

    @property
    def item_table(self):
        return self._item_table

    @basic_debug
    def add_file(self, file_path: str):
        """add a wikifier file to the wikifier. loads the file and adds it to the item table.
        file must be a csv file, and must contain the columns 'row', 'column', 'value', 'context', 'item'
        (columns may be empty)

        Args:
            file_path (str): location of the wikifier file

        Raises:
            ValueError: if the wikifier file fails to apply

        Returns:
            dict: a dictionary describing which item definitions were already present and overwritten
        """
        df = pd.read_csv(file_path)
        try:
            overwritten = self.item_table.update_table_from_dataframe(df)
        except Exception as e:
            raise ValueError(
                "Could not apply {} : {}".format(file_path, str(e)))
        self.wiki_files.append(file_path)
        self._data_frames.append(df)
        return overwritten

    @basic_debug
    def add_dataframe(self, df: DataFrame):
        """Add a wikifier dataframe to the Wikifier item table

        Args:
            df (DataFrame): a dataframe with columns 'row', 'column', 'value', 'context', 'item'        
            (columns may be empty)

        Raises:
            ValueError: not all columns defined
            ValueError: could not apply dataframe

        Returns:
            dict: a dictionary describing which item definitions were already present and overwritten
        """
        expected_columns = set(['row', 'column', 'value', 'context', 'item', "sheet", "file"])
        columns = set(df.columns)
        missing_columns = expected_columns.difference(columns)
        if len(missing_columns):
            raise ValueError(
                "Dataframe for wikifier must contain all 7 expected columns")
        try:
            overwritten = self.item_table.update_table_from_dataframe(df)
        except Exception as e:
            raise ValueError("Could not apply dataframe: "+str(e))
        self._data_frames.append(df)
        return overwritten

    @basic_debug
    def save(self, filename: str):
        """save Wikifier to a json file

        Args:
            filename (str): location of save file
        """
        output = json.dumps({
            "wiki_files": self.wiki_files,
            "lookup_table": self.item_table.lookup_table,
            "dataframes": [df.to_json() for df in self._data_frames]
        })
        with open(filename, 'w', encoding="utf-8") as f:
            f.write(output)

    @classmethod
    @basic_debug
    def load(cls, filename:str):
        """load Wikifier from saved json file (created by the wikifier save method)

        Args:
            filename (str): location of save file

        Returns:
            Wikifier: initialized wikifier
        """
        with open(filename, 'r', encoding="utf-8") as f:
            wiki_args = json.load(f)
        wikifier = Wikifier()
        wikifier.wiki_files = wiki_args["wiki_files"]
        wikifier._item_table = ItemTable(
            lookup_table=wiki_args["lookup_table"])
        wikifier._data_frames = [pd.read_json(
            json_string) for json_string in wiki_args["dataframes"]]
        return wikifier



def convert_old_wikifier_to_new(wikifier_file, sheet, out_file=None):
    df = pd.read_csv(wikifier_file)
    df = df.fillna('')
    df = df.replace(r'^\s+$', '', regex=True)
    new_rows=[]
    columns=['row', 'column', 'value', 'context', 'item', "sheet", "file"]
    for entry in df.itertuples():
            column = entry.column
            row = entry.row
            value = str(entry.value)
            context = entry.context or ""
            item = entry.item
            
            if not item:
                raise ValueError("missing item")
            
            if column:
                column=int(column)
            if row:
                row=int(row)
            
            if column!="" and row!="" and value!="":
                new_rows.append([row, column, value, context, item, sheet.name, sheet.data_file_name])
                continue

            if not value:
                if (column=="" and row==""):
                    raise ValueError("cannot leave row and column and value all unspecified")
                try:
                    value = sheet[row, column]
                    new_rows.append([row, column, value, context, item, sheet.name, sheet.data_file_name])
                except:
                    pass #print("row+col outside of sheet bounds, skipping")
                continue
            
            if (column=="" and row==""):
                for r in range(sheet.row_len):
                    for c in range(sheet.col_len):
                        if sheet[r, c] == value:
                            new_rows.append([r, c, value, context, item, sheet.name, sheet.data_file_name])
                continue
            
            if row!="":
                for c in range(sheet.col_len):
                    if sheet[row, c] ==  value:
                        new_rows.append([row, c, value, context, item, sheet.name, sheet.data_file_name])
                continue

            if column!="":
                for r in range(sheet.row_len):
                    if sheet[r, column] ==  value:
                        new_rows.append([r, column, value, context, item, sheet.name, sheet.data_file_name])
                continue

            


    new_df = pd.DataFrame(new_rows, columns=columns)
    if out_file:
        new_df.to_csv(out_file, index=False)
    return new_df
        

        
    


