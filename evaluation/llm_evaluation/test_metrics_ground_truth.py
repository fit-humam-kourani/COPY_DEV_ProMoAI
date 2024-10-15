import csv
import os
import pm4py
import json
from utils import llm_model_generator

long_desc_folder = "../testfiles/long_descriptions"
ground_truth_pn_folder = "../testfiles/ground_truth_pn"
ground_truth_log_folder = "../testfiles/ground_truth_xes"
base_dir = f"llm_com"

# Results table to collect statistics
results_table = []

statistics_csv_file = os.path.join(base_dir, "ground_truth_statistics.csv")
with open(statistics_csv_file, "w", newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    # Write the header
    csv_writer.writerow([
        "log_name",
        "visible_transitions_ground_truth_log",
        "visible_transitions_model",
        "shared_activities",
        "percFitTraces",
        "averageFitness",
        "percentage_of_fitting_traces",
        "average_trace_fitness",
        "log_fitness",
        "precision"
    ])

# Loop through each process description file
for proc_file in os.listdir(long_desc_folder):
    # Get process ID from file name (e.g., "01.txt")
    proc_id = os.path.splitext(proc_file)[0]

    # Define paths for ground truth Petri net and log
    ground_truth_pn_path = os.path.join(ground_truth_pn_folder, f"{proc_id}_ground_truth_petri.pnml")
    ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}_ground_truth_log.xes")

    # Check if the corresponding ground truth files exist
    if not os.path.exists(ground_truth_pn_path) or not os.path.exists(ground_truth_log_path):
        raise Exception(f"Ground truth files not found for {proc_file}, skipping.")


    # Load ground truth Petri net and log
    ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.read_pnml(ground_truth_pn_path)
    ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)
    activities_in_ground_truth = [x for x in pm4py.get_event_attribute_values(ground_truth_log, 'concept:name').keys() if x is not None]

    activities_in_generated = [x for x in ground_truth_net.transitions if x.label is not None]

    # Compare with ground truth
    shared_activities = len(set(t.label for t in ground_truth_net.transitions if t.label) & set(
        t.label for t in ground_truth_net.transitions if t.label))
    fitness = pm4py.fitness_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)
    precision = pm4py.precision_alignments(ground_truth_log, ground_truth_net, ground_truth_im, ground_truth_fm)

    # Extract statistics
    stats = {
        "log_name": proc_file,
        "visible_transitions_ground_truth_log": len(activities_in_ground_truth),
        "visible_transitions_model": len(activities_in_generated),
        "shared_activities": shared_activities,
        "fitness": fitness,
        "precision": precision
    }

    # Save statistics
    results_table.append(stats)

    # Append to CSV for every iteration
    with open(statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            stats["log_name"],
            stats["visible_transitions_ground_truth_log"],
            stats["visible_transitions_model"],
            stats["shared_activities"],
            stats["fitness"]["percFitTraces"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["averageFitness"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["percentage_of_fitting_traces"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["average_trace_fitness"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["log_fitness"] if stats["fitness"] != "None" else "None",
            stats["precision"] if stats["precision"] != "None" else "None"
        ])

    # Save the statistics table
    statistics_file = os.path.join(base_dir, "results_statistics.json")
    with open(statistics_file, "w") as stats_file:
        json.dump(results_table, stats_file, indent=4)
