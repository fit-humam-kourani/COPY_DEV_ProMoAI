import os

import pm4py

from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.model_generation import extract_model_from_response
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges
from utils.prompting import create_conversation


id = 'hotel'


code = open(f"../testfiles/models_as_code/{id}.txt", "r").read()

variable_name = 'final_model'
result = execute_code_and_get_variable(code, variable_name)
validate_partial_orders_with_missing_transitive_edges(result)

from pm4py.visualization.powl import visualizer
svg = visualizer.apply(result)
visualizer.view(svg)
#
# ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.convert_to_petri_net(result)
#
# ground_truth_dir = f"../testfiles/ground_truth_pn"
# if not os.path.exists(ground_truth_dir):
#     os.makedirs(ground_truth_dir)
# pm4py.write_pnml(ground_truth_net, ground_truth_im, ground_truth_fm,
#                  os.path.join(ground_truth_dir, f"{id}_ground_truth_petri.pnml"))