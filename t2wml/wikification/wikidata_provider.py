from abc import ABC, abstractmethod
from SPARQLWrapper import SPARQLWrapper, JSON
from t2wml.settings import t2wml_settings


class WikidataProvider(ABC):
    @abstractmethod
    def get_property_type(self, wikidata_property, *args, **kwargs):
        raise NotImplementedError

    def save_entry(self, property, data_type, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass


class SparqlProvider(WikidataProvider):
    '''
    Provides responses to queries purely from sparql. 
    Will fail if item/property not in wikidata
    '''

    def __init__(self, sparql_endpoint:str=None, *args, **kwargs):
        """[summary]
        Args:
            sparql_endpoint (str, optional): [description]. Defaults to None.
            If None, the sparql endpoint from t2wml_settings is used.
        """
        if sparql_endpoint is None:
            sparql_endpoint = t2wml_settings.sparql_endpoint
        self.sparql_endpoint = sparql_endpoint
        self.cache = {}

    def query_wikidata_for_property_type(self, wikidata_property):
        query = """SELECT ?type ?label ?desc WHERE {
                    wd:"""+wikidata_property+""" rdf:type wikibase:Property;
                        wikibase:propertyType ?type.
                    OPTIONAL { wd:"""+wikidata_property+""" rdfs:label ?label. }
                    OPTIONAL { wd:"""+wikidata_property+""" schema:description ?desc. }
                    FILTER(LANGMATCHES(LANG(?label), "EN"))
                    FILTER(LANGMATCHES(LANG(?desc), "EN"))
                    }"""
        sparql = SPARQLWrapper(self.sparql_endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        try:
            results_0=results["results"]["bindings"][0]
            data_type = results_0["type"]["value"].split("#")[1]
            label=results_0["label"]["value"]
            description=results_0["desc"]["value"]
        except IndexError:
            data_type = "Property Not Found"
            label=description=""
        return dict(data_type=data_type, label=label, description=description)

    def get_property_type(self, wikidata_property: str):
        data_type = self.cache.get(wikidata_property, False)
        if not data_type:
            data_type_args = self.query_wikidata_for_property_type(
                wikidata_property)
            data_type=data_type_args["data_type"]
            self.save_entry(wikidata_property, **data_type_args)
            if data_type == "Property Not Found":
                raise ValueError("Property "+wikidata_property+" not found")

        return data_type

    def save_entry(self, property, data_type, *args, **kwargs):
        self.cache[property] = data_type


class FallbackSparql(SparqlProvider):
    '''
    A class for querying some source, and if the source does not have a response to the query, 
    falling back to sparql queries (and then optionally saving query response to the main source)
    '''

    def get_property_type(self, wikidata_property, *args, **kwargs):
        try:
            data_type = self.try_get_property_type(
                wikidata_property, *args, **kwargs)
        except:
            data_type = super().get_property_type(wikidata_property)
        return data_type

    def try_get_property_type(self, wikidata_property, *args, **kwargs):
        raise NotImplementedError


class DictionaryProvider(SparqlProvider):
    def __init__(self, ref_dict, sparql_endpoint=None, *args, **kwargs):
        super().__init__(sparql_endpoint)
        self.cache = ref_dict
