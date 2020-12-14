from t2wml.input_processing.annotation_parsing import Annotations, ValueArgs

annotations=dict(

canonical=Annotations(
data_regions=[ValueArgs("E4:E19")],
subject_regions=[ValueArgs("C4:C19")],
qualifier_regions=[ValueArgs("A4:A19", use_item=True), ValueArgs("D4:D19")],
property_regions=[ValueArgs("A3", True), ValueArgs("D3", True), ValueArgs("B4:B19", True)]
),


product_row=Annotations(
data_regions=[ValueArgs("C4:D11")],
subject_regions=[ValueArgs("C3:D3")],
qualifier_regions=[ValueArgs("A4:A11", use_item=True), ValueArgs("E4:D11")],
property_regions=[ValueArgs("A3", True), ValueArgs("B4:B11", True)]
),


multi_header=Annotations(
data_regions=[ValueArgs("B5:E8")],
subject_regions=[ValueArgs("F5:F8")],
qualifier_regions=[ValueArgs("A5:A8", use_item=True), ValueArgs("B4:E4")],
property_regions=[ValueArgs("A3", True), ValueArgs("B3:E3", True)]
),

columbia_elections_2_advanced=Annotations(
data_regions=[ValueArgs("A20:A22")],
subject_regions=[ValueArgs("A17")],
qualifier_regions=[ValueArgs("C20:F22", use_item=True)],
property_regions=[ValueArgs("A18", True), ValueArgs("C19:F19", True)]
),


elections_example_1=Annotations(
data_regions=[ValueArgs("C3:F10")],
subject_regions=[ValueArgs("A3:A10")],
qualifier_regions=[ValueArgs("C1:F1")],
property_regions=[ValueArgs("C2:F2", True)]
),

FC_Barcelona_squad=Annotations(
data_regions=[ValueArgs("A2:B13")],
subject_regions=[ValueArgs("D2:D13")],
qualifier_regions=[ValueArgs("C2:C13")],
property_regions=[ValueArgs("A1:B1", True), ValueArgs("C1", True)] 
),

major_staples=Annotations(
data_regions=[ValueArgs("B2:L8")],
subject_regions=[ValueArgs("B1:L1")],
qualifier_regions=[],
property_regions=[ValueArgs("A2:A8", True)] 
),

staple_production=Annotations(
data_regions=[ValueArgs("C3:E12"), ValueArgs("G3:G12")],
subject_regions=[ValueArgs("B3:B12")],
qualifier_regions=[],
property_regions=[ValueArgs("C1:E1"), ValueArgs("G1")] 
),

largest_buildings=Annotations(
data_regions=[ValueArgs("D2:E5")],
subject_regions=[ValueArgs("A2:A5")],
qualifier_regions=[],
property_regions=[ValueArgs("D1:E1")] 
),

queen_disco=Annotations(
data_regions=[ValueArgs("C3:N7")],
subject_regions=[ValueArgs("A3:A7")],
qualifier_regions=[ValueArgs("B3:B7")],
property_regions=[ValueArgs("B1"), ValueArgs("C1")]
),


tallest_buildings=Annotations(
data_regions=[ValueArgs("E2:F18")],
subject_regions=[ValueArgs("B2:B18")],
qualifier_regions=[ValueArgs("C2:D18"), ValueArgs("G2:G18")],
property_regions=[ValueArgs("C1:D1"), ValueArgs("E1:F1"), ValueArgs("G1")]
),

world_tennis_players=Annotations(
data_regions=[ValueArgs("F3:G12")],
subject_regions=[ValueArgs("C3:C12")],
qualifier_regions=[ValueArgs("D3:E12"), ValueArgs("B3:B12")],
property_regions=[ValueArgs("B1"), ValueArgs("F1:G1"), ValueArgs("D1:E1")]
),

largest_biotech=Annotations(
data_regions=[ValueArgs("D2:J6")],
subject_regions=[ValueArgs("B2:B6")],
property_regions=[ValueArgs("D1:J1")]
)
)

