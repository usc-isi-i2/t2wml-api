import json
from collections import defaultdict
import pandas as pd
from t2wml.utils.t2wml_exceptions import ItemNotFoundException
from t2wml.utils.debug_logging import basic_debug




class ItemTable:
    def __init__(self, lookup_table = None):
        lookup_table = lookup_table or {}
        self.lookup_table = defaultdict(dict, lookup_table)

    def lookup_func(self, context, column, row, value):
        lookup = self.lookup_table.get(context)
        if not lookup:
            raise ItemNotFoundException(
                "Search for cell item failed. (No values defined for context: {})".format(context))

        key = (column, row, value)
        try:
            return lookup[key]
        except KeyError:
             raise ItemNotFoundException(str(key)+ " not found")

    def get_item(self, column:int, row:int, sheet=None, context:str='', value=None):
        if value is None:
            value = str(sheet[row, column])
        try:
            item = self.lookup_func(context, column, row, value)
            return item
        except ItemNotFoundException:
            return None  # currently this is what the rest of the API expects. could change later

    def get_cell_info(self, column, row, sheet):
        # used to serialize table
        value = str(sheet[row, column])
        for context in self.lookup_table:
            item = self.get_item(column, row, sheet, context=context, value=value)
            if item:
                return item, context, value
        return None, None, None


class Wikifier:
    def __init__(self, lookup_table = None, filepath = None):
        self.item_table = ItemTable(lookup_table)
        self.filepath= filepath
    
    @property
    def lookup_table(self):
        return self.item_table.lookup_table

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
                self.lookup_table.get(context).pop((col, row, value), None)
    
    def add_or_replace(self, replace, context, col, row, value, item):
        if not replace:
            if (col, row, value) in self.lookup_table.get(context, {}):
                return
        self.lookup_table[context][(col, row, value)] = item


    
    def add_wikification(self, item, selection, value, context:str='', replace=True):
        (row1, col1), (row2, col2) = selection
        for row in range(row1, row2+1):
            for col in range(col1, col2+1):
                self.add_or_replace(replace, context, col, row, value, item)
    

    def update_from_dict(self, wiki_dict, replace=True):
        for context in wiki_dict:
            if isinstance(wiki_dict[context], list): #backwards compatible
                for (col, row, value), item in wiki_dict[context]:
                    self.add_or_replace(replace, context, col, row, value, item)

            else:
                for (col, row, value), item in wiki_dict[context].items():
                    self.add_or_replace(replace, context, col, row, value, item)
    
    def add_dataframe(self, df, replace=True): #TODO: replace all instances
        wiki_dict=convert_old_df_to_dict(df)
        self.update_from_dict(wiki_dict, replace)

    def add_file(self, filepath, replace=True): #TODO: replace?
        df = pd.read_csv(filepath)
        self.add_dataframe(df, replace)

    @classmethod
    def load_from_file(cls, filepath):
        with open(filepath, 'r', encoding="utf-8") as f:
            itemized_dict = json.load(f)
            lookup_table=dict()
            for context in itemized_dict:
                try:
                    arr = itemized_dict[context]
                    lookup_table[context]={tuple(entry[0]): entry[1] for entry in arr}
                except Exception as e:
                    raise e
        return cls(lookup_table, filepath)
    
    def save_to_file(self, filepath=None):
        if not filepath:
            filepath= self.filepath
        if not filepath:
            return
        with open(filepath, 'w', encoding="utf-8") as f:
            itemized_dict = {key: list(self.lookup_table[key].items()) for key in self.lookup_table}
            f.write(json.dumps(itemized_dict))


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
    wiki_dict=defaultdict(dict)
    for entry in df.itertuples():
        column = int(entry.column)
        row = int(entry.row)
        value = str(entry.value)
        context = entry.context or ""
        if str(context) == "nan":
            context=""
        item = entry.item
        wiki_dict[context][(column, row, value)] = item
    return wiki_dict

