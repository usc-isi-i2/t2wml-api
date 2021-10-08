
import re
import datetime
from t2wml.input_processing.utils import clean_id

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
'Time': 'date_and_times',
'String': 'string',
'MonolingualText': 'string',
'ExternalIdentifier': 'symbol',
'WikibaseItem': 'symbol',
'WikibaseProperty': 'symbol',
'Url': 'symbol',
}



def clean_name(input):
    input = input.strip()
    input=input.rstrip(":")
    return input.strip()


def create_metadata_for_project(project):
    def get_edge(node1, label, node2, type):
        #id = node1-label (no serial number)
        return dict(node1=node1, label=label, node2=node2, type=type, id=f'{node1}-{label}')

    dataset_id=clean_id(project.title)
    dataset_qnode = "Q"+dataset_id
    timestamp=datetime.datetime.now().isoformat()

    metadata = [
        #no needs for serial number as there's only one edge each
        get_edge(node1=dataset_qnode, label="P31", node2="Q1172284", type="symbol"), # this is a dataset
        get_edge(node1=dataset_qnode, label="P1813", node2=clean_id(project.title), type="string"), # this is its name that we expose
        get_edge(node1=dataset_qnode, label="label", node2=clean_name(project.title), type="string"), # an informative label
        get_edge(node1=dataset_qnode, label="P1476", node2=project.title, type="string"), # a title, same as label
        get_edge(node1=dataset_qnode, label="description", node2=project.description, type="string"), # a description
        get_edge(node1=dataset_qnode, label="P2699", node2=project.url, type="string"), #source url for dataset
        get_edge(node1=dataset_qnode, label="P5017", node2=timestamp, type="date_and_times") #last update date, in YYYY-mm-DDTHH:mm format
    ]

    return metadata

def add_qualifier_property_to_variable(project, variable_id, qualifier_property_id):
    dataset_Qnode=f'Q{clean_id(project.title)}'
    variable_id=variable_id #Knock off the P in the beginning
    variable_Qnode = f'Q{variable_id}'
    return dict(id=f'{dataset_Qnode}-{variable_Qnode}-P2006020002-{qualifier_property_id}',
                node1=f'{dataset_Qnode}-{variable_Qnode}', label="P2006020002", node2=qualifier_property_id, type="symbol")
    


def create_metadata_for_variable(project, variable_id, label, description, data_type, tags=[]):
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
    dataset_Qnode=f'Q{clean_id(project.title)}'
    variable_id=variable_id[1:] #knock off the P
    Pnode = f'P{variable_id}'
    Qnode = f'Q{variable_id}'

    def get_Q_edge(node1, label, node2, type):
        #id = datasetQnode-variableQnode-node1-label
        return dict(node1=f'{dataset_Qnode}-{node1}', label=label, node2=node2, type=type, id=f'{dataset_Qnode}-{node1}-{label}')
    
    
    def get_P_edge(node1, label, node2, type):
        # id = node1-label
        # Note that the property edge IDs do not have the dataset in them, 
        # that’s because properties should be shared between datasets. 
        # If we want properties not be shared, we need to add the dataset name to their node1, not just the ID.
        return dict(node1=node1, label=label, node2=node2, type=type, id=f'{node1}-{label}')

    edges=[
        #The following edges describe the variable metadata in Datamart
        dict(id=f'{dataset_Qnode}-P2006020003-{Qnode}', node1=dataset_Qnode, label="P2006020003", node2=f'{dataset_Qnode}-{Qnode}', type="symbol"), #the <dataset_id> dataset has the <Qnode> variable
        get_Q_edge(node1=Qnode, label="P2006020004", node2=dataset_Qnode, type="symbol"), # the dataset of <Qnode> variable is <dataset_id> dataset
        get_Q_edge(node1=Qnode, label="P31", node2="Q50701", type="symbol"), #<Qnode> is a variable
        get_Q_edge(node1=Qnode, label="P1813", node2=clean_id(label), type="string"), #name of variable (?)
        get_Q_edge(node1=Qnode, label="label", node2=clean_name(label), type="string"), #label of variable
        get_Q_edge(node1=Qnode, label="P1476", node2=label, type="string"), #title of variable, same as label
        get_Q_edge(node1=Qnode, label="description", node2=description, type="string"), #description
        get_Q_edge(node1=Qnode, label="P1687", node2=Pnode, type="symbol"), #<Qnode> corresponds to property <Pnode>

        # datamart requires qualifiers P585 and P248:
        add_qualifier_property_to_variable(project, variable_id, "P585"),
        add_qualifier_property_to_variable(project, variable_id, "P248"),
        
        # We also need to define the corresponding property Phomicides, with the following edges:
        get_P_edge(node1=Pnode, label="data_type", node2=wikidata_to_datamart[wikidata_sparql_to_wikidata[data_type]], type="string"), #datatype for variable
        get_P_edge(node1=Pnode, label="P31", node2="Q18616576", type="symbol"), #this is a property
        get_P_edge(node1=Pnode, label="label", node2=clean_name(label), type="string"), #label (can allow user to edit?)
        get_P_edge(node1=Pnode, label="wikidata_data_type", node2= wikidata_sparql_to_wikidata[data_type], type="string"), #do we still need this?

    ]

    #handle any tags:
    for index, tag in enumerate(tags):
        edges.append(dict(node1=Qnode, label="P2010050001", node2=tag, type="string", id=f'{dataset_Qnode}-{Qnode}-P2010050001-{index}'))

    return edges

def create_metadata_for_qualifier_property(project, variable_id, qualifier_property_id, label, data_type):
    dataset_Qnode=f'Q{clean_id(project.title)}'
    def get_edge(node1, label, node2, type):
        return dict(node1=node1, label=label, node2=node2, type=type, id=f"{dataset_Qnode}-{node1}-{label}")

    edges = [
            add_qualifier_property_to_variable(project, variable_id[1:], qualifier_property_id),
            get_edge(node1=qualifier_property_id, label="label", node2=clean_name(label), type="string"),
            get_edge(node1=qualifier_property_id, label="P31", node2="Q18616576", type="symbol"), #do we need this?
            get_edge(node1=qualifier_property_id, label="data_type", node2=wikidata_to_datamart[wikidata_sparql_to_wikidata[data_type]], type="string"), #do we need this?
            get_edge(node1=qualifier_property_id, label="wikidata_data_type", node2= wikidata_sparql_to_wikidata[data_type], type="string")
        ]
    return edges




def create_metadata_for_custom_qnode(id, label, description="", **kwargs): #do we need this function?
    def get_edge(node1, label, node2, type):
        return dict(node1=node1, label=label, node2=node2, type=type, id=f'{node1}-{label}')
    edges = [
            get_edge(node1=id, label="label", node2=clean_name(label), type="string"),
        ]
    if description:
        edges.append(get_edge(node1=id, label="description", node2=description, type="string"))
    return edges


def link_statement_to_dataset(project, statement_id):
    dataset_Qnode=f'Q{clean_id(project.title)}'
    result_dict = dict(node1=statement_id, label="P2006020004", node2=dataset_Qnode, id=f"{dataset_Qnode}-P2006020004-{statement_id}")
    result_dict["node2;kgtk:data_type"]="symbol"
    result_dict["node2;kgtk:symbol"] = dataset_Qnode
    return result_dict

