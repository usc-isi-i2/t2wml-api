
import re
import datetime

def clean_id(input):
    input = re.sub(r'[^A-Za-z0-9\s]+', '', input)
    input = re.sub("\s", "_", input)
    return input


def create_metadata_for_project(project):
    dataset_id=clean_id(project.title)
    dataset_qnode = "Q"+dataset_id
    timestamp=datetime.datetime.utcnow()

    metadata = [
        dict(node1=dataset_qnode, label="P31", node2="Q1172284", id=dataset_qnode+"-P31-Q1172284-1"),
        dict(node1=dataset_qnode, label="label", node2=project.title, id=""),
        dict(node1=dataset_qnode, label="P1476", node2=project.title, id=""),
        dict(node1=dataset_qnode, label="description", node2=project.description, id=""),
        dict(node1=dataset_qnode, label="P2699", node2=project.url, id=""),
        dict(node1=dataset_qnode, label="P1813", node2=project.title, id=""),
        dict(node1=dataset_qnode, label="P5017", node2=timestamp, id="")
    ]

    return metadata


def create_metadata_for_property(project, name, description, data_type="Quantity"):
    dataset_id=clean_id(project.title)
    property_id=clean_id(name)
    Pnode = f'P{dataset_id}{property_id}'
    Qnode = f'Q{dataset_id}{property_id}'
    
    
    edges=[
        dict(node1=Qnode, label="description", node2=description),
        dict(node1=Qnode, label="label", node2=name),
        dict(node1=Qnode, label="P1476", node2=name),
        dict(node1=Qnode, label="P1687", node2=Pnode),
        dict(node1=Qnode, label="P1813", node2=property_id),
        dict(node1=Qnode, label="P2006020004", node2=dataset_id),
        dict(node1=Qnode, label="P31", node2="Q50701"),
        dict(node1=Pnode, label="P31", node2="Q18616576"),
        dict(node1=Pnode, label="label", node2=name),
        dict(node1=Pnode, label="data_type", node2=data_type),
        dict(node1=Pnode, label="wikidata_data_type", node2=data_type),
    ]

    return edges

def create_metadata_for_qualifier_property(qualifier, dataset_id, Property_Qnode, data_type="String"):
    Qualifier_PNode = f'P{dataset_id}-qualifier-{qualifier}'
    edges = [
            dict(node1=Property_Qnode, label="P2006020002", node2=Qualifier_PNode),
            dict(node1=Qualifier_PNode, label="label", node2=qualifier),
            dict(node1=Qualifier_PNode, label="P31", node2="Q18616576"),
            dict(node1=Qualifier_PNode, label="data_type", node2=data_type),
            dict(node1=Qualifier_PNode, label="wikidata_data_type", node2=data_type)
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
    edge = dict(node1=f'Q{dataset_id}', label="P2006020003", node2=Property_Qnode)


def create_metadata_for_qnode(id, label, description=""):
    edges = [
            dict(node1=id, label="label", node2=label),
        ]
    if description:
        edges.append(dict(node1=id, label="description", node2=description))
    return edges


def create_tag_edges():
    pass #TODO