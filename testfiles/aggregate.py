import os
import json
import numpy as np


api_url = open("api_url.txt", "r").read().strip()
api_key = open("api_key.txt", "r").read().strip()
openai_model = open("api_model.txt", "r").read().strip().replace("/", "").replace(":", "").strip()
n_candidates = 1
improve_initial_prompt = "0"
improve_resulting_model = "0"

agg_cat = {}

for file in os.listdir("results"):
    file_split = file.split("__")

    if len(file_split) == 6:
        model = file_split[0]
        cat = file_split[1]
        ite = file_split[2]
        pi = file_split[3]
        mi = file_split[4]

        if model == openai_model and ite == str(n_candidates) and pi == improve_initial_prompt and mi == improve_resulting_model:
            contents = json.load(open(os.path.join("results", file), "r"))
            if cat not in agg_cat:
                agg_cat[cat] = {"visible_transitions": [], "self_grading": [], "n_iterations": []}

            agg_cat[cat]["visible_transitions"].append(contents["visible_transitions"])
            agg_cat[cat]["self_grading"].append(contents["self_grading"])
            agg_cat[cat]["n_iterations"].append(contents["n_iterations"])


for cat in agg_cat:
    agg_cat[cat]["visible_transitions"] = (float(np.mean(agg_cat[cat]["visible_transitions"])), float(np.std(agg_cat[cat]["visible_transitions"])))
    agg_cat[cat]["self_grading"] = (float(np.mean(agg_cat[cat]["self_grading"])), float(np.std(agg_cat[cat]["self_grading"])))
    agg_cat[cat]["n_iterations"] = (float(np.mean(agg_cat[cat]["n_iterations"])), float(np.std(agg_cat[cat]["n_iterations"])))

    agg_cat[cat]["visible_transitions"] = "%.1f pm %.1f" % (agg_cat[cat]["visible_transitions"][0], agg_cat[cat]["visible_transitions"][1])
    agg_cat[cat]["self_grading"] = "%.1f pm %.1f" % (agg_cat[cat]["self_grading"][0], agg_cat[cat]["self_grading"][1])
    agg_cat[cat]["n_iterations"] = "%.1f pm %.1f" % (agg_cat[cat]["n_iterations"][0], agg_cat[cat]["n_iterations"][1])

    print(cat, "visible_transitions", agg_cat[cat]["visible_transitions"], "\tself_grading", agg_cat[cat]["self_grading"], "\tn_iterations", agg_cat[cat]["n_iterations"])
