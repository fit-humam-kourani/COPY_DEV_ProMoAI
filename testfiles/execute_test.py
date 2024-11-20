import os
import pm4py
import json
from utils import llm_model_generator, shared
from utils.general_utils import connection_utils


api_url = open("api_url.txt", "r").read().strip()
api_key = open("api_key.txt", "r").read().strip()
openai_model = open("api_model.txt", "r").read().strip()
n_candidates = 1
improve_initial_prompt = "0"
improve_resulting_model = "0"


folders = ["short", "medium", "long"]

for fold in folders:
    for proc_file in os.listdir(fold):
        output_file = os.path.join("results", openai_model.replace("/", "").replace(":", "")+"__"+fold+"__"+str(n_candidates)+"__"+improve_initial_prompt+"__"+improve_resulting_model+"__"+proc_file)
        proc_descr = open(os.path.join(fold, proc_file), "r").read().strip()

        if not os.path.exists(output_file):
            try:
                if improve_initial_prompt == "1":
                    proc_descr = connection_utils.improve_process_description(proc_descr, api_key, openai_model, api_url=api_url)

                obj = llm_model_generator.initialize(process_description=proc_descr, api_key=api_key, openai_model=openai_model,
                                                     api_url=api_url, n_candidates=n_candidates, debug=False)

                if improve_resulting_model == "1":
                    feedback = "Please improve the process model. For example, typical improvement steps include additional activities, managing a greater number of exceptions, or increasing the concurrency in the execution of the process."

                    obj = llm_model_generator.update(obj, feedback, n_candidates=n_candidates, debug=False, api_key=api_key, openai_model=openai_model, api_url=api_url)

                powl = obj.process_model
                net, im, fm = pm4py.convert_to_petri_net(powl)
                visible_transitions = [x for x in net.transitions if x.label is not None]

                #reachability_graph = pm4py.convert_to_reachability_graph(net, im, fm)

                dictio = {"visible_transitions": len(visible_transitions), "n_iterations": shared.LAST_ITERATIONS, "self_grading": obj.grade_process_model()}

                F = open(output_file, "w")
                json.dump(dictio, F)
                F.close()
            except:
                pass

        #break
    #break
