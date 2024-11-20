import csv
import os
import pm4py
import json

from selenium.webdriver.common.by import By

from evaluation.chatgpt import ChatGPTAutomation
from utils import constants
from utils.general_utils.openai_connection import print_conversation
from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges
from utils.prompting import create_conversation
import time

# IDS_TO_CONSIDER = ['17', '18', 'order', 'hotel']
IDS_TO_CONSIDER = None
CREATE_FILES = True
ITERATION = 2

# Read API configurations
# openai_model = "o1-mini"
openai_model = "gpt-4o"

# Define directories for reading input and saving results
description_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_process_descriptions"
# ground_truth_pn_folder = "../testfiles/ground_truth_pn"
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

chatgpt = ChatGPTAutomation(model=openai_model)

statistics_csv_file = os.path.join(base_dir, "results_statistics.csv")
if CREATE_FILES:
    with open(statistics_csv_file, "a", newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write the header
        csv_writer.writerow([
            "log_name",
            "conversation_length",
            "visible_transitions_ground_truth",
            "visible_transitions_generated",
            "shared_activities",
            "percFitTraces",
            "averageFitness",
            "percentage_of_fitting_traces",
            "average_trace_fitness",
            "log_fitness",
            "precision"
        ])


def generate_model_with_chatgpt(input_conversation):
    max_iterations = 10
    error_history = []
    for iteration in range(max_iterations+5):
        prompt = input_conversation[-1]['content']
        chatgpt.send_prompt_to_chatgpt(prompt)
        try:
            div = chatgpt.return_last_response()
            response = div.text
            input_conversation.append({"role": "assistant", "content": response})
            python_code_element = div.find_elements(
                By.CSS_SELECTOR,
                'code.language-python'
            )
            if python_code_element:
                if len(python_code_element) > 1:
                    raise Exception("Multiple Python code snippets found!")
                model_code = python_code_element[0].text
            else:
                raise Exception("No Python code found!")
            variable_name = 'final_model'
            auto_duplicate = iteration >= max_iterations
            if auto_duplicate:
                model_code = model_code.replace('ModelGenerator()', 'ModelGenerator(True, True)')
                print(f"START DUPLICATING at {iteration+1}th iteration")
            result = execute_code_and_get_variable(model_code, variable_name)
            # validate_unique_transitions(result)
            validate_partial_orders_with_missing_transitive_edges(result)
            print_conversation(input_conversation)
            return model_code, result, input_conversation  # Break loop if execution is successful
        except Exception as e:
            error_description = str(e)
            error_history.append(error_description)
            if constants.ENABLE_PRINTS:
                print("Error detected in iteration " + str(iteration + 1))
            new_message = f"Executing your code led to an error! Please update the model to fix the error. Make sure" \
                          f" to save the updated final model is the variable 'final_model'. This is the error" \
                          f" message: {error_description}"
            input_conversation.append({"role": "user", "content": new_message})

        print_conversation(input_conversation)

    raise Exception(openai_model + " failed to fix the errors after " + str(max_iterations+5) +
                    " iterations! This is the error history: " + str(error_history))


for proc_file in os.listdir(description_folder):
    # Get process ID from file name (e.g., "01.txt")
    proc_id = os.path.splitext(proc_file)[0]

    if IDS_TO_CONSIDER and proc_id not in IDS_TO_CONSIDER:
        continue

    # Define paths for ground truth Petri net and log
    # ground_truth_pn_path = os.path.join(ground_truth_pn_folder, f"{proc_id}_ground_truth_petri.pnml")
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
    proc_descr += "\n\nEnsure the generated model uses the following activity labels (please also note upper and lower case): " + ", ".join(
        log_activities)
    activities_in_ground_truth = log_activities
    init_conversation = create_conversation(proc_descr)
    start_time = time.time()
    try:
        code, process_model, conversation = generate_model_with_chatgpt(input_conversation=init_conversation)
        end_time = time.time()
        time_difference = str(end_time - start_time - (5 * len(conversation) / 2))
    except Exception as e:
        end_time = time.time()
        num_iterations = 15
        time_difference = str(end_time - start_time - (5 * num_iterations))
        stats = {
            "log_name": proc_file,
            "conversation_length": "Error",
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": "None",
            "shared_activities": "None",
            "fitness": "None",
            "precision": "None",
            "time (sec)": time_difference,
            "error": str(e)
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
        fitness = "skipped"
        precision = "skipped"

        # Extract statistics
        stats = {
            "log_name": proc_file,
            "conversation_length": len(conversation_history),
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": len(activities_in_generated),
            "shared_activities": shared_activities,
            "fitness": fitness,
            "precision": precision,
            "time (sec)": time_difference
        }

    chatgpt.reload_page()

    # Save statistics
    results_table.append(stats)

    if CREATE_FILES:
        # Append to CSV for every iteration
        with open(statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                stats["log_name"],
                stats["conversation_length"],
                stats["visible_transitions_ground_truth"],
                stats["visible_transitions_generated"],
                stats["shared_activities"],
                # stats["fitness"]["percFitTraces"] if stats["fitness"] != "None" else "None",
                # stats["fitness"]["averageFitness"] if stats["fitness"] != "None" else "None",
                # stats["fitness"]["percentage_of_fitting_traces"] if stats["fitness"] != "None" else "None",
                # stats["fitness"]["average_trace_fitness"] if stats["fitness"] != "None" else "None",
                # stats["fitness"]["log_fitness"] if stats["fitness"] != "None" else "None",
                "skipped",
                "skipped",
                "skipped",
                "skipped",
                "skipped",
                stats["precision"],
                stats["time (sec)"]
            ])

    print(stats)
    if CREATE_FILES:
        # Save the statistics table
        statistics_file = os.path.join(base_dir, "results_statistics.json")
        with open(statistics_file, "a") as stats_file:
            json.dump(stats, stats_file, indent=4)

chatgpt.quit()
