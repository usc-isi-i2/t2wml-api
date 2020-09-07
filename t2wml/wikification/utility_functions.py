from collections import defaultdict
import json
import csv
from pathlib import Path
from t2wml.utils.utilities import VALID_PROPERTY_TYPES
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
from t2wml.utils import t2wml_exceptions as T2WMLExceptions
from t2wml.wikification.wikidata_provider import SparqlProvider
from t2wml.settings import t2wml_settings


def get_provider():
    wikidata_provider = t2wml_settings.wikidata_provider
    if wikidata_provider is None:
        wikidata_provider = SparqlProvider(t2wml_settings.sparql_endpoint)
        t2wml_settings.wikidata_provider = wikidata_provider
    return wikidata_provider


def get_property_type(prop):
    try:
        prop_type = _get_property_type(prop)
        return str(prop_type).lower()
    except QueryBadFormed:
        raise T2WMLExceptions.MissingWikidataEntryException(
            "The value given for property is not a valid property:" + str(prop))
    except ValueError:
        raise T2WMLExceptions.MissingWikidataEntryException(
            "Property not found:" + str(prop))


def _get_property_type(wikidata_property):
    provider = get_provider()
    property_type = provider.get_property_type(wikidata_property)
    if property_type == "Property Not Found":
        raise ValueError("Property "+wikidata_property+" not found")
    return property_type


def add_nodes_from_file(file_path: str):
    """load wikidata entries from a file and add them to the current WikidataProvider as defined in settings.
    If a kgtk-format tsv file, the property information will be loaded as follows:
    node1 is used as the wikidata_id. 
    each wikidata ID has a dictionary, as follows:
    label is used as keys, for "data_type", "label", "description", and "P31". 
    (note: rows with a label not in those 4 are not added to provider by default 
    (users could write custom provider with support))
    node2 is used for the value for that row's key, eg "Quantity", "Area(HA)", etc

    Args:
        file_path (str): location of the properties file

    Raises:
        ValueError: invalid filetype (only tsv files are supported)

    Returns:
        dict: a dictionary of "added", "present" (already present, updated), and "failed" properties from the file
    """
    if Path(file_path).suffix != ".tsv":
        raise ValueError(
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
                if data_type: #validate data types
                    if str(data_type.lower()) not in VALID_PROPERTY_TYPES:
                        raise ValueError("Property type: " +data_type+" not supported")
                added = p.save_entry(node_id, data_type, **prop_info)
                if added:
                    return_dict["added"].append(node_id)
                else:
                    return_dict["updated"].append(node_id)
            except Exception as e:
                print(e)
                return_dict["failed"].append((node_id, str(e)))
    return return_dict
