from collections import defaultdict
import json
import csv
from pathlib import Path
from t2wml.input_processing.utils import VALID_PROPERTY_TYPES
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
from t2wml.utils import t2wml_exceptions as T2WMLExceptions
from t2wml.wikification.wikidata_provider import DictionaryProvider
from t2wml.settings import t2wml_settings
from t2wml.utils.debug_logging import basic_debug


def get_default_provider():
    from t2wml.wikification.preloaded_properties import preloaded_properties
    wikidata_provider = DictionaryProvider(preloaded_properties)
    return wikidata_provider

#@basic_debug
def get_provider():
    """get current provider or default"""
    wikidata_provider = t2wml_settings.wikidata_provider
    if wikidata_provider is None:
        wikidata_provider = get_default_provider()
        t2wml_settings.wikidata_provider = wikidata_provider
    return wikidata_provider

#@basic_debug
def get_property_type(prop):
    try:
        provider = get_provider()
        prop_type = provider.get_property_type(prop)
        if prop_type == "Property Not Found":
            raise T2WMLExceptions.UnsupportedPropertyType("Property "+prop+" not found")
        return str(prop_type).lower()
    except QueryBadFormed:
        raise T2WMLExceptions.UnsupportedPropertyType(
            "The value given for property is not a valid property:" + str(prop))
    except ValueError:
        raise T2WMLExceptions.UnsupportedPropertyType(
            "Property not found:" + str(prop))


def validate_id(node_id):
    first_letter=str(node_id).upper()[0]
    if first_letter not in ["P", "Q"]:
        raise T2WMLExceptions.InvalidEntityDefinition("Only entity IDs beginning with P or Q are supported: "+str(node_id))
    try:
        num=int(node_id[1:])
        if first_letter=="P" and num<10000:
            raise T2WMLExceptions.InvalidEntityDefinition("Custom entity ID Pnum where num<10000 is not allowed: "+str(node_id))
        if first_letter=="Q" and num<1000000000:
            raise T2WMLExceptions.InvalidEntityDefinition("Custom entity ID Qnum where num<1 billion is not allowed: "+str(node_id))
    except ValueError: #conversion to int failed, is not Pnum or Qnum
        pass

#@basic_debug
def kgtk_to_dict(file_path):
    """loads kgtk file with entities and converts to entity dict

    Args:
        file_path (str): file to load

    Returns:
        dict: entity dict loaded from file
    """

    input_dict=defaultdict(dict)
    input_dict["filepath"]=dict(node1="", node2="", value=file_path)
    with open(file_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row_dict in reader:
            node1 = row_dict["node1"]
            label = row_dict["label"]
            value = row_dict["node2"]
            
            #if label is P2010050001 (datamart tag), the key is tags and a dict is generated
            if label == "P2010050001":
                if ":" in value:
                    key, val = value.split(":", 1)
                    try:
                        input_dict[node1]["tags"][key]=val
                    except KeyError:
                        input_dict[node1]["tags"]={key:val}
                else: 
                    print("malformed tag: ", value)

            else:
                input_dict[node1][label]=value
    return dict(input_dict)

#@basic_debug
def dict_to_kgtk(in_dict, out_path):
    """converts dictionary of entities to kgtk file and saves to file

    Args:
        in_dict (dict): entity dictionary
        out_path (string): file path to save to
    """
    tsv_dict_columns=["id", "node1", "label", "node2"]
    tsv_dict_arr=[]
    in_dict.pop("filepath", None)
    for node1, node_dict in in_dict.items():
        for label, value in node_dict.items():
            if label=="tags":
                tag_dict=value
                for index, tag_key in enumerate(tag_dict):
                    tag= tag_key + ":" + tag_dict[tag_key]
                    tsv_dict_arr.append(dict(node1=node1, label="P2010050001", node2=tag, id=f'{node1}-{label}-{index}'))
            else:
                tsv_dict_arr.append(dict(node1=node1, label=label, node2=value, id=f'{node1}-{label}'))
    with open(out_path, 'w', encoding="utf-8") as f:
        dw= csv.DictWriter(f, tsv_dict_columns,
                            restval="", delimiter="\t", lineterminator="\n",
                            escapechar='', quotechar='',
                            dialect=csv.unix_dialect, quoting=csv.QUOTE_NONE)
        dw.writeheader()
        for line in tsv_dict_arr:
            dw.writerow(line)


#@basic_debug
def add_entities_from_file(file_path: str, validate_ids=True):
    """load wikidata entries from a file and add them to the current WikidataProvider as defined in settings.
    If a kgtk-format tsv file, the property information will be loaded as follows:
    node1 is used as the wikidata_id.
    wikidata_id must be valid: Must begin with P or Q, Pnum where num<10000 or Qnum where num<1 billion are not allowed.
    each wikidata ID has a dictionary, as follows:
    label is used as keys, for "data_type", "label", "description", and "P31".
    (note: rows with a label not in those 4 are not added to provider by default
    (users could write custom provider with support))
    node2 is used for the value for that row's key, eg "Quantity", "Area(HA)", etc

    Args:
        file_path (str): location of the properties file
        validate_ids (bool): When true, only ids of form Pnum/Qnum will be allowed, and only with numbers greater than 10 thousand/1 billion

    Raises:
        UnsupportedPropertyType: invalid filetype (only tsv files are supported)
        InvalidEntityDefinition: if the id is invalid

    Returns:
        dict: a dictionary of "added", "present" (already present, updated), and "failed" properties from the file
    """
    if Path(file_path).suffix != ".tsv":
        raise T2WMLExceptions.UnsupportedPropertyType(
            "Only .tsv property files are currently supported")

    input_dict=defaultdict(dict)
    with open(file_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row_dict in reader:
            node1 = row_dict["node1"]
            label = row_dict["label"]
            value = row_dict["node2"]
            input_dict[node1][label]=value

    return_dict = {"added": [], "updated": [], "failed": []}

    provider = get_provider()
    with provider as p:
        for node_id in input_dict:
            prop_info = input_dict[node_id]
            data_type = prop_info.pop("data_type", None) #we pop it because it's passed as a required argument for historical reasons

            try:
                #validate ID
                if validate_ids:
                    validate_id(node_id)

                #validate data types
                if data_type:
                    if str(data_type.lower()) not in VALID_PROPERTY_TYPES:
                        raise T2WMLExceptions.InvalidEntityDefinition("Property type: " +data_type+" not supported")

                #attempt to add definition
                added = p.save_entry(node_id, data_type, from_file=True, **prop_info)
                if added:
                    return_dict["added"].append(node_id)
                else:
                    return_dict["updated"].append(node_id)
            except Exception as e:
                return_dict["failed"].append((node_id, str(e)))
    return return_dict