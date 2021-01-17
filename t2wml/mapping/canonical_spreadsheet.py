import csv
from io import StringIO

def try_get_label(input):
    return input



def create_canonical_spreadsheet(statements):
    column_titles=["main_subject", "variable", "value"]

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
            elif key=="subject":
                statement_dict["main_subject"]=try_get_label(statement[key])
            elif key=="property":
                statement_dict["variable"]=try_get_label(statement[key])
            elif key=="unit":
                if key not in column_titles:
                    column_titles.append(key)
                statement_dict[key]=try_get_label(statement[key])
            elif key=="value":
                statement_dict[key]=try_get_label(statement[key])
        dict_values.append(statement_dict)
    
    string_stream = StringIO("", newline="")

    writer = csv.DictWriter(string_stream, column_titles,
                            restval="", lineterminator="\n",
                            escapechar='', quotechar='',
                            dialect=csv.unix_dialect, quoting=csv.QUOTE_NONE)
    writer.writeheader()
    for entry in dict_values:
        writer.writerow(entry)

    output = string_stream.getvalue()
    string_stream.close()
    return output


