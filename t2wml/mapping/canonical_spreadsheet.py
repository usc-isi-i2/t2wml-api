import csv
from io import StringIO
from t2wml.wikification.utility_functions import get_provider

provider = get_provider()

def try_get_label(input):
    if input is None:
        return None
    if input[0] in ["P", "Q"]:
        try:
            entry = provider.get_entity(input)
            if entry and 'label' in entry:
                return entry['label']
        except:
            pass
    return input

def get_cells_and_columns(statements):
    column_titles=["subject", "property", "value"]

    dict_values=[]
    for cell, statement in statements.items():
        statement_dict={}
        for key in statement:
            if key == "cells":
                continue
            if key == "qualifier":
                for i, qualifier in enumerate(statement["qualifier"]):
                    qual_property=try_get_label(qualifier["property"])
                    if qual_property not in column_titles:
                        column_titles.append(qual_property)
                    statement_dict[qual_property]=qualifier["value"]
                    unit=qualifier.get("unit")
                    if unit:
                        unit_heading= qual_property + " unit"
                        if unit_heading not in column_titles:
                            column_titles.append(unit_heading)
                        statement_dict[unit_heading]=qualifier["unit"]
            elif key in ["subject", "property", "value", "unit"]:
                if key not in column_titles:
                    column_titles.append(key)
                statement_dict[key]=try_get_label(statement[key])
        dict_values.append(statement_dict)
    return column_titles, dict_values



def create_canonical_spreadsheet(statements):
    column_titles, dict_values = get_cells_and_columns(statements)
    
    string_stream = StringIO("", newline="")
    writer = csv.DictWriter(string_stream, column_titles,
                             restval="", 
                             lineterminator="\n",
                             escapechar="", 
                             #quotechar='',
                             dialect=csv.unix_dialect, 
                             #quoting=csv.QUOTE_NONE
                             )
    writer.writeheader()
    for entry in dict_values:
        writer.writerow(entry)

    output = string_stream.getvalue()
    string_stream.close()
    return output


