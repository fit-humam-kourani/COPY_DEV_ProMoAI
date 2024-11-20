from utils import llm_model_generator, shared


def execute_script():
    proc_descr = "A then B then C"
    api_url = open("api_url.txt", "r").read().strip()
    api_key = open("api_key.txt", "r").read().strip()
    openai_model = open("api_model.txt", "r").read().strip()
    n_candidates = 1

    obj = llm_model_generator.initialize(process_description=proc_descr, api_key=api_key, openai_model=openai_model, api_url=api_url, n_candidates=n_candidates)
    print(obj.grade_process_model())
    print("Number of required iterations:", str(shared.LAST_ITERATIONS))
    obj.view_bpmn("svg")


if __name__ == "__main__":
    execute_script()
