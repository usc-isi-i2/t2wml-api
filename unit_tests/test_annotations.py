import unittest
import json
from pathlib import Path
from t2wml.input_processing.annotation_parsing import Annotation

repo_folder = Path(__file__).parents[2]
unit_test_folder = Path(repo_folder)/"t2wml-api"/"unit_tests"/"ground_truth"/"annotations"

class TestAnnotations(unittest.TestCase):      
    def test_load_annotation(self):
        anno_path=unit_test_folder/"test_annotation.annotation"
        anno=Annotation.load(anno_path)
        anno.initialize()
        anno.save(anno_path)
        
    def test_user_link(self):
        with open(unit_test_folder/"test_annotation.annotation", 'r') as f:
            annotations=json.load(f)
        annotations[-1]["userlink"]="0d996604-014e-4ef1-ace2-0583ecc2eb70" #"9a4b3f0e-7b55-40bf-9863-b862a5216765"
        anno=Annotation(annotations)
        anno.initialize()
        assert anno.annotation_block_array[-1]["link"]=="0d996604-014e-4ef1-ace2-0583ecc2eb70" # "9a4b3f0e-7b55-40bf-9863-b862a5216765"
        annotations[-1]["userlink"]="nonexistentid"
        anno=Annotation(annotations)
        anno.initialize()
        assert anno.annotation_block_array[-1]["link"]=="9a4b3f0e-7b55-40bf-9863-b862a5216765" #"0d996604-014e-4ef1-ace2-0583ecc2eb70"

    

if __name__ == '__main__':
    unittest.main()