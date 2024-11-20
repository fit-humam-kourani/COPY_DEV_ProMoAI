import copy
import csv
import os
import pm4py

from evaluation.llm_evaluation.test_llm_with_chatgpt import generate_model_with_chatgpt
import time
import json  # Added to handle conversation history

from utils.prompting.prompt_engineering import model_self_improvement_prompt_short

IDS_TO_CONSIDER = [f"{i:02}" for i in range(1, 21)]
# IDS_TO_CONSIDER = ['17']
CREATE_FILES = True
ITERATION = 1


openai_model = "gpt-4o"

ground_truth_log_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_xes_one_trace_per_variant"

# Original base directory
base_dir = f"llm_com/{openai_model.replace('/', '_')}/IT{ITERATION}"
# New base directory for the improved models
new_base_dir = f"llm_com/{openai_model.replace('/', '_')}/NEW_IT{ITERATION}"

# Ensure new base directories exist for saving results
if not os.path.exists(new_base_dir):
    os.makedirs(new_base_dir)

new_pn_folder = os.path.join(new_base_dir, 'pn')
new_conv_folder = os.path.join(new_base_dir, 'conv')
new_code_folder = os.path.join(new_base_dir, 'code')
if CREATE_FILES:
    for folder in [new_pn_folder, new_conv_folder, new_code_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)

# Results table to collect statistics
results_table = []


new_statistics_csv_file = os.path.join(new_base_dir, "results_statistics.csv")
if CREATE_FILES:
    with open(new_statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write the header
        csv_writer.writerow([
            "log_name",
            "added_it",
            "visible_transitions_ground_truth",
            "visible_transitions_generated",
            "shared_activities",
            "time (sec)",
            "error message",
        ])

# Loop through each process description file
for proc_file in os.listdir(ground_truth_log_folder):
    # Get process ID from file name (e.g., "01.txt")
    proc_id = os.path.splitext(proc_file)[0]

    if IDS_TO_CONSIDER and proc_id not in IDS_TO_CONSIDER:
        continue

    ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}.xes")

    # Check if the corresponding ground truth files exist
    if not os.path.exists(ground_truth_log_path):
        raise Exception(f"Ground truth files not found for {proc_file}, skipping.")


    ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)

    # Get activities in ground truth
    log_activities = set(event["concept:name"] for trace in ground_truth_log for event in trace)
    activities_in_ground_truth = log_activities

    # **Read the previous conversation history**
    previous_conv_folder = os.path.join(base_dir, 'conv')
    previous_conversation_path = os.path.join(previous_conv_folder, f"{proc_id}.txt")

    import ast

    # Load the content as text
    with open(previous_conversation_path, "r") as file:
        content = file.read()

    conversation_history = ast.literal_eval(content)


    # **Append the new user message**
    new_user_message = model_self_improvement_prompt_short()
    conversation = copy.deepcopy(conversation_history)
    conversation.append({"role": "user", "content": new_user_message})

    start_time = time.time()
    try:
        # **Invoke the LLM with the updated conversation**
        code, process_model, conversation = generate_model_with_chatgpt(input_conversation=conversation)
        end_time = time.time()
        time_difference = str(end_time - start_time)
    except Exception as e:
        end_time = time.time()
        time_difference = str(end_time - start_time - (5 * (len(conversation) - len(conversation_history)) / 2))
        stats = {
            "log_name": proc_file,
            "num_it": "Error",
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": "None",
            "shared_activities": "None",
            "time (sec)": time_difference,
            "error message": str(e)
        }
        print(e)
    else:
        # conversation_history = conversation
        powl = process_model
        net, im, fm = pm4py.convert_to_petri_net(powl)
        activities_in_generated = [x for x in net.transitions if x.label is not None]

        # **Save Petri net**
        pnml_path = os.path.join(new_pn_folder, f"{proc_id}.pnml")
        if CREATE_FILES:
            pm4py.write_pnml(net, im, fm, pnml_path)

        # **Save conversation history and code**
        conversation_path = os.path.join(new_conv_folder, f"{proc_id}.txt")
        code_path = os.path.join(new_code_folder, f"{proc_id}.txt")

        if CREATE_FILES:
            with open(conversation_path, "w", encoding="utf-8") as conv_file:
                json.dump(conversation, conv_file, indent=4)
            with open(code_path, "w", encoding="utf-8") as code_file:
                code_file.write(str(code))

        # **Compare with ground truth**
        shared_activities = len(set(t.label for t in net.transitions if t.label) & log_activities)

        # **Extract statistics**
        stats = {
            "log_name": proc_file,
            "num_it": (len(conversation) - len(conversation_history)) / 2,
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": len(activities_in_generated),
            "shared_activities": shared_activities,
            "time (sec)": time_difference,
            "error message": ""
        }

    # **Save statistics**
    results_table.append(stats)

    if CREATE_FILES:
        # Append to CSV for every iteration
        with open(new_statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                stats["log_name"],
                stats["num_it"],
                stats["visible_transitions_ground_truth"],
                stats["visible_transitions_generated"],
                stats["shared_activities"],
                stats["time (sec)"],
                stats["error message"]
            ])

    print(stats)
