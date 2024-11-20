

import pm4py

from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.model_generation import extract_model_from_response
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges
from utils.prompting import create_conversation


id = '21'
IT = '7'
model = 'gemini-1.5-pro-002'
# model = 'ground_truth'
import os

code = open(os.path.join(r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com", f"{model}", f"IT{IT}", "code", f"{id}.txt"), "r").read()
# code = open(r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_code\21.txt", "r").read()

variable_name = 'final_model'
result = execute_code_and_get_variable(code, variable_name)
print(result)
validate_partial_orders_with_missing_transitive_edges(result)

pm4py.view_powl(result, format="SVG")

# pn_path = os.path.join(r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com", f"{model}", f"IT{IT}", "pn", f"{id}.pnml")
# #
# pn, im, fm = pm4py.read_pnml(pn_path)
#
# bpmn = pm4py.convert_to_bpmn(pn, im, fm)
#
# pm4py.view_bpmn(bpmn, format="SVG")

# pn_path = os.path.join(r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_pn", f"{id}.pnml")

# print(pn)
# BPMN = pm4py.convert_to_bpmn(pn, im, fm)
#
# new_path = os.path.join(r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\images", f"{model}_p{id}.pdf")
#
# from pm4py.visualization.bpmn import visualizer
# pm4py.save_vis_bpmn(BPMN, new_path)

#
# pn, im, fm = pm4py.read_pnml(pn_path)
# pm4py.view_petri_net(pn, im, fm)