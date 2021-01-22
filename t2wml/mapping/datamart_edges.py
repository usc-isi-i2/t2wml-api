
import re
import datetime

#translate from lower-case (case insensitive) OR from wikidata standard OR for full uppercase URL, to wikidata standard
wikidata_sparql_to_wikidata = {
"globecoordinate": 'GlobeCoordinate',
"quantity": 'Quantity',
"time": 'Time',
"string": 'String',
"monolingualtext":'MonolingualText',
"externalidentifier":'ExternalIdentifier',
"wikibaseitem":'WikibaseItem',
"wikibaseproperty":'WikibaseProperty',
"url":'Url',
"GlobeCoordinate": 'GlobeCoordinate',
"Quantity": 'Quantity',
"Time": 'Time',
"String": 'String',
"MonolingualText":'MonolingualText',
"ExternalIdentifier":'ExternalIdentifier',
"WikibaseItem":'WikibaseItem',
"WikibaseProperty":'WikibaseProperty',
"Url":'Url',
"URL":"Url"
}

#translate from wikidata standard to datamart
wikidata_to_datamart = {
'GlobeCoordinate': 'location',
'Quantity': 'quantity',
'Time': 'date_and_time',
'String': 'string',
'MonolingualText': 'string',
'ExternalIdentifier': 'symbol',
'WikibaseItem': 'symbol',
'WikibaseProperty': 'symbol',
'Url': 'symbol',
}


def clean_id(input):
    '''
    remove non alphanumeric characters and lowercase
    replace whitespace by _ (underscore)
    '''
    input = re.sub(r'[^A-Za-z0-9\s]+', '', input)
    input = re.sub("\s", "_", input)
    return input




def create_metadata_for_project(project):
    def get_edge(node1, label, node2, type):
        #id = node1-label (no serial number)
        return dict(node1=node1, label=label, node2=node2, type=type, id=f'{node1}-{label}')

    dataset_id=clean_id(project.title)
    dataset_qnode = "Q"+dataset_id
    timestamp=datetime.datetime.utcnow()

    metadata = [
        #no needs for serial number as there's only one edge each
        get_edge(node1=dataset_qnode, label="P31", node2="Q1172284", type="symbol"), # this is a dataset
        get_edge(node1=dataset_qnode, label="P1813", node2=project.title, type="string"), # this is its name that we expose
        get_edge(node1=dataset_qnode, label="label", node2=project.title, type="string"), # an informative label
        get_edge(node1=dataset_qnode, label="P1476", node2=project.title, type="string"), # a title, same as label
        get_edge(node1=dataset_qnode, label="description", node2=project.description, type="string"), # a description
        get_edge(node1=dataset_qnode, label="P2699", node2=project.url, type="string"), #source url for dataset
        get_edge(node1=dataset_qnode, label="P5017", node2=timestamp, type="date_and_time") #last update date, in YYYY-mm-DDTHH:mm format
    ]

    return metadata


def create_metadata_for_variable(project, property_id, label, description, data_type):
    '''
    Unlike datasets, which only have the dataset definition metadata described above, 
    variables have both metadata defining them and their qualifiers, and data.

    Like datasets, variables have an id (which is a Qnode), and a name which is exposed to Datamart users. 
    In addition, variables have property ids, which are Pnodes.

    Variables also have qualifiers. 
    In datamart all variables must have at least two qualifiers:
    P585 - point_in_time (since Datamart only handles time-series)
    P248 (stated_in). 
    Datamart cannot display data from variables that do not have these two qualifiers.

    Additional qualifiers may be added to each variable.

    Variables also have tags. 
    Tags are strings that are, by convention, formatted A:B with A being the tag name and B being the tag value. 
    Datamart does not enforce this convention, but does use it when retrieving data 
    (you can query variables that have A:B, or A:C, or even A:*)

    '''
    dataset_Qnode=f'Q-{clean_id(project.title)}'
    Pnode = f'P{property_id}'
    Qnode = f'Q{property_id}'

    def get_Q_edge(node1, label, node2, type):
        #id = datasetQnode-variableQnode-node1-label
        return dict(node1=node1, label=label, node2=node2, type=type, id=f'{dataset_Qnode}-{Qnode}-{node1}-{label}')
    
    
    
    def get_P_edge(node1, label, node2, type):
        # id = node1-label
        # Note that the property edge IDs do not have the dataset in them, 
        # that’s because properties should be shared between datasets. 
        # If we want properties not be shared, we need to add the dataset name to their node1, not just the ID.
        return dict(node1=node1, label=label, node2=node2, type=type, id=f'{node1}-{label}')

    edges=[
        #The following edges describe the variable metadata in Datamart
        dict(id=f'QWGI-P2006020003-{dataset_Qnode}-{Qnode}', node1=dataset_Qnode, label="P2006020003", node2=Qnode, type="symbol") #the <dataset_id> dataset has the <Qnode> variable
        get_Q_edge(node1=Qnode, label="P2006020004", node2=dataset_id, type="symbol"), # the dataset of <Qnode> variable is <dataset_id> dataset
        get_Q_edge(node1=Qnode, label="P31", node2="Q50701", type="symbol"), #<Qnode> is a variable
        get_Q_edge(node1=Qnode, label="P1813", node2=property_id, type="string"), #name of variable
        get_Q_edge(node1=Qnode, label="label", node2=label, type="string"), #label of variable
        get_Q_edge(node1=Qnode, label="P1476", node2=label, type="string"), #title of variable, same as label
        get_Q_edge(node1=Qnode, label="description", node2=description, type="string"), #description
        get_Q_edge(node1=Qnode, label="P1687", node2=Pnode), #<Qnode> corresponds to property <Pnode>

        # datamart requires qualifiers P585 and P248:
        get_Q_edge()
        
        # We also need to define the corresponding property Phomicides, with the following edges:
        get_P_edge(node1=Pnode, label="data_type", node2=wikidata_to_datamart[wikidata_sparql_to_wikidata[data_type]]), #datatype for variable
        get_P_edge(node1=Pnode, label="P31", node2="Q18616576"), #this is a property
        get_P_edge(node1=Pnode, label="label", node2=label), #label (can allow user to edit?)

        get_P_edge(node1=Pnode, label="wikidata_data_type", node2= wikidata_sparql_to_wikidata[data_type]), #do we still need this?


    ]

    return edges

def create_metadata_for_qualifier_property(qualifier, dataset_id, Property_Qnode, data_type="String"):
    Qualifier_PNode = f'P{dataset_id}-qualifier-{qualifier}'
    edges = [
            get_edge(node1=Property_Qnode, label="P2006020002", node2=Qualifier_PNode),
            get_edge(node1=Qualifier_PNode, label="label", node2=qualifier),
            get_edge(node1=Qualifier_PNode, label="P31", node2="Q18616576"),
            get_edge(node1=Qualifier_PNode, label="data_type", node2=wikidata_to_datamart[wikidata_sparql_to_wikidata[data_type]]),
            get_edge(node1=Qualifier_PNode, label="wikidata_data_type", node2= wikidata_sparql_to_wikidata[data_type])
        ]
    return edges

def create_metadata_for_qualifier_properties(project, property_name, qualifiers):
    dataset_id=clean_id(project.title)
    property_id=clean_id(property_name)
    Property_Qnode = f'Q{dataset_id}{property_id}'
    edges=[    ]
    for qualifier in qualifiers:
        new_edges = create_metadata_for_qualifier_property(qualifier, dataset_id, Property_Qnode)
        edges+=new_edges
    return edges

def connect_property_to_dataset_edge(project, property_name):
    dataset_id=clean_id(project.title)
    property_id=clean_id(property_name)
    Property_Qnode = f'Q{dataset_id}{property_id}'
    edge = get_edge(node1=f'Q{dataset_id}', label="P2006020003", node2=Property_Qnode)


def create_metadata_for_qnode(id, label, description="", **kwargs):
    edges = [
            get_edge(node1=id, label="label", node2=label),
        ]
    if description:
        edges.append(get_edge(node1=id, label="description", node2=description))
    return edges


def create_tag_edges():
    pass #TODO


