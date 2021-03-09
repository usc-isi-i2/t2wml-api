import json
from t2wml.wikification.utility_functions import dict_to_kgtk

def create_kgtk_from_sparql_query_saved_as_json(query_path, output_path):
    with open(query_path, 'r', encoding="utf-8") as f:
        properties = json.load(f)
    properties_dict={}
    for property in properties:
        id=property["id"]
        properties_dict[id]=dict(label=property["itemLabel"],
                                description=property.get("itemDescription", ""),
                                data_type=property["data_type"])
    dict_to_kgtk(properties_dict, output_path)

def query_sparql_for_all_properties():
    query_str="""SELECT DISTINCT (?item as ?id) ?itemLabel ?itemDescription (?type as ?data_type)
                WHERE
                {
                ?item wdt:P31/wdt:P279* wd:Q18616576;
                        wikibase:propertyType ?type;
                SERVICE wikibase:label { bd:serviceParam wikibase:language "en".}
                }"""