import csv
import os

import pm4py

from utils.general_utils.openai_connection import generate_result_with_error_handling
from utils.prompting import create_conversation
from utils.prompting.self_evaluation import extraction_function_dictionary, generate_self_evaluation_prompt

# IDS_TO_CONSIDER = [f"{i:02}" for i in range(1, 21)]  # '01' to '20'
IDS_TO_CONSIDER = [f"{i:02}" for i in range(1, 3)]  # '01' to '20'
ITERATIONS = 1

with open("../api_url.txt", "r") as f:
    api_url = f.read().strip()
with open("../api_key.txt", "r") as f:
    api_key = f.read().strip()
with open("../api_model.txt", "r") as f:
    llm_name = f.read().strip()

description_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_process_descriptions"
ground_truth_log_folder = r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\ground_truth_xes_one_trace_per_variant"
llm_name_fixed = f"{llm_name.replace('/', '_')}"
base_dir = f"llm_com/{llm_name_fixed}"

self_ev_folder = os.path.join(r"C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation", 'self_ev', llm_name_fixed)
responses_folder = os.path.join(self_ev_folder, 'responses')

if not os.path.exists(responses_folder):
    os.makedirs(responses_folder)

statistics_csv_file = os.path.join(self_ev_folder, "self_ev_scores.csv")

if not os.path.exists(statistics_csv_file):
    with open(statistics_csv_file, "w", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
                                "log_name",
                                "len_conv"
                            ]
                            + [f'IT{iteration}' for iteration in range(1, ITERATIONS + 1)]
                            )

# Main Loop
for proc_id in IDS_TO_CONSIDER:

    proc_descr = open(os.path.join(description_folder, f"{proc_id}.txt"), "r").read().strip()

    ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}.xes")
    ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)

    log_activities = set(event["concept:name"] for trace in ground_truth_log for event in trace)
    proc_descr += "\n\nEnsure the generated model uses the following activity labels (please also note upper and" \
                  " lower case): " + ", ".join(log_activities) + "\n\n"

    model_codes = {}

    for iteration in range(1, ITERATIONS + 1):
        iteration_id = f'IT{iteration}'
        model_codes[iteration_id] = open(os.path.join(base_dir, iteration_id, 'code', f"{proc_id}.txt"),
                                         "r").read().strip()

    init_conversation = create_conversation(None)

    KEYS = list(model_codes.keys())

    def extraction_function_with_keys(response: str, iteration):
        return extraction_function_dictionary(response, keys=KEYS)


    self_ev_prompt = generate_self_evaluation_prompt(proc_descr, model_codes)

    init_conversation.append({"role": "user", "content": f'{self_ev_prompt}'})

    error_message = ""

    code, result, conversation = generate_result_with_error_handling(init_conversation,
                                                                     llm_name=llm_name,
                                                                     api_key=api_key,
                                                                     api_url=api_url,
                                                                     extraction_function=extraction_function_with_keys,
                                                                     standard_error_message=error_message)

    response_path = os.path.join(responses_folder, f"{proc_id}.txt")
    with open(response_path, "w", encoding="utf-8") as f:
        f.write(conversation[-1]["content"])

    with open(statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([proc_id, len(conversation)]
                            + [result[f'IT{iteration}'] for iteration in range(1, ITERATIONS + 1)])

    print(f"Scores for {proc_id}: {result}")

print("Scoring completed.")
