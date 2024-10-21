import os
import pm4py

from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges

folder = '../testfiles/long_descriptions'


def recreate_petri_net_from_code(proc_id, path):
    ground_truth_file = f"../testfiles/models_as_code/{proc_id}.txt"

    if not os.path.exists(ground_truth_file):
        raise Exception(f"Ground truth file not found for {proc_id}, skipping.")

    code = open(ground_truth_file, "r").read()

    # Generate ground truth Petri net
    variable_name = 'final_model'
    ground_truth_powl = execute_code_and_get_variable(code, variable_name)
    validate_partial_orders_with_missing_transitive_edges(ground_truth_powl)
    ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.convert_to_petri_net(ground_truth_powl)

    pm4py.write_pnml(ground_truth_net, ground_truth_im, ground_truth_fm, path)

    return ground_truth_net, ground_truth_im, ground_truth_fm


def add_missing_activity_after(ground_truth_log, target_activity, activity_to_add):
    from pm4py.objects.log.obj import EventLog, Event
    import copy
    modified_log = EventLog()

    for trace in ground_truth_log:
        target_indices = [i for i, event in enumerate(trace) if event["concept:name"] == target_activity]
        if len(target_indices) != 1:
            raise Exception("Duplicated/missing target activity!")

        base_trace = copy.deepcopy(trace)

        for index in range(target_indices[0], len(base_trace)):
            # Create a new trace with the activity inserted after the target_activity
            new_trace = copy.deepcopy(trace)
            new_event = Event({"concept:name": activity_to_add})
            new_trace.insert(index + 1, new_event)
            modified_log.append(new_trace)
    return modified_log


def recreate_log_from_petri_net(proc_id, ground_truth_net, ground_truth_im, ground_truth_fm):
    if True:
        ground_truth_file = f"../testfiles/models_as_code/{proc_id}.txt"
        code = open(ground_truth_file, "r").read()
        variable_name = 'final_model'
        ground_truth_powl = execute_code_and_get_variable(code, variable_name)
        validate_partial_orders_with_missing_transitive_edges(ground_truth_powl)
        pm4py.view_powl(ground_truth_powl)

    ground_truth_dir = f"../testfiles/ground_truth_xes_one_trace_per_variant"
    if not os.path.exists(ground_truth_dir):
        os.makedirs(ground_truth_dir)

    tree = pm4py.convert_to_process_tree(ground_truth_net, ground_truth_im, ground_truth_fm)
    ground_truth_log = pm4py.algo.simulation.playout.process_tree.algorithm.apply(tree,
                                                                                  variant=pm4py.algo.simulation.playout.process_tree.algorithm.Variants.EXTENSIVE,
                                                                                  parameters={
                                                                                      "max_trace_length": 10000000,
                                                                                      "max_loop_occ": 1,
                                                                                      # 'num_traces': 5000
                                                                                  })
    #
    print(len((ground_truth_log)))
    # precision = pm4py.precision_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
    # print(precision)
    # fitness = pm4py.fitness_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
    # print(fitness)

    pm4py.write_xes(ground_truth_log, os.path.join(ground_truth_dir, f"{proc_id}_ground_truth_log.xes"))


for proc_desc_file in os.listdir(folder):
    process_id = os.path.splitext(proc_desc_file)[0]

    # IDS_TO_CONSIDER = ['hotel']
    IDS_TO_CONSIDER = None
    CREATE_NEW_PN = False

    if IDS_TO_CONSIDER and process_id not in IDS_TO_CONSIDER:
        continue

    ground_truth_dir_pn = f"../testfiles/ground_truth_pn"
    if not os.path.exists(ground_truth_dir_pn):
        os.makedirs(ground_truth_dir_pn)
    pn_path = os.path.join(ground_truth_dir_pn, f"{process_id}_ground_truth_petri.pnml")

    if CREATE_NEW_PN:
        pn, im, fm = recreate_petri_net_from_code(process_id, pn_path)
    else:
        pn, im, fm = pm4py.read_pnml(pn_path)

    recreate_log_from_petri_net(process_id, pn, im, fm)
