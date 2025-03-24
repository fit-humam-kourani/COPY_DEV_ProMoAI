from typing import Callable, List, TypeVar, Any
from utils import constants
import requests
import sys
from copy import copy
import google.generativeai as genai
import time
import json
import traceback

from utils.prompting.prompt_engineering import ERROR_MESSAGE_FOR_MODEL_GENERATION

T = TypeVar('T')


def generate_result_with_error_handling(conversation: List[dict[str:str]],
                                        extraction_function: Callable[[str, Any], T],
                                        api_key: str,
                                        llm_name: str,
                                        api_url: str,
                                        max_iterations=5,
                                        additional_iterations=5,
                                        standard_error_message=ERROR_MESSAGE_FOR_MODEL_GENERATION) \
        -> tuple[str, any, list[Any]]:
    error_history = []

    for iteration in range(max_iterations + additional_iterations):
        if api_url == "GOOGLE":
            response = generate_response_with_history_google(conversation, api_key, llm_name)
        elif api_url == "https://api.anthropic.com/v1/messages":
            response = generate_response_with_history_anthropic(conversation, api_key, llm_name)
        else:
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
        # time.sleep(5)

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
    :param api_key: OpenAI API key
    :param llm_name: OpenAI model to be used
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

    response = requests.post(api_url + "/chat/completions", headers=headers, json=payload, timeout=20*60).json()

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
    except Exception as e:
        raise Exception("Connection failed! This is the response: " + str(message))


def generate_response_with_history_anthropic(conversation, api_key, llm_name):
    ANTHROPIC_THINKING_TOKENS = 65536

    complete_url = "https://api.anthropic.com/v1/messages"

    messages = copy(conversation)

    headers = {
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "output-128k-2025-02-19",
        "x-api-key": api_key
    }

    payload = {
        "model": llm_name,
        "max_tokens": 128000,
        "messages": messages
    }

    if ANTHROPIC_THINKING_TOKENS is not None:
        payload["thinking"] = {"type": "enabled", "budget_tokens": ANTHROPIC_THINKING_TOKENS}
        payload["max_tokens"] += ANTHROPIC_THINKING_TOKENS
        payload["max_tokens"] = min(128000, payload["max_tokens"])
        print(payload)

    streaming_enabled = False

    if streaming_enabled is True:
        payload["stream"] = True
        response_message = ""
        chunk_count = 0

        # Make a streaming POST request
        with requests.post(complete_url, headers=headers, json=payload, stream=True) as resp:
            print(resp)
            print(resp.status_code)
            print(resp.text)

            for line in resp.iter_lines():
                if not line:
                    continue
                # Decode the line
                decoded_line = line.decode("utf-8").strip()

                # Optionally check for a stream end marker (Anthropic may send "[DONE]")
                if "message_stop" in decoded_line:
                    break

                if "message_start" in decoded_line:
                    continue

                try:
                    decoded_line = decoded_line.split("data: ")[-1].strip()
                    if "text" in decoded_line:
                        chunk = decoded_line.split('"text":"')[-1].split('"')[0].replace("\\n", "\n")
                        response_message += chunk
                        chunk_count += 1
                        #print(chunk_count)

                        # You could add logging or progress updates here if desired
                        if chunk_count % 10 == 0:
                            #print(chunk_count, len(response_message), response_message)
                            pass

                except json.JSONDecodeError:
                    # Skip any malformed lines
                    traceback.print_exc()
                    continue
    else:
        with requests.post(complete_url, headers=headers, json=payload, stream=True) as resp:
            print(resp)
            print(resp.status_code)

            resp = resp.json()

            response_message = resp["content"][-1]["text"]
            print(response_message)

    return response_message
