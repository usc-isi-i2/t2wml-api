from abc import ABC, abstractmethod
from SPARQLWrapper import SPARQLWrapper, JSON
from t2wml.settings import t2wml_settings
from t2wml.utils.debug_logging import basic_debug

class WikidataProvider(ABC):
    @abstractmethod
    def get_property_type(self, wikidata_property, *args, **kwargs):
        raise NotImplementedError

    def get_entity(self, id, *args, **kwargs):
        #default to returning a dict with the data_type
        property_type=self.get_property_type(id)
        return {"data_type":property_type}

    def save_entry(self, node_id, data_type=None, *args, **kwargs):
        pass

    def update_cache(self, update_dict):
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
        self.failed_sparql_queries=set()

    def query_wikidata_for_property_type(self, wikidata_property):
        failure_dict=dict(data_type = "Property Not Found",
                        label="",
                        description="")
        try:
            int(wikidata_property[1:])
        except:
            return failure_dict
        
        if wikidata_property in self.failed_sparql_queries:
            return failure_dict
        
        query = """SELECT ?label ?desc ?type
                WHERE 
                {{
                wd:{wpid} wikibase:propertyType ?type;
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en".
                        wd:{wpid} rdfs:label         ?label.
                        wd:{wpid} schema:description   ?desc.
                    }}
                }}
                """.format(wpid=wikidata_property)
        sparql = SPARQLWrapper(self.sparql_endpoint, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36')
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        try:
            results_0=results["results"]["bindings"][0]
            data_type = results_0["type"]["value"].split("#")[1]
            label=results_0["label"]["value"]
            description=results_0["desc"]["value"]
        except IndexError:
            self.failed_sparql_queries.add(wikidata_property)
            return failure_dict
        return dict(data_type=data_type, label=label, description=description)

    #@basic_debug
    def get_property_type(self, wikidata_id: str):
        property_args = self.cache.get(wikidata_id, False)
        if not property_args:
            property_args = self.query_wikidata_for_property_type(wikidata_id)
            self.save_entry(wikidata_id, **property_args)
        data_type=property_args["data_type"]    
        if data_type == "Property Not Found":
            raise ValueError("Property "+wikidata_id+" not found")
        return data_type
    
    def get_entity(self, id, *args, **kwargs):
        property_type=self.get_property_type(id) #trigger caching so we can just check cache
        return self.cache[id]

    def save_entry(self, node_id=None, data_type=None, label=None, description=None, *args, **kwargs):
        self.cache[node_id] = {"data_type":data_type}
        if label:
            self.cache[node_id]["label"]=label
        if description:
            self.cache[node_id]["description"]=label
    
    def update_cache(self, update_dict):
        self.cache.update(update_dict)


class FallbackSparql(SparqlProvider):
    '''
    A class for querying some source, and if the source does not have a response to the query, 
    falling back to sparql queries (and then optionally saving query response to the main source)
    '''

    #@basic_debug
    def get_property_type(self, wikidata_property, *args, **kwargs):
        try:
            data_type = self.try_get_property_type(
                wikidata_property, *args, **kwargs)
        except Exception as e:
            if self.sparql_endpoint== "DO NOT QUERY":
                raise e
            data_type = super().get_property_type(wikidata_property)
        return data_type

    def try_get_property_type(self, wikidata_property, *args, **kwargs):
        raise NotImplementedError


class DictionaryProvider(SparqlProvider):
    def __init__(self, ref_dict, sparql_endpoint=None, *args, **kwargs):
        super().__init__(sparql_endpoint)
        self.cache = ref_dict
    
class KGTKFileProvider():
    def __init__(self, file_path):
        from t2wml.wikification.utility_functions import kgtk_to_dict
        self.properties=kgtk_to_dict(file_path)

    def get_property_type(self, wikidata_property, *args, **kwargs):
        try:
            property_dict=self.properties[wikidata_property]
            return property_dict["data_type"]
        except KeyError:
            raise ValueError("Property "+wikidata_property+" not found")

    def get_entity(self, wikidata_property, *args, **kwargs):
        try:
            property_dict=self.properties[wikidata_property]
            return property_dict
        except KeyError:
            raise ValueError("Property "+wikidata_property+" not found")

    def save_entry(self, node_id, data_type=None, *args, **kwargs):
        self.properties[node_id]=dict(kwargs)
        self.properties[node_id]["data_type"]=data_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass