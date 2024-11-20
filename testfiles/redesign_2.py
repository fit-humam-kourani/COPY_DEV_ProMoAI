import os
import pm4py
from utils.general_utils import pt_to_powl_code
from utils import llm_model_generator


api_url = open("api_url.txt", "r").read().strip()
api_key = open("api_key.txt", "r").read().strip()
openai_model = open("api_model.txt", "r").read().strip()

for bpmn_file in os.listdir("bpmn"):
    print("\n\n")
    print(bpmn_file)

    xes_file = bpmn_file.replace(".bpmn", ".xes.gz")

    bpmn_graph = pm4py.read_bpmn(os.path.join("bpmn", bpmn_file))
    process_tree = pm4py.convert_to_process_tree(bpmn_graph)
    net, im, fm = pm4py.convert_to_petri_net(process_tree)
    num_visible = len([x for x in net.transitions if x.label is not None])
    log = pm4py.read_xes(os.path.join("xes", xes_file), return_legacy_log_object=True)

    powl_code = pt_to_powl_code.recursively_transform_process_tree(process_tree)

    obj = llm_model_generator.initialize(None, api_key=api_key,
                                         powl_model_code=powl_code, openai_model=openai_model, api_url=api_url, debug=False)

    feedback = "These are the process variants of the log, any suggested improvement to the model?\n\n"+pm4py.llm.abstract_variants(log, response_header=False)

    obj = llm_model_generator.update(obj, feedback, debug=False, api_key=api_key, openai_model=openai_model, api_url=api_url)
    grade2 = obj.grade_process_model()
    print("grade2", grade2)

    powl2 = obj.process_model
    net2, im2, fm2 = pm4py.convert_to_petri_net(powl2)
    num_visible2 = len([x for x in net2.transitions if x.label is not None])

    fitness_tbr2 = pm4py.fitness_token_based_replay(log, net2, im2, fm2)["log_fitness"]
    precision_tbr2 = pm4py.precision_token_based_replay(log, net2, im2, fm2)

    print("fitness2", fitness_tbr2, "\tprecision2", precision_tbr2, "\tgrade2", grade2, "\tnum_visible2", num_visible2)

    #break
