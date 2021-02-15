import unittest
from pathlib import Path
from t2wml.input_processing.annotation_parsing import Annotation, AnnotationNodeGenerator

repo_folder = Path(__file__).parents[2]
unit_test_folder = Path(repo_folder)/"t2wml-api"/"unit_tests"/"ground_truth"/"annotations"

class TestAnnotations(unittest.TestCase):      
    def test_load_annotation(self):
        anno_path=unit_test_folder/"test_annotation.annotation"
        anno=Annotation.load(anno_path)
        anno.initialize()
        anno.save(anno_path)
    

if __name__ == '__main__':
    unittest.main()