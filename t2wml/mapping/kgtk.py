
import csv
from io import StringIO
from pathlib import Path
from t2wml.mapping.datamart_edges import (clean_id, create_metadata_for_custom_qnode, create_metadata_for_project, create_metadata_for_variable, 
                create_metadata_for_qualifier_property, link_statement_to_dataset)
from t2wml.utils.utilities import VALID_PROPERTY_TYPES
import t2wml.utils.t2wml_exceptions as T2WMLExceptions
from t2wml.wikification.utility_functions import get_property_type
from t2wml.wikification.utility_functions import kgtk_to_dict

class EmptyValueException(Exception):
    pass

def enclose_in_quotes(value):
    if value != "" and value is not None:
        return "\""+str(value.replace('"','\\"'))+"\""
    return ""


def kgtk_add_property_type_specific_fields(property_dict, result_dict):
    property_type = get_property_type(property_dict["property"])

    if property_type not in VALID_PROPERTY_TYPES:
        raise T2WMLExceptions.UnsupportedPropertyType(
                "Property type "+property_type+" is not currently supported" + "(" + property_dict["property"] + ")")


    # The only property that doesn't require value
    if property_type == "globecoordinate":
        '''
        node2;kgtk:latitude: for coordinates, the latitude
        node2;kgtk:longitude: for coordinates, the longitude
        '''
        result_dict["node2;kgtk:data_type"] = "location_coordinates"
        result_dict["node2;kgtk:latitude"] = property_dict["latitude"]
        result_dict["node2;kgtk:longitude"] = property_dict["longitude"]
        result_dict["node2;kgtk:precision"] = property_dict.get(
            "precision", "")
        result_dict["node2;kgtk:globe"] = property_dict.get("globe", "")

    else:
        try:
            value = property_dict["value"]
            result_dict["node2"] = value
        except:
            raise EmptyValueException(f'Cell {property_dict["cell"]} has no value')

        if property_type == "quantity":
            '''
            node2;kgtk:magnitude: for quantities, the number
            node2;kgtk:units_node: for quantities, the unit
            node2;kgtk:low_tolerance: for quantities, the lower bound of the value (cannot do it in T2WML yet)
            node2;kgtk:high_tolerance: for quantities, the upper bound of the value (cannot do it in T2WML yet)
            '''
            result_dict["node2;kgtk:data_type"] = "quantity"
            result_dict["node2;kgtk:number"] = value
            result_dict["node2;kgtk:units_node"] = property_dict.get(
                "unit", "")
            result_dict["node2;kgtk:low_tolerance"] = property_dict.get(
                "lower-bound", "")
            result_dict["node2;kgtk:high_tolerance"] = property_dict.get(
                "upper-bound", "")

        elif property_type == "time":
            '''
            node2;kgtk:date_and_time: for dates, the ISO-formatted data
            node2;kgtk:precision: for dates, the precision, as an integer (need to verify this with KGTK folks, could be that we use human readable strings such as year, month
            node2;kgtk:calendar: for dates, the qnode of the calendar, if specified
            '''
            result_dict["node2;kgtk:data_type"] = "date_and_times"
            result_dict["node2;kgtk:date_and_time"] = enclose_in_quotes(value)
            result_dict["node2;kgtk:precision"] = property_dict.get(
                "precision", "")
            result_dict["node2;kgtk:calendar"] = property_dict.get(
                "calendar", "")

        elif property_type in ["string", "monolingualtext", "externalid", "url"]:
            '''
            node2;kgtk:text: for text, the text without the language tag
            node2;kgtk:language: for text, the language tag
            '''
            result_dict["node2;kgtk:data_type"] = "string"
            result_dict["node2;kgtk:text"] = enclose_in_quotes(value)
            result_dict["node2;kgtk:language"] = enclose_in_quotes(
                property_dict.get("lang", ""))

        elif property_type in ["wikibaseitem", "wikibaseproperty"]:
            '''
            node2;kgtk:symbol: when node2 is another item, the item goes here"
            '''
            result_dict["node2;kgtk:data_type"] = "symbol"
            result_dict["node2;kgtk:symbol"] = value


def handle_additional_edges(project, statements):
    tsv_data=[]
    tsv_data+=create_metadata_for_project(project)
    variable_ids=set()
    qualifier_ids=set(["P585", "P248"])
    qnode_ids=set()
    entity_dict={}
    for file in project.entity_files:
        full_path=project.get_full_path(file)
        entity_dict.update(kgtk_to_dict(full_path))

    for cell, statement in statements.items():
        variable=statement["property"]
        if variable not in variable_ids:
            variable_ids.add(variable)
            variable_dict=entity_dict.get(variable, None)
            if variable_dict is not None:
                label=variable_dict.get("label", "A "+variable)
                description=variable_dict.get("description", variable+" relation")
                data_type=variable_dict.get("data_type", "quantity")
                if data_type.lower()=="wikibaseitem":
                    qnode_ids.add(statement["value"])
                tags=variable_dict.get("tags", [])
                #TODO: P31?
                tsv_data+=create_metadata_for_variable(project, variable, label, description, data_type, tags)

        qualifiers=statement.get("qualifier", [])
        for qualifier in qualifiers:
            property=qualifier["property"]
            if property not in qualifier_ids:
                qualifier_ids.add(property)
                variable_dict=entity_dict.get(property, {})
                if True:# variable_dict is not None:
                    label=variable_dict.get("label", "A "+property)
                    #description=variable_dict.get("description", variable+" relation")
                    data_type=variable_dict.get("data_type", "string")
                    if data_type.lower()=="wikibaseitem":
                        qnode_ids.add(qualifier["value"])
                    tsv_data+=create_metadata_for_qualifier_property(project, variable, property, label, data_type)
        
        subject=statement["subject"]
        if subject not in qnode_ids:
            qnode_ids.add(subject)
            #TODO
    
    for qnode_id in qnode_ids:
        variable_dict=entity_dict.get(qnode_id, {})
        if variable_dict:
            label=variable_dict.get("label", qnode_id)
            tsv_data+=create_metadata_for_custom_qnode(qnode_id, label)

    for result_dict in tsv_data:
        property_type=result_dict.pop("type")
        result_dict["node2;kgtk:data_type"]=property_type
        value=result_dict["node2"]

        if property_type == "quantity":
            result_dict["node2;kgtk:number"] = value

        elif property_type == "date_and_times":
            result_dict["node2;kgtk:date_and_time"] = enclose_in_quotes(value)

        elif property_type == "string":
            result_dict["node2;kgtk:text"] = enclose_in_quotes(value)

        elif property_type == "symbol":
            result_dict["node2;kgtk:symbol"] = value
    return tsv_data


def create_kgtk(statements, file_path, sheet_name, project=None):
    file_name = Path(file_path).name

    file_extension = Path(file_path).suffix
    if file_extension == ".csv":
        sheet_name = ""
    else:
        sheet_name = "."+sheet_name

    tsv_data = []

    if project:
        tsv_data+=handle_additional_edges(project, statements)

    for cell, statement in statements.items():
        try:
            id = file_name + sheet_name + ";" + cell

            if project:
                tsv_data.append(link_statement_to_dataset(project, id))

            cell_result_dict = dict(
                id=id, node1=statement["subject"], label=statement["property"])
            kgtk_add_property_type_specific_fields(statement, cell_result_dict)
            tsv_data.append(cell_result_dict)

            qualifiers = statement.get("qualifier", [])
            for qualifier in qualifiers:
                qualifier_result_dict = dict(id=id+"-"+qualifier["property"],
                    node1=id, label=qualifier["property"])

                try:
                    kgtk_add_property_type_specific_fields(
                        qualifier, qualifier_result_dict)
                    tsv_data.append(qualifier_result_dict)
                except EmptyValueException:
                    # Allow missing qualifier values
                    pass


            references = statement.get("reference", [])
            # todo: handle references
        except Exception as e:
            raise(e)

    string_stream = StringIO("", newline="")
    fieldnames = ["id", "node1", "label", "node2", "node2;kgtk:data_type",
                  "node2;kgtk:number", "node2;kgtk:low_tolerance", "node2;kgtk:high_tolerance", "node2;kgtk:units_node",
                  "node2;kgtk:date_and_time", "node2;kgtk:precision", "node2;kgtk:calendar",
                  "node2;kgtk:truth",
                  "node2;kgtk:symbol",
                  "node2;kgtk:latitude", "node2;kgtk:longitude", "node2;kgtk:globe",
                  "node2;kgtk:text", "node2;kgtk:language", ]

    writer = csv.DictWriter(string_stream, fieldnames,
                            restval="", delimiter="\t", lineterminator="\n",
                            escapechar='', quotechar='',
                            dialect=csv.unix_dialect, quoting=csv.QUOTE_NONE)
    writer.writeheader()
    for entry in tsv_data:
        writer.writerow(entry)

    output = string_stream.getvalue()
    string_stream.close()
    return output

def get_all_variables(project, statements, validate_for_datamart=False):
    tsv_data=[]
    tsv_data+=create_metadata_for_project(project)
    variable_set=set()
    variable_ids=set()
    entity_dict={}
    for file in project.entity_files:
        full_path=project.get_full_path(file)
        entity_dict.update(kgtk_to_dict(full_path))

    for cell, statement in statements.items():
        variable=statement["property"]
        property_type = get_property_type(variable)
        if validate_for_datamart:
            if property_type!="quantity":
                raise T2WMLExceptions.InvalidDatamartVariables("A valid datamart variable must be of type quantity")
        if variable not in variable_set:
            variable_set.add(variable)
            variable_dict=entity_dict.get(variable, None)
            if variable_dict is not None:
                label=variable_dict.get("label", variable)
                variable_id=clean_id(label)
                variable_ids.add(variable_id)
    return variable_ids