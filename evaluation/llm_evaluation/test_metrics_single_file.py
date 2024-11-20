import csv
import os
import pm4py
import json
from utils import llm_model_generator

pn_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com\gemini-1.5-pro-002\IT3_IMPROVED\pn"
ground_truth_log_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\FIXED_ground_truth_xes_one_trace_per_variant"

proc_id = '02'
# model = 'gpt-4o'

pn_path = os.path.join(pn_folder, f"{proc_id}.pnml")
ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}.xes")

net, im, fm = pm4py.read_pnml(pn_path)
tree = pm4py.convert_to_process_tree(net, im, fm)
pm4py.view_process_tree(tree)
ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)

precision = pm4py.precision_token_based_replay(ground_truth_log, net, im, fm)
# pm4py.view_petri_net(net, im, fm)

print(precision)
fit = pm4py.fitness_token_based_replay(ground_truth_log, net, im, fm)
# pm4py.view_petri_net(net, im, fm)

print(fit)
# # Extract statistics
# stats = {
#     "log_name": proc_id,
#     "visible_transitions_ground_truth_log": len(activities_in_ground_truth),
#     "visible_transitions_model": len(activities_in_generated),
#     "shared_activities": shared_activities,
#     # "fitness": fitness,
#     "precision": precision
# }
