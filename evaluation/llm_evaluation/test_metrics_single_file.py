import csv
import os
import pm4py
import json
from utils import llm_model_generator

ground_truth_pn_folder = "../testfiles/ground_truth_pn"
ground_truth_log_folder = "../testfiles/ground_truth_xes"


proc_id = '18'

# Define paths for ground truth Petri net and log
ground_truth_pn_path = os.path.join(ground_truth_pn_folder, f"{proc_id}_ground_truth_petri.pnml")
ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}_ground_truth_log.xes")

# Load ground truth Petri net and log
ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.read_pnml(ground_truth_pn_path)
ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)
activities_in_ground_truth = [x for x in pm4py.get_event_attribute_values(ground_truth_log, 'concept:name').keys() if x is not None]

activities_in_generated = [x for x in ground_truth_net.transitions if x.label is not None]

# Compare with ground truth
shared_activities = len(set(t.label for t in ground_truth_net.transitions if t.label) & set(
    t.label for t in ground_truth_net.transitions if t.label))
# fitness = pm4py.fitness_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
precision = pm4py.precision_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
print(precision)
# # Extract statistics
# stats = {
#     "log_name": proc_id,
#     "visible_transitions_ground_truth_log": len(activities_in_ground_truth),
#     "visible_transitions_model": len(activities_in_generated),
#     "shared_activities": shared_activities,
#     # "fitness": fitness,
#     "precision": precision
# }
