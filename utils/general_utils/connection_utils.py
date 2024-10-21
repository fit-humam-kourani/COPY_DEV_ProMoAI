from utils.general_utils import openai_connection
from utils.prompting.prompt_engineering import description_self_improvement_prompt


def improve_process_description(description: str,  api_key, openai_model, api_url: str = "https://api.openai.com/v1") -> str:

    conversation = [{"role": "user", "content": description_self_improvement_prompt(description)}]
    improved_description = openai_connection.generate_response_with_history(conversation,
                                                                            api_key=api_key,
                                                                            openai_model=openai_model,
                                                                            api_url=api_url)
    return improved_description
