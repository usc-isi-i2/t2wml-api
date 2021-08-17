import json
import pandas as pd
from t2wml.utils.t2wml_exceptions import ItemNotFoundException
from t2wml.utils.bindings import bindings
from t2wml.utils.debug_logging import basic_debug


class ItemTable:
    def __init__(self, lookup_table = None):
        self.lookup_table = lookup_table or {}

    def lookup_func(self, context, column, row, value):
        key = str((column, row, value, context))
        try:
            return self.lookup_table[key]
        except KeyError:
             raise ItemNotFoundException("Not found")

    def get_item(self, column:int, row:int, context:str='', sheet=None, value=None):
        if not sheet:
            sheet = bindings.excel_sheet
        if value is None:
            value = str(sheet[row, column])
        try:
            item = self.lookup_func(context, column, row, value)
            return item
        except ItemNotFoundException:
            return None  # currently this is what the rest of the API expects. could change later

    def get_cell_info(self, col, row, sheet): #this will be replaced soon
        value = str(sheet[row, col])
        item = self.get_item(col, row, '', value=value)
        return item, '', value


class Wikifier:
    def __init__(self, lookup_table = None, filepath = None):
        self.lookup_table = lookup_table or {}
        self.filepath= filepath
    
    @property
    def item_table(self):
        return ItemTable(self.lookup_table)

    def delete_wikification(self, selection, value=None, context:str='', sheet=None):
        [[col1, row1], [col2, row2]] = selection #the range is 0-indexed [[col, row], [col, row]]
        if value is None and sheet is None:
            raise ValueError("for deletion, must specify value or sheet")
        if value is not None:
            sheet=None
        for row in range(row1, row2+1):
            for col in range(col1, col2+1):
                if sheet:
                    value = sheet[row, col]
                self.lookup_table.pop(str((col, row, value, context)), None)
    
    def add_wikification(self, item, selection, value, context:str='', replace=True):
        (row1, col1), (row2, col2) = selection
        for row in range(row1, row2+1):
            for col in range(col1, col2+1):
                if replace:
                    self.lookup_table[str((col, row, value, context))] = item
                else:
                    try:
                        self.lookup_table[str((col, row, value, context))]
                    except KeyError:
                        self.lookup_table[str((col, row, value, context))] = item
    

    def update_from_dict(self, wiki_dict, replace=False):
        for key in wiki_dict:
            if replace:
                self.lookup_table[key]=wiki_dict[key]
            else:
                try: 
                    self.lookup_table[key]
                except KeyError:
                    self.lookup_table[key]=wiki_dict[key]
    
    def add_dataframe(self, df): #TODO: replace all instances
        wiki_dict=convert_old_df_to_dict(df)
        self.update_from_dict(wiki_dict)

    def add_file(self, filepath): #TODO: replace?
        df = pd.read_csv(filepath)
        self.add_dataframe(df)



    @classmethod
    def load_from_file(cls, filepath):
        with open(filepath, 'r', encoding="utf-8") as f:
            lookup_table = json.load(f)
        return cls(lookup_table, filepath)
    
    def save_to_file(self, filepath=None):
        if not filepath:
            filepath= self.filepath
        if not filepath:
            return
        with open(filepath, 'w', encoding="utf-8") as f:
            f.write(json.dumps(self.lookup_table))


def convert_old_wikifier_to_new(wikifier_file, sheet):
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
    new_wiki_dict = convert_old_df_to_dict(new_df)
    return new_wiki_dict
        

        
    
def convert_old_df_to_dict(df):
    wiki_dict={}
    for entry in df.itertuples():
        column = entry.column
        row = entry.row
        value = str(entry.value)
        context = entry.context or ""
        if str(context) == "nan":
            context=""
        item = entry.item
        wiki_dict[str((column, row, value, context))] = item
    return wiki_dict

