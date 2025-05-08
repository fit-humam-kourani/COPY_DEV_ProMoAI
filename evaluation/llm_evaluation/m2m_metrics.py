import pandas as pd
import pm4py
import traceback
import os


def execute_script(evaluated_llm):
    final_model = None

    # base_path = os.path.join("evaluation", "llm_evaluation")
    base_path = "."

    folder_ground_truth_logs = os.path.join(base_path, "ground_truth", "ground_truth_xes_one_trace_per_variant")
    folder_ground_truth_models = os.path.join(base_path, "ground_truth", "ground_truth_code")
    folder_llm = os.path.join(base_path, "llm_com", evaluated_llm, "IT1")
    folder_this_models = os.path.join(folder_llm, "code")

    dataframe = []

    for file in os.listdir(folder_this_models):
        dictio = {}
        gt_model = open(os.path.join(folder_ground_truth_models, file), "r").read()
        exec(gt_model, dictio)
        gt_model = dictio["final_model"]

        gt_log = pm4py.read_xes(os.path.join(folder_ground_truth_logs, file.replace("txt", "xes")),
                                return_legacy_log_object=True)

        dictio = {}
        thi_model = open(os.path.join(folder_this_models, file), "r").read()
        exec(thi_model, dictio)
        thi_model = dictio["final_model"]

        label_set_simil = pm4py.label_sets_similarity(thi_model, gt_model)
        behav_fps_simil = pm4py.behavioral_similarity(thi_model, gt_model)
        structural_simil = pm4py.structural_similarity(thi_model, gt_model)
        embeddings_simil = pm4py.embeddings_similarity(thi_model, gt_model)

        net, im, fm = pm4py.convert_to_petri_net(thi_model)
        fitness_tbr = pm4py.fitness_token_based_replay(gt_log, net, im, fm)["log_fitness"]
        precision_tbr = pm4py.precision_token_based_replay(gt_log, net, im, fm)
        den = (fitness_tbr + precision_tbr)
        f_score_tbr = (2 * fitness_tbr * precision_tbr) / den if den > 0 else 0.0

        footprints_thi = pm4py.discover_footprints(thi_model)
        footprints_log = pm4py.discover_footprints(gt_log)
        fitness_fps = pm4py.fitness_footprints(footprints_log, footprints_thi)["log_fitness"]
        precision_fps = pm4py.precision_footprints(footprints_log, footprints_thi)
        den = (fitness_fps + precision_fps)
        f_score_fps = (2 * fitness_fps * precision_fps) / den if den > 0 else 0.0

        dataframe.append({"file": file, "f_score_tbr": f_score_tbr, "f_score_fps": f_score_fps, \
                          "label_set_simil": label_set_simil, \
                          "behav_fps_simil": behav_fps_simil, "structural_simil": structural_simil, \
                          "embeddings_simil": embeddings_simil})

    dataframe = pd.DataFrame(dataframe)

    dictio = {}
    dictio["model"] = evaluated_llm
    dictio["f_score_tbr_avg"] = dataframe["f_score_tbr"].mean()
    dictio["f_score_fps_avg"] = dataframe["f_score_fps"].mean()

    dictio["label_set_simil_avg"] = dataframe["label_set_simil"].mean()
    dictio["behav_fps_simil_avg"] = dataframe["behav_fps_simil"].mean()
    dictio["structural_simil_avg"] = dataframe["structural_simil"].mean()
    dictio["embeddings_simil_avg"] = dataframe["embeddings_simil"].mean()

    return dictio


def create_results_df(target_llms):
    dataframe = []
    print(len(target_llms))
    for index, llm in enumerate(target_llms):
        try:
            print(index, llm)
            dataframe.append(execute_script(llm))
        except:
            traceback.print_exc()

    dataframe = pd.DataFrame(dataframe)
    dataframe.columns = ["model", "f_score_tbr_avg", "f_score_fps_avg", "label_set_simil_avg", "behav_fps_simil_avg",
                         "structural_simil_avg", "embeddings_simil_avg"]

    dataframe.sort_values(["f_score_tbr_avg", "model"], ascending=False, inplace=True)
    return dataframe


if __name__ == "__main__":
    dataframe = create_results_df([x for x in os.listdir("llm_com") if "." not in x])
    print(dataframe)
    dataframe.to_csv("overall_m2m_metrics.csv", index=False)
