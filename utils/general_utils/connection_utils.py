from utils.general_utils.ai_providers import AIProviders
from utils.general_utils.openai_connection import generate_response_with_history_google, \
    generate_response_with_history_anthropic, generate_response_with_history
from utils.prompting.prompt_engineering import description_self_improvement_prompt


def improve_process_description(description: str,  api_key, llm_name, ai_provider: str) -> str:

    conversation = [{"role": "user", "content": description_self_improvement_prompt(description)}]

    if ai_provider == AIProviders.GOOGLE.value:
        improved_description = generate_response_with_history_google(conversation, api_key, llm_name)
    elif ai_provider == AIProviders.ANTHROPIC.value:
        improved_description = generate_response_with_history_anthropic(conversation, api_key, llm_name)
    else:
        if ai_provider == AIProviders.DEEPINFRA.value:
            api_url = "https://api.deepinfra.com/v1/openai"
        elif ai_provider == AIProviders.OPENAI.value:
            api_url = "https://api.openai.com/v1"
        elif ai_provider == AIProviders.MISTRAL_AI.value:
            api_url = "https://api.mistral.ai/v1/"
        else:
            raise Exception(f"AI provider {ai_provider} is not supported!")
        improved_description = generate_response_with_history(conversation, api_key, llm_name, api_url)

    print(conversation)
    return improved_description
