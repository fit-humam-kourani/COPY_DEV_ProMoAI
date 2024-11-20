import sys
from typing import Callable, List, TypeVar, Any
from utils import constants
import requests

from utils.general_utils.ai_providers import AIProviders
from utils.prompting.prompt_engineering import ERROR_MESSAGE_FOR_MODEL_GENERATION

T = TypeVar('T')


def generate_result_with_error_handling(conversation: List[dict[str:str]],
                                        extraction_function: Callable[[str, Any], T],
                                        api_key: str,
                                        llm_name: str,
                                        ai_provider: str,
                                        max_iterations=5,
                                        additional_iterations=5,
                                        standard_error_message=ERROR_MESSAGE_FOR_MODEL_GENERATION) \
        -> tuple[str, any, list[Any]]:
    error_history = []
    for iteration in range(max_iterations + additional_iterations):
        if ai_provider == AIProviders.GOOGLE.value:
            response = generate_response_with_history_google(conversation, api_key, llm_name)
        elif ai_provider == AIProviders.ANTHROPIC.value:
            response = generate_response_with_history_anthropic(conversation, api_key, llm_name)
        else:
            if ai_provider == AIProviders.DEEPINFRA.value:
                api_url = "https://api.deepinfra.com/v1/openai"
            elif ai_provider == AIProviders.OPENAI.value:
                api_url = "https://api.openai.com/v1"
            elif ai_provider == AIProviders.MISTRAL_AI.value:
                api_url = "https://api.mistral.ai/v1/"
            else:
                raise Exception(f"AI provider {ai_provider} is not supported!")
            response = generate_response_with_history(conversation, api_key, llm_name, api_url)

        try:
            conversation.append({"role": "assistant", "content": response})
            auto_duplicate = iteration >= max_iterations
            code, result = extraction_function(response, auto_duplicate)
            print_conversation(conversation)
            return code, result, conversation  # Break loop if execution is successful
        except Exception as e:
            error_description = str(e)
            error_history.append(error_description)
            if constants.ENABLE_PRINTS:
                print("Error detected in iteration " + str(iteration + 1))
            new_message = f"Executing your code led to an error! " + standard_error_message + "This is the error" \
                          f" message: {error_description}"
            conversation.append({"role": "user", "content": new_message})

        print_conversation(conversation)

    raise Exception(llm_name + " failed to fix the errors after " + str(max_iterations+5) +
                    " iterations! This is the error history: " + str(error_history))


def print_conversation(conversation):
    if constants.ENABLE_PRINTS:
        print("\n\n")
        for index, msg in enumerate(conversation):
            print("\t%d: %s" % (index, str(msg).replace("\n", " ").replace("\r", " ")))
        print("\n\n")


def generate_response_with_history(conversation_history, api_key, llm_name, api_url) -> str:
    """
    Generates a response from the LLM using the conversation history.

    :param conversation_history: The conversation history to be included
    :param api_key: API key
    :param llm_name: model to be used
    :param api_url: API URL to be used
    :return: The content of the LLM response
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    messages_payload = []
    for message in conversation_history:
        messages_payload.append({
            "role": message["role"],
            "content": message["content"]
        })

    payload = {
        "model": llm_name,
        "messages": messages_payload
    }

    if constants.MAX_TOKENS < sys.maxsize:
        payload["max_tokens"] = constants.MAX_TOKENS

    if api_url.endswith("/"):
        api_url = api_url[:-1]

    response = requests.post(api_url + "/chat/completions", headers=headers, json=payload).json()

    try:
        return response["choices"][0]["message"]["content"]
    except Exception:
        raise Exception("Connection failed! This is the response: " + str(response))


def generate_response_with_history_google(conversation_history, api_key, google_model) -> str:
    """
    Generates a response from the LLM using the conversation history.

    :param conversation_history: The conversation history to be included
    :param api_key: Google API key
    :param google_model: Google model to be used
    :return: The content of the LLM response
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(google_model)
    response = model.generate_content(str(conversation_history))
    try:
        return response.text
    except Exception as e:
        raise Exception("Connection failed! This is the response: " + str(response))


def generate_response_with_history_anthropic(conversation, api_key, llm_name):
    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key,
    )
    message = client.messages.create(
        model=llm_name,
        max_tokens=8192,
        messages=conversation
    )
    try:
        return message.content[0].text
    except Exception:
        raise Exception("Connection failed! This is the response: " + str(message))