
import re
import datetime


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
    input = re.sub(r'[^A-Za-z0-9\s]+', '', input)
    input = re.sub("\s", "_", input)
    return input

def get_edge(node1, label, node2):
    return dict(node1=node1, label=label, node2=node2, id=f'{node1}-{label}-1')


def create_metadata_for_project(project):
    dataset_id=clean_id(project.title)
    dataset_qnode = "Q"+dataset_id
    timestamp=datetime.datetime.utcnow()

    metadata = [
        get_edge(node1=dataset_qnode, label="P31", node2="Q1172284"), #"-P31-Q1172284-1"
        get_edge(node1=dataset_qnode, label="label", node2=project.title),
        get_edge(node1=dataset_qnode, label="P1476", node2=project.title),
        get_edge(node1=dataset_qnode, label="description", node2=project.description),
        get_edge(node1=dataset_qnode, label="P2699", node2=project.url),
        get_edge(node1=dataset_qnode, label="P1813", node2=project.title),
        get_edge(node1=dataset_qnode, label="P5017", node2=timestamp)
    ]

    return metadata


def create_metadata_for_variable(project, property_id, label, description, data_type):
    dataset_id=clean_id(project.title)
    Pnode = f'P{dataset_id}-{property_id}'
    Qnode = f'Q{dataset_id}-{property_id}'
    
    edges=[
        get_edge(node1=Qnode, label="description", node2=description),
        get_edge(node1=Qnode, label="label", node2=label),
        get_edge(node1=Qnode, label="P1476", node2=label),
        get_edge(node1=Qnode, label="P1687", node2=Pnode),
        get_edge(node1=Qnode, label="P1813", node2=property_id),
        get_edge(node1=Qnode, label="P2006020004", node2=dataset_id),
        get_edge(node1=Qnode, label="P31", node2="Q50701"),
        get_edge(node1=Pnode, label="P31", node2="Q18616576"),
        get_edge(node1=Pnode, label="label", node2=label),
        get_edge(node1=Pnode, label="data_type", node2=wikidata_to_datamart[wikidata_sparql_to_wikidata[data_type]]),
        get_edge(node1=Pnode, label="wikidata_data_type", node2= wikidata_sparql_to_wikidata[data_type]),
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


