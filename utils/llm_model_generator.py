from pm4py.objects.powl.obj import POWL

from utils.prompting import create_conversation, update_conversation
from utils.model_generation.model_generation import generate_model, extract_model_from_response
from utils.general_utils import openai_connection
from pm4py.util import constants
from copy import copy, deepcopy
from typing import Optional
import re


class LLMProcessModelGenerator(object):
    def __init__(self, process_description: Optional[str], api_key: str, openai_model: str,
                 api_url: str = "https://api.openai.com/v1", powl_model_code: str = None, powl_model: POWL = None):
        self.api_url = api_url
        self.api_key = api_key
        self.openai_model = openai_model
        init_conversation = create_conversation(process_description)
        if process_description is not None:
            self.process_model, self.conversation = generate_model(init_conversation,
                                                                   api_key=self.api_key,
                                                                   openai_model=self.openai_model,
                                                                   api_url=self.api_url)
        elif powl_model:
            conversation = list(init_conversation)
            conversation.append({"role": "assistant",
                                 "content": "We have the following POWL model already created: "
                                            "on the user's feedback:\n\n" + str(powl_model)})
            self.process_model = powl_model
            self.conversation = conversation
        elif powl_model_code:
            process_model = extract_model_from_response(powl_model_code, 0)
            conversation = list(init_conversation)
            conversation.append({"role": "assistant", "content": "The following code is used to generate the process model:\n\n"+powl_model_code})
            self.process_model = process_model
            self.conversation = conversation
        else:
            raise Exception("insufficient parameters provided to LLMProcessModelGenerator. at least one between 'process_description' and 'powl_model_code' should be provided.")

    def __to_petri_net(self):
        from pm4py.objects.conversion.powl.converter import apply as powl_to_pn
        net, im, fm = powl_to_pn(self.process_model)
        return net, im, fm

    def get_powl(self):
        return self.process_model

    def get_bpmn(self):
        net, im, fm = self.__to_petri_net()
        from pm4py.objects.conversion.wf_net.variants.to_bpmn import apply as pn_to_bpmn
        bpmn_model = pn_to_bpmn(net, im, fm)
        from pm4py.objects.bpmn.layout import layouter
        bpmn_model = layouter.apply(bpmn_model)
        return bpmn_model

    def update(self, feedback: str, api_key: str, openai_model: str, api_url: str = "https://api.openai.com/v1"):
        self.api_url = api_url
        self.api_key = api_key
        self.openai_model = openai_model
        self.conversation = update_conversation(self.conversation, feedback)
        self.process_model, self.conversation = generate_model(conversation=self.conversation,
                                                               api_key=self.api_key,
                                                               openai_model=self.openai_model,
                                                               api_url=self.api_url)

    def view_bpmn(self, image_format: str = "svg"):
        bpmn_model = self.get_bpmn()
        image_format = str(image_format).lower()
        from pm4py.visualization.bpmn import visualizer as bpmn_visualizer
        parameters = bpmn_visualizer.Variants.CLASSIC.value.Parameters
        visualization = bpmn_visualizer.apply(bpmn_model,
                                              parameters={parameters.FORMAT: image_format})
        bpmn_visualizer.view(visualization)

    def view_petri_net(self, image_format: str = "svg"):
        net, im, fm = self.__to_petri_net()
        image_format = str(image_format).lower()
        from pm4py.visualization.petri_net import visualizer as petri_net_visualizer
        parameters = petri_net_visualizer.Variants.WO_DECORATION.value.Parameters
        visualization = petri_net_visualizer.apply(net, im, fm,
                                                   parameters={parameters.FORMAT: image_format})
        petri_net_visualizer.view(visualization)

    def view_powl(self, image_format: str = "svg"):
        image_format = str(image_format).lower()
        from pm4py.visualization.powl import visualizer as powl_visualizer
        parameters = powl_visualizer.POWLVisualizationVariants.BASIC.value.Parameters
        visualization = powl_visualizer.apply(self.process_model,
                                              parameters={parameters.FORMAT: image_format})
        powl_visualizer.view(visualization)

    def export_bpmn(self, file_path: str, encoding: str = constants.DEFAULT_ENCODING):
        if not file_path.lower().endswith("bpmn"):
            raise Exception("The provided file path does not have the '.bpmn' extension!")
        bpmn_model = self.get_bpmn()
        from pm4py.objects.bpmn.exporter import exporter
        exporter.apply(bpmn_model, file_path, parameters={"encoding": encoding})

    def export_petri_net(self, file_path: str, encoding: str = constants.DEFAULT_ENCODING):
        if not file_path.lower().endswith("pnml"):
            raise Exception("The provided file path does not have the '.pnml' extension!")
        net, im, fm = self.__to_petri_net()
        from pm4py.objects.petri_net.exporter import exporter as petri_exporter
        petri_exporter.apply(net=net,
                             initial_marking=im,
                             final_marking=fm,
                             output_filename=file_path,
                             parameters={"encoding": encoding})

    def grade_process_model(self, api_key: str, openai_model: str, api_url: str = "https://api.openai.com/v1"):
        self.api_url = api_url
        self.api_key = api_key
        self.openai_model = openai_model
        conversation = copy(self.conversation)
        conversation.append({"role": "user", "content": "Could you provide a grade from 1.0 (minimum) to 10.0 (maximum) to the provided process model? Please explain briefly your motivations. Please put the overall grade at the beginning of your response."})
        response = openai_connection.generate_response_with_history(conversation, self.api_key, self.openai_model, self.api_url)
        pattern = r'\d+'
        reg_expr = re.compile(pattern)
        numbers = reg_expr.findall(response)
        if numbers:
            return float(numbers[0])
        return 0.0


def initialize(process_description: str | None, api_key: str, openai_model: str, api_url: str = "https://api.openai.com/v1",
               powl_model_code: str = None, powl_model: POWL = None, n_candidates: int = 1, debug: bool = False):
    best_grade = -1.0
    best_cand = None
    exception = ""
    for i in range(n_candidates):
        try:
            cand = LLMProcessModelGenerator(process_description=process_description, api_key=api_key,
                                            openai_model=openai_model, api_url=api_url,
                                            powl_model_code=powl_model_code, powl_model=powl_model)
            if n_candidates > 1:
                grade = cand.grade_process_model(api_key, openai_model, api_url)
                if grade > best_grade:
                    best_grade = grade
                    best_cand = cand
                if debug:
                    print("i=%d n_candidates=%d grade=%.2f best_grade=%.2f" % (i, n_candidates, grade, best_grade))
            else:
                best_cand = cand
        except Exception as e:
            exception = str(e)
    if best_cand is None:
        raise Exception(exception)
    return best_cand


def update(generator: LLMProcessModelGenerator, feedback: str, api_key: str, openai_model: str, api_url: str = "https://api.openai.com/v1", n_candidates: int = 1, debug: bool = False):
    best_grade = -1.0
    best_cand = None
    exception = ""
    for i in range(n_candidates):
        try:
            cand = generator if n_candidates == 1 else deepcopy(generator)
            cand.update(feedback, api_key, openai_model, api_url)
            if n_candidates > 1:
                grade = cand.grade_process_model(api_key, openai_model, api_url)
                if grade > best_grade:
                    best_grade = grade
                    best_cand = cand
                if debug:
                    print("i=%d n_candidates=%d grade=%.2f best_grade=%.2f" % (i, n_candidates, grade, best_grade))
            else:
                best_cand = cand
        except Exception as e:
            exception = str(e)
    if best_cand is None:
        raise Exception(exception)
    return best_cand
