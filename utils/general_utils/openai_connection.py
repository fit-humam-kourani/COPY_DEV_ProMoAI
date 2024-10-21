from typing import Callable, List, TypeVar, Any
from utils import constants, shared
import requests
import sys
import google.generativeai as genai

T = TypeVar('T')


def generate_result_with_error_handling(conversation: List[dict[str:str]],
                                        extraction_function: Callable[[str, Any], T],
                                        api_key: str,
                                        openai_model: str,
                                        api_url: str,
                                        max_iterations=5) \
        -> tuple[str, any, list[Any]]:
    error_history = []

    print_conversation(conversation)

    for iteration in range(max_iterations + 5):
        if api_url == "GOOGLE":
            response = generate_response_with_history_google(conversation, api_key, openai_model)
        elif api_url == "https://api.anthropic.com/v1/messages":
            response = generate_response_with_history_anthropic(conversation, api_key, openai_model)
        else:
            response = generate_response_with_history(conversation, api_key, openai_model, api_url)

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
            new_message = f"Executing your code led to an error! Please update the model to fix the error. Make sure" \
                          f" to save the updated final model is the variable 'final_model'. This is the error" \
                          f" message: {error_description}"
            conversation.append({"role": "user", "content": new_message})

        print_conversation(conversation)

    raise Exception(openai_model + " failed to fix the errors after " + str(max_iterations+5) +
                    " iterations! This is the error history: " + str(error_history))


def print_conversation(conversation):
    if constants.ENABLE_PRINTS:
        print("\n\n")
        for index, msg in enumerate(conversation):
            print("\t%d: %s" % (index, str(msg).replace("\n", " ").replace("\r", " ")))
        print("\n\n")


def generate_response_with_history(conversation_history, api_key, openai_model, api_url) -> str:
    """
    Generates a response from the LLM using the conversation history.

    :param conversation_history: The conversation history to be included
    :param api_key: OpenAI API key
    :param openai_model: OpenAI model to be used
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
        "model": openai_model,
        "messages": messages_payload
    }

    if constants.MAX_TOKENS < sys.maxsize:
        payload["max_tokens"] = constants.MAX_TOKENS

    if api_url.endswith("/"):
        api_url = api_url[:-1]

    response = requests.post(api_url + "/chat/completions", headers=headers, json=payload).json()

    try:
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception("Connection failed! This is the response: " + str(response))


def generate_response_with_history_google(conversation_history, api_key, google_model) -> str:
    """
    Generates a response from the LLM using the conversation history.

    :param conversation_history: The conversation history to be included
    :param api_key: Google API key
    :param google_model: Google model to be used
    :return: The content of the LLM response
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(google_model)
    response = model.generate_content(str(conversation_history))
    try:
        return response.text
    except Exception as e:
        raise Exception("Connection failed! This is the response: " + str(response))


def generate_response_with_history_anthropic(conversation, api_key, model):
    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key,
    )
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=conversation
    )
    try:
        return message.content[0].text
    except Exception as e:
        raise Exception("Connection failed! This is the response: " + str(message))
