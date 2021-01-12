import csv

def try_get_label(input):
    return input



def create_canonical_spreadsheet(statements):
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
    
    with open(r'C:\Users\devora\C_sources\pedro\names.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=column_titles)
        writer.writeheader()
        for statement_dict in dict_values:
            writer.writerow(statement_dict)



