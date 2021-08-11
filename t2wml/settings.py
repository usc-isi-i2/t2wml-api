import os
# DEFAULT_SPARQL_ENDPOINT ='https://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql'
DEFAULT_SPARQL_ENDPOINT= 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'

class T2WMLSettings:
    def __init__(self):
        self.sparql_endpoint=DEFAULT_SPARQL_ENDPOINT
        self.wikidata_provider=None #default is DictionaryProvider with preloaded properties
        self.warn_for_empty_cells=False
        self.handle_calendar="leave"
        self.no_wikification=False

    def update_from_dict(self, **kwargs):
        for key in self.__dict__:
            if key in kwargs:
                self.__dict__[key]=kwargs[key]

t2wml_settings=T2WMLSettings()

