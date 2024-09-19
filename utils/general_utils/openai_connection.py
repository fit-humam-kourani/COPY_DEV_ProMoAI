from typing import Callable, List, TypeVar, Any
from utils import constants, shared
import requests
import sys

T = TypeVar('T')


def generate_result_with_error_handling(conversation: List[dict[str:str]],
                                        extraction_function: Callable[[str, Any], T],
                                        api_key: str,
                                        openai_model: str,
                                        api_url: str,
                                        max_iterations=5) \
        -> tuple[T, List[dict[str:str]]]:
    error_history = []

    print_conversation(conversation)

    for iteration in range(max_iterations):
        shared.LAST_ITERATIONS = iteration+1

        response = generate_response_with_history(conversation, api_key, openai_model, api_url)

        try:
            conversation.append({"role": "assistant", "content": response})
            result = extraction_function(response, iteration)

            print_conversation(conversation)

            return result, conversation  # Break loop if execution is successful
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

    raise Exception(openai_model + " failed to fix the errors after " + str(max_iterations) +
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

    response = requests.post(api_url+"/chat/completions", headers=headers, json=payload).json()

    try:
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception("Connection to OpenAI failed! This is the response: " + str(response))
