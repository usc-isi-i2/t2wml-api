# DEFAULT_SPARQL_ENDPOINT ='https://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql'
DEFAULT_SPARQL_ENDPOINT= 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'

class T2WMLSettings:
    def __init__(self):
        self.cache_data_files_folder=None
        self.sparql_endpoint=DEFAULT_SPARQL_ENDPOINT
        self.wikidata_provider=None #default is DictionaryProvider with preloaded properties
        self.warn_for_empty_cells=False
    @property
    def cache_data_files(self):
        if self.cache_data_files_folder:
            return True
        return False


t2wml_settings=T2WMLSettings()

