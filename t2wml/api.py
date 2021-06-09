import warnings
from t2wml.settings import t2wml_settings
from t2wml.wikification.utility_functions import add_entities_from_file, kgtk_to_dict, dict_to_kgtk
from t2wml.wikification.item_table import Wikifier
from t2wml.spreadsheets.sheet import Sheet, SpreadsheetFile
from t2wml.mapping.statement_mapper import YamlMapper, StatementMapper, AnnotationMapper
from t2wml.wikification.wikifier_service import WikifierService
from t2wml.wikification.wikidata_provider import SparqlProvider, DictionaryProvider, WikidataProvider
from t2wml.knowledge_graph import KnowledgeGraph, create_output_from_files
from t2wml.project import Project
from t2wml.input_processing.annotation_parsing import Annotation, AnnotationNodeGenerator, get_Pnode, get_Qnode
from t2wml.input_processing.annotation_suggesting import block_finder, annotation_suggester



def add_nodes_from_file(file_path: str):
    warnings.warn("add_nodes_from_file is deprecated, use add_entities_from_file instead", DeprecationWarning)
    return add_entities_from_file(file_path)