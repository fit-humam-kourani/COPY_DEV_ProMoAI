import csv
import os
import pm4py
import json
from utils import llm_model_generator

ground_truth_pn_folder = "../testfiles/ground_truth_pn"
ground_truth_log_folder = "../testfiles/ground_truth_xes"


proc_id = 'hotel'

ground_truth_pn_path = os.path.join(ground_truth_pn_folder, f"{proc_id}_ground_truth_petri.pnml")

ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.read_pnml(ground_truth_pn_path)

ground_truth_dir = f"../testfiles/ground_truth_xes"

ground_truth_log = pm4py.algo.simulation.playout.petri_net.algorithm.apply(ground_truth_net, ground_truth_im,
                                                                           ground_truth_fm, variant=pm4py.algo.simulation.playout.petri_net.algorithm.Variants.EXTENSIVE,
                                                                           parameters={'noTraces': 10000, 'maxTraceLength':200})

# tree = pm4py.convert_to_process_tree(ground_truth_net, ground_truth_im, ground_truth_fm)
# pm4py.view_process_tree(tree)
#
# ground_truth_log = pm4py.algo.simulation.playout.process_tree.algorithm.apply(tree, variant=pm4py.algo.simulation.playout.process_tree.algorithm.Variants.EXTENSIVE,
#                                                                               parameters={"max_trace_length": 10000,
#                                                                                           "max_loop_occ":1,
#                                                                                           # 'num_traces': 5000
#                                                                                           })

new_tree = pm4py.discover_process_tree_inductive(ground_truth_log)
pm4py.view_process_tree(new_tree)


pm4py.write_xes(ground_truth_log, os.path.join(ground_truth_dir, f"{proc_id}_ground_truth_log.xes"))

print(len(ground_truth_log))

precision = pm4py.precision_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
print(precision)
fitness = pm4py.fitness_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
print(fitness)



