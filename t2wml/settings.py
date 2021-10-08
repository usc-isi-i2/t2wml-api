import os
# DEFAULT_SPARQL_ENDPOINT ='https://dsbox02.isi.edu:8888/bigdata/namespace/wdq/sparql'
DEFAULT_SPARQL_ENDPOINT= 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'

class T2WMLSettings:
    """like utils.bindings, this is a class that is made globally accesible and used in many places for calculations.
    It is therefore highly likely to be problematic in a multi-user server and an alternative should be found

    Attributes:
        sparql_endpoint (str): endpoint used to make sparql queries to get property type. note that with pre-cached properties this is less relevant
        wikidata_provider (WikidataProvider): instance of class to be used to query property type.
        warn_for_empty_cells (bool): block coordinate dictionary. taken from dictionary and then "normalized" (relabeled as necessary so that x1, y1 coordinates are upper left and x2, y2 lower right)
        handle_calendar (str): when receiving a non-Gregorian calendar, should the statement generator: a. "leave" the original value as-is b. "replace" the value with the gregorian value c. "add" the gregorian as an additional dictionary
        no_wikification (bool): treat item[] cells as value[], and do not run property validation
    """
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

