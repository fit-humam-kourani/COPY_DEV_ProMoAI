import pm4py
from utils import llm_model_generator
from utils.general_utils import pt_to_powl_code


def execute_script():
    api_url = open("api_url.txt", "r").read().strip()
    api_key = open("api_key.txt", "r").read().strip()
    openai_model = open("api_model.txt", "r").read().strip()
    feedback = "Can you add an activity Throw Chair in the end"

    bpmn_graph = pm4py.read_bpmn("running-example.bpmn")
    # works for BPMNs that are block-structured in the control-flow
    process_tree = pm4py.convert_to_process_tree(bpmn_graph)
    powl_code = pt_to_powl_code.recursively_transform_process_tree(process_tree)
    obj = llm_model_generator.initialize(None, api_key=api_key,
                                   powl_model_code=powl_code, openai_model=openai_model, api_url=api_url)
    obj = llm_model_generator.update(obj, feedback, api_key=api_key, openai_model=openai_model, api_url=api_url)
    obj.view_bpmn("svg")


if __name__ == "__main__":
    execute_script()
