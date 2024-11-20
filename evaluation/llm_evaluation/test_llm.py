import csv
import os
import pm4py
from utils.model_generation.model_generation import generate_model
from utils.prompting import create_conversation
import time

# IDS_TO_CONSIDER = ['hotel']
IDS_TO_CONSIDER = "21"
CREATE_FILES = True
ITERATION = 7

# Read API configurations
api_url = open("../api_url.txt", "r").read().strip()
api_key = open("../api_key.txt", "r").read().strip()
openai_model = open("../api_model.txt", "r").read().strip()

description_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_process_descriptions"
ground_truth_log_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_xes_one_trace_per_variant"

base_dir = f"llm_com/{openai_model.replace('/', '_')}/IT{ITERATION}"

# Ensure base directories exist for saving results
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

pn_folder = os.path.join(base_dir, 'pn')
conv_folder = os.path.join(base_dir, 'conv')
code_folder = os.path.join(base_dir, 'code')
if CREATE_FILES:
    if not os.path.exists(pn_folder):
        os.makedirs(pn_folder)
    if not os.path.exists(conv_folder):
        os.makedirs(conv_folder)
    if not os.path.exists(code_folder):
        os.makedirs(code_folder)

# Results table to collect statistics
results_table = []

statistics_csv_file = os.path.join(base_dir, "results_statistics.csv")
if CREATE_FILES:
    with open(statistics_csv_file, "a", newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write the header
        csv_writer.writerow([
            "log_name",
            "num_it",
            "visible_transitions_ground_truth",
            "visible_transitions_generated",
            "shared_activities",
            # "percFitTraces",
            # "averageFitness",
            # "percentage_of_fitting_traces",
            # "average_trace_fitness",
            # "log_fitness",
            # "precision",
            "time",
            "error message",
        ])

# Loop through each process description file
for proc_file in os.listdir(description_folder):
    # Get process ID from file name (e.g., "01.txt")
    proc_id = os.path.splitext(proc_file)[0]

    if IDS_TO_CONSIDER and proc_id not in IDS_TO_CONSIDER:
        continue

    ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}.xes")

    # Check if the corresponding ground truth files exist
    if not os.path.exists(ground_truth_log_path):
        raise Exception(f"Ground truth files not found for {proc_file}, skipping.")

    # Load process description
    proc_descr = open(os.path.join(description_folder, proc_file), "r").read().strip()

    # Load ground truth Petri net and log
    # ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.read_pnml(ground_truth_pn_path)
    ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)
    # activities_in_ground_truth = [x for x in ground_truth_net.transitions if x.label is not None]

    log_activities = set(event["concept:name"] for trace in ground_truth_log for event in trace)
    activities_in_ground_truth = log_activities
    proc_descr += "\n\nEnsure the generated model uses the following activity labels (please also note upper and lower case): " + ", ".join(
        log_activities)
    init_conversation = create_conversation(proc_descr)
    start_time = time.time()
    try:
        code, process_model, conversation = generate_model(init_conversation,
                                                           api_key=api_key,
                                                           llm_name=openai_model,
                                                           api_url=api_url,
                                                           max_iterations=10,
                                                           additional_iterations=5
                                                           )
        end_time = time.time()
        time_difference = str(end_time - start_time)
    except Exception as e:
        end_time = time.time()
        time_difference = str(end_time - start_time)
        stats = {
            "log_name": proc_file,
            "num_it": "Error",
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": "None",
            "shared_activities": "None",
            # "fitness": "None",
            # "precision": "None",
            "time (sec)": time_difference,
            "error message": str(e)
        }
        print(e)

    else:
        conversation_history = conversation
        powl = process_model
        net, im, fm = pm4py.convert_to_petri_net(powl)
        activities_in_generated = [x for x in net.transitions if x.label is not None]

        # Save Petri net
        pnml_path = os.path.join(pn_folder, f"{proc_id}.pnml")
        if CREATE_FILES:
            pm4py.write_pnml(net, im, fm, pnml_path)

        # Save conversation history
        conversation_path = os.path.join(conv_folder, f"{proc_id}.txt")
        code_path = os.path.join(code_folder, f"{proc_id}.txt")

        if CREATE_FILES:
            with open(conversation_path, "w", encoding="utf-8") as conv_file:
                conv_file.write(str(conversation_history))
            with open(code_path, "w", encoding="utf-8") as code_file:
                code_file.write(str(code))

        # Compare with ground truth
        shared_activities = len(set(t.label for t in net.transitions if t.label) & log_activities)
        # fitness = pm4py.fitness_alignments(ground_truth_log, net, im, fm)
        # precision = pm4py.precision_alignments(ground_truth_log, net, im, fm)

        # Extract statistics
        stats = {
            "log_name": proc_file,
            "num_it": len(conversation_history) / 2,
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": len(activities_in_generated),
            "shared_activities": shared_activities,
            # "fitness": "skipped",
            # "precision": "skipped",
            "time (sec)": time_difference,
            "error message": ""
        }

    # Save statistics
    results_table.append(stats)

    if CREATE_FILES:
        # Append to CSV for every iteration
        with open(statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                stats["log_name"],
                stats["num_it"],
                stats["visible_transitions_ground_truth"],
                stats["visible_transitions_generated"],
                stats["shared_activities"],
                # "skipped",
                # "skipped",
                # "skipped",
                # "skipped",
                # "skipped",
                # "skipped",
                stats["time (sec)"],
                stats["error message"]
            ])

    print(stats)
    # if CREATE_FILES:
    #     # Save the statistics table
    #     statistics_file = os.path.join(base_dir, "results_statistics.json")
    #     with open(statistics_file, "a") as stats_file:
    #         json.dump(stats, stats_file, indent=4)
