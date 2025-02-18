import csv
import os
import pm4py
import time
import traceback
import pyperclip
import subprocess

from utils.model_generation.model_generation import generate_model, extract_model_from_response
from utils.prompting import create_conversation

# New boolean flag
MANUAL = True  # Set to True for manual mode

# IDS_TO_CONSIDER = ['hotel']
IDS_TO_CONSIDER = ["18"]
IDS_TO_CONSIDER = None
CREATE_FILES = True
ITERATION = 1

# Read API configurations
api_url = "https://api.x.ai/v1"
api_key = "aaaaaa"
openai_model = "Grok-3-beta"

description_folder = r"C:\Users\berti\EvaluatingLLMsProcessModeling\ground_truth\ground_truth_process_descriptions\long"
ground_truth_log_folder = r"C:\Users\berti\EvaluatingLLMsProcessModeling\ground_truth\ground_truth_xes_one_trace_per_variant"

base_dir = f"llm_com/{openai_model.replace('/', '_').replace(':', '')}/IT{ITERATION}"

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

    print(proc_id, proc_file)
    # Check if the corresponding ground truth file exists
    if not os.path.exists(ground_truth_log_path):
        raise Exception(f"Ground truth file not found for {proc_file}, skipping.")

    # Load process description
    proc_descr = open(os.path.join(description_folder, proc_file), "r").read().strip()

    # Load ground truth log
    ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)
    log_activities = set(event["concept:name"] for trace in ground_truth_log for event in trace)
    activities_in_ground_truth = log_activities

    # Append instructions to use ground truth activities
    proc_descr += "\n\nEnsure the generated model uses the following activity labels (please also note upper and lower case): " + ", ".join(log_activities)
    init_conversation = create_conversation(proc_descr)

    start_time = time.time()
    try:
        if MANUAL:
            # Manual mode: copy prompt to clipboard and open Notepad on a designated file
            manual_file = os.path.join(base_dir, f"{proc_id}_manual_response.txt")
            # Copy the prompt to the clipboard
            pyperclip.copy(init_conversation[0]["content"])

            if os.path.exists(manual_file):
                # Create/clear the manual file so the user can edit it
                F = open(manual_file, "r", encoding="utf-8")
                current_content = F.read().strip()
                F.close()

                if current_content:
                    continue

            F = open(manual_file, "w", encoding="utf-8")
            F.close()

            # Open Notepad and wait until it is closed
            subprocess.run(["notepad.exe", manual_file])

            # Initialize manual iteration counter
            manual_iteration_count = 0

            # Loop until the extraction succeeds
            while True:
                manual_iteration_count += 1
                with open(manual_file, "r", encoding="utf-8") as f:
                    response_text = f.read()
                try:
                    # Attempt to extract the model from the response text
                    code, process_model = extract_model_from_response(response_text, auto_duplicate=True)
                    powl = process_model
                except Exception as extraction_error:
                    print("Error extracting model from response:", extraction_error)
                    # Re-copy the same prompt to clipboard and re-open Notepad for editing
                    pyperclip.copy(init_conversation[0]["content"])
                    subprocess.run(["notepad.exe", manual_file])
                else:
                    break

            # In manual mode, we assign the response as the "code"
            # Create a conversation history with two turns: the prompt and the manual response
            conversation = [init_conversation, response_text]
        else:
            # Automatic mode: generate the model using the LLM API
            code, process_model, conversation = generate_model(
                init_conversation,
                api_key=api_key,
                llm_name=openai_model,
                api_url=api_url,
                max_iterations=10,
                additional_iterations=5
            )
            powl = process_model

        end_time = time.time()
        time_difference = str(end_time - start_time)
    except Exception as e:
        traceback.print_exc()
        end_time = time.time()
        time_difference = str(end_time - start_time)
        stats = {
            "log_name": proc_file,
            "num_it": "Error",
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": "None",
            "shared_activities": "None",
            "time": time_difference,
            "error message": str(e)
        }
        print(e)
    else:
        conversation_history = conversation
        # Convert the extracted model (powl) to a Petri net
        net, im, fm = pm4py.convert_to_petri_net(powl)
        activities_in_generated = [x for x in net.transitions if x.label is not None]

        # Save Petri net
        pnml_path = os.path.join(pn_folder, f"{proc_id}.pnml")
        if CREATE_FILES:
            pm4py.write_pnml(net, im, fm, pnml_path)

        # Save conversation history and code
        conversation_path = os.path.join(conv_folder, f"{proc_id}.txt")
        code_path = os.path.join(code_folder, f"{proc_id}.txt")
        if CREATE_FILES:
            with open(conversation_path, "w", encoding="utf-8") as conv_file:
                conv_file.write(str(conversation_history))
            with open(code_path, "w", encoding="utf-8") as code_file:
                code_file.write(str(code))

        # Compare with ground truth
        shared_activities = len(set(t.label for t in net.transitions if t.label) & log_activities)

        # Use different iteration counting based on manual mode
        if MANUAL:
            num_iterations = manual_iteration_count
        else:
            num_iterations = len(conversation_history) / 2

        stats = {
            "log_name": proc_file,
            "num_it": num_iterations,
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": len(activities_in_generated),
            "shared_activities": shared_activities,
            "time": time_difference,
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
                stats["time"],
                stats["error message"]
            ])

    print(stats)
    # Optionally, you can also save the statistics table to a JSON file
