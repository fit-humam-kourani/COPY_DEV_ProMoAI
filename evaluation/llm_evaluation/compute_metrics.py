import csv
import os
import pm4py

LLM_NAME = 'gemini-1.5-pro-002'
ITERATION = 4

ground_truth_log_folder = "../testfiles/ground_truth_xes_one_trace_per_variant"
base_dir = f"llm_com/{LLM_NAME}/IT{ITERATION}"

metrics_data = {
    "ALIGN_percentage_of_fitting_traces": [],
    "ALIGN_average_trace_fitness": [],
    "ALIGN_precision": [],
    "ALIGN_f_measure": []
}

process_ids = [f"{i:02}" for i in range(1, 19)] + ['order', 'hotel']
special_mapping = {'order': '19', 'hotel': '20'}

results_csv_file = os.path.join(base_dir, "ALIGN_metrics.csv")
file_exists = os.path.exists(results_csv_file)
with open(results_csv_file, "a", newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "process_id",
        "fitness_percFitTraces",
        "averageFitness",
        "precision",
        "f_measure"
    ])


# Function to compute f-measure
def f_measure(precision, fitness):
    if precision + fitness == 0:
        return 0
    return 2 * (precision * fitness) / (precision + fitness)


# Process each file
for proc_id in process_ids:
    ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}_ground_truth_log.xes")
    generated_pn_path = os.path.join(base_dir, 'pn', f"{proc_id}.txt.pnml")

    if os.path.exists(generated_pn_path):

        ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)
        generated_net, generated_im, generated_fm = pm4py.read_pnml(generated_pn_path)

        fitness = pm4py.fitness_alignments(ground_truth_log, generated_net, generated_im, generated_fm)
        fit_perc = fitness['percFitTraces']
        fit_avg = fitness['averageFitness']
        precision = pm4py.precision_alignments(ground_truth_log, generated_net, generated_im, generated_fm)
        f_measure_score = f_measure(precision, fit_avg)
    else:
        fit_perc = fit_avg = precision = f_measure_score = "nan"

    with open(results_csv_file, "a", newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            special_mapping.get(proc_id, proc_id),
            fit_perc,
            fit_avg,
            precision,
            f_measure_score
        ])

    metrics_data["ALIGN_percentage_of_fitting_traces"].append(fit_perc)
    metrics_data["ALIGN_average_trace_fitness"].append(fit_avg)
    metrics_data["ALIGN_precision"].append(precision)
    metrics_data["ALIGN_f_measure"].append(f_measure_score)

for metric_name, values in metrics_data.items():
    metric_csv_file = os.path.join("llm_com", f"{metric_name}.csv")
    with open(metric_csv_file, "a", newline='') as file:
        writer = csv.writer(file)
        # if not os.path.exists(metric_csv_file) or os.path.getsize(metric_csv_file) == 0:
        #     writer.writerow(["model_name"] + [f"{special_mapping.get(i, i)}" for i in process_ids])
        writer.writerow([LLM_NAME] + values)
