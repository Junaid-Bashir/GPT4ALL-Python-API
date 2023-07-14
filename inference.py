import os
import time
from typing import Any, Dict, AnyStr, List, Union
import uuid
import re
from fastapi import FastAPI, Request
from gpt4all import GPT4All
from dotenv import load_dotenv

load_dotenv()
home_directory: str = os.path.expanduser('~')
print("Home directory: ", home_directory)

global model_path
default_model = "ggml-model-gpt4all-falcon-q4_0.bin"
model_instance = GPT4All(default_model)


def prompt_test(prompt, prompt_template):
    instruct_prompt = "\n" + simple_format(prompt_template, prompt)
    print(model_instance.generate(instruct_prompt, streaming=False, tokens_size=400, temp=0.39))


def extract_arguments_from_json(json_string):
    json_data = json_string
    print(type(json_data))
    return json_data


def simple_format(format, promt):
    return format.replace('%1', promt)


def chat_by_payload(payload):
    return payload


def generate_text_by_payload(payload):
    global model_instance
    global default_model
    start_time = time.time()

    payload_arguments = extract_arguments_from_json(payload)
    # not implemented
    thread_count = 4

    model = default_model
    if "model" in payload_arguments:
        model = payload_arguments["model"]
    # prompt in string only
    prompt = ""
    if "prompt" in payload_arguments:
        prompt = payload_arguments["prompt"]
    if prompt == "":
        return {
            "error": {
                "message": "empty prompt",
                "type": "invalid_request_error",
                "param": None,
                "code": None
            }
        }

    if model != default_model:
        # load model if model provided in payload is different from default model
        model_instance = GPT4All(model)
        # change the name of the default model to prevent the model from being loaded again on the next request
        default_model = model

    max_tokens = 16
    if "max_tokens" in payload_arguments:
        max_tokens = payload_arguments["max_tokens"]

    temperature = 1.0
    if "temperature" in payload_arguments:
        temperature = payload_arguments["temperature"]

    top_p = 1.0
    if "top_p" in payload_arguments:
        top_p = payload_arguments["top_p"]

    prompt_batch_size = 128
    if "prompt_batch_size" in payload_arguments:
        prompt_batch_size = payload_arguments["prompt_batch_size"]

    top_k = 40
    if "top_k" in payload_arguments:
        top_k = payload_arguments["top_k"]

    # reloads model if true
    reload = False
    if "reload" in payload_arguments:
        reload = payload_arguments["reload"]
    # not implemented
    n = 1
    if "n" in payload_arguments:
        n = payload_arguments["n"]

    # not implemented
    if "thread_count" in payload_arguments:
        thread_count = payload_arguments["thread_count"]

    repeat_penality = 1.18
    if "repeat_penality" in payload_arguments:
        repeat_penality = payload_arguments["repeat_penality"]

    repeat_last_n = 64
    if "repeat_last_n" in payload_arguments:
        repeat_last_n = payload_arguments["repeat_last_n"]

    # not implemented
    echo = False
    if "echo" in payload_arguments:
        echo = payload_arguments["echo"]



    # reloads model if reload is true
    if reload:
        model_instance = GPT4All(model)
    prompt_template = ("\n"
                       "### Instruction\n"
                       "Paraphrase the text below by expanding the words based on the subject\n"
                       "### Human:\n"
                       "%1\n"
                       "### Assistant:\n")
    if "prompt_template" in payload_arguments:
        prompt_template = payload_arguments["prompt_template"]

    instruct_prompt = "\n" + simple_format(prompt_template, prompt)

    output = model_instance.generate(instruct_prompt, tokens_size=max_tokens, temp=temperature, top_p=top_p,
                                     top_k=top_k,
                                     n_batch=prompt_batch_size, repeat_penalty=repeat_penality,
                                     repeat_last_n=repeat_last_n,
                                     streaming=False)

    response_tokens = 0
    if output:
        response_tokens = len(re.findall(r'\w+', output))
    prompt_tokens = len(re.findall(r'\w+', instruct_prompt))

    end_time = time.time()

    print("Inference time:", (end_time - start_time))
    response_object = {"id": uuid.uuid4().hex, "object": "text_completion", "created": time.time(), "model": model}
    # generate uuid for each response
    index = 0

    choices = []
    choice = {"text": output, "index": index, "logprobs": None,
              "finish_reason": "length" if response_tokens == max_tokens else "stop"}
    # We don't support
    references = []
    choice["references"] = references
    choices.append(choice)

    response_object["choices"] = choices

    usage = {"prompt_tokens": max_tokens, "completion_tokens": len(re.findall(r'\w+', output)),
             "total_tokens": int(prompt_tokens + response_tokens),
             "thread_count": thread_count, "prompt_template": prompt_template}

    response_object["usage"] = usage

    return response_object


app = FastAPI()

JSONObject = Dict[AnyStr, Any]
JSONArray = List[Any]
JSONStructure = Union[JSONArray, JSONObject]


@app.get("/")
async def base():
    return {
        "error": {
            "message": "Invalid URL (GET /v1/)",
            "type": "invalid_request_error",
            "param": None,
            "code": None
        }
    }


@app.post("/v1/completions")
async def completions(request: Request):
    json_body = await request.json()
    return generate_text_by_payload(json_body)


@app.post("/v1/chat/completions")
async def completions_chat(request: Request):
    json_body = await request.json()
    return chat_by_payload(json_body)


@app.get("/v1/models")
async def models():
    global model_instance
    return {
        "object": "list",
        "data": model_instance.list_models()
    }


# download or retrive model
@app.get("/v1/models/{model_name}")
async def get_model(model_name):
    global model_instance
    return {
        "object": "list",
        "data": model_instance.retrieve_model(model_name)
    }
