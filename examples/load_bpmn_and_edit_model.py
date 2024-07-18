import pm4py
from utils import llm_model_generator
from utils.general_utils import pt_to_powl_code


def execute_script():
    bpmn_graph = pm4py.read_bpmn("running-example.bpmn")
    # works for BPMNs that are block-structured in the control-flow
    process_tree = pm4py.convert_to_process_tree(bpmn_graph)
    powl_code = pt_to_powl_code.recursively_transform_process_tree(process_tree)
    obj = llm_model_generator.initialize(None, "sk-",
                                   powl_model_code=powl_code, openai_model="gpt-4o")
    obj.update("Can you add an activity Throw Chair in the end")
    obj.view_bpmn("svg")


if __name__ == "__main__":
    execute_script()