from utils.general_utils import openai_connection
from utils.general_utils.openai_connection import generate_response_with_history_google, \
    generate_response_with_history_anthropic, generate_response_with_history
from utils.prompting.prompt_engineering import description_self_improvement_prompt


def improve_process_description(description: str,  api_key, llm_name, api_url: str = "https://api.openai.com/v1") -> str:

    conversation = [{"role": "user", "content": description_self_improvement_prompt(description)}]

    if api_url == "GOOGLE":
        improved_description = generate_response_with_history_google(conversation, api_key, llm_name)
    elif api_url == "https://api.anthropic.com/v1/messages":
        improved_description = generate_response_with_history_anthropic(conversation, api_key, llm_name)
    else:
        improved_description = generate_response_with_history(conversation, api_key, llm_name, api_url)

    print(conversation)
    return improved_description
