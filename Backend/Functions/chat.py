"""OpenAI-compatible chat completions for a workbook and its selected resources."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, cast

from Pawm.CallerTypes import INVOKE_OUTPUT
from Pawm.Manage_Profile import Profile
from Pawm.Manage_Tool import Tool

from ..Models.chat import ChatRequest
from ..commons import STORAGE
from .api_keys import endpoint_config

class ChatAccessError(Exception):
    """The requested API key is not enabled for this workbook."""


def _schema_items(schema: Any) -> list[Any]:
    if isinstance(schema, dict):
        candidates = schema.get("functions", schema.get("tools", [schema]))
    else:
        candidates = schema
    if not isinstance(candidates, list):
        return []
    return [item for group in candidates for item in (group if isinstance(group, list) else [group])]


def _profile(profile_id: int) -> Profile:
    return STORAGE.profiles.load(profile_id)


def get_chat_history(profile_id: int, workbook_id: int) -> list[dict[str, Any]]:
    workbook = _profile(profile_id).workbooks.load(workbook_id)
    return workbook.chat.list()


def clear_chat_history(profile_id: int, workbook_id: int) -> None:
    workbook = _profile(profile_id).workbooks.load(workbook_id)
    workbook.chat.clear()


def _tool_functions(
    profile: Profile,
    workbook_config: dict[str, Any],
    workbook: Any,
) -> tuple[list[dict[str, Any]], dict[str, Callable[[dict[str, Any]], Any]]]:
    if not workbook_config.get("use_tools", True):
        return [], {}

    definitions: list[dict[str, Any]] = []
    function_lookup: dict[str, Callable[[dict[str, Any]], Any]] = {}
    selected_ids = workbook_config.get("selected_tool_ids", [])
    if not isinstance(selected_ids, list):
        selected_ids = []

    for tool_id in selected_ids:
        try:
            tool = profile.tools.load(tool_id)
            schema = profile.tools.get_schema(tool_id)
        except (KeyError, ValueError):
            continue
        for candidate in _schema_items(schema):
            if not isinstance(candidate, dict):
                continue
            function = candidate.get("function", candidate)
            if not isinstance(function, dict):
                continue
            original_name = function.get("name")
            if not isinstance(original_name, str) or not original_name:
                continue
            parameters = function.get("parameters", {"type": "object", "properties": {}})
            if not isinstance(parameters, dict):
                continue
            external_name = f"tool_{tool.id}_{original_name}"
            definitions.append({
                "type": "function",
                "function": {
                    "name": external_name,
                    "description": str(function.get("description", tool.description)),
                    "parameters": parameters,
                },
            })
            requires_workbook = bool(tool.data.get("requires_workbook"))
            function_lookup[external_name] = (
                lambda arguments, selected_tool=tool, selected_name=original_name, with_workbook=requires_workbook:
                selected_tool.make_call(
                    selected_name,
                    arguments,
                    context={"workbook": workbook} if with_workbook else None,
                )
            )

    return definitions, function_lookup


def _trim_history(history: list[dict[str, str]], context_length: int) -> list[dict[str, str]]:
    return history[-context_length:] if context_length > 0 else []


def _call_completion(
    caller: Any,
    api_key: Any,
    base_url: str,
    endpoint: str,
    settings: dict[str, Any],
) -> INVOKE_OUTPUT:
    parameters = dict(settings)
    parameters["base_url"] = base_url
    parameters["endpoint"] = endpoint
    parameters["key"] = str(api_key.data["secret"])
    parameters["api_key"] = str(api_key.data["secret"])
    try:
        result = caller.INVOKE(**parameters)
    except Exception as error:
        raise RuntimeError(f"Caller INVOKE failed: {error}") from error
    if not isinstance(result, dict) or result.get("success") is not True:
        detail = result.get("error", "Caller returned an unsuccessful INVOKE_OUTPUT") if isinstance(result, dict) else "Caller must return an INVOKE_OUTPUT object"
        raise RuntimeError(str(detail))
    message = result.get("message")
    if not isinstance(message, dict):
        text = result.get("text", "")
        if not isinstance(text, str):
            raise RuntimeError("Caller text must be a string")
        normalized_message: dict[str, Any] = {"role": "assistant", "content": text}
        tool_calls = result.get("tool_calls")
        if isinstance(tool_calls, list):
            normalized_message["tool_calls"] = tool_calls
        result["message"] = normalized_message
    return cast(INVOKE_OUTPUT, result)


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") in ("text", "output_text")
        )
    return ""


def _execute_tool_calls(
    tool_calls: list[dict[str, Any]],
    function_lookup: dict[str, Callable[[dict[str, Any]], Any]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    events: list[dict[str, str]] = []
    tool_messages: list[dict[str, Any]] = []
    for call in tool_calls:
        function = call.get("function")
        call_id = str(call.get("id", ""))
        function_name = function.get("name") if isinstance(function, dict) else None
        arguments = function.get("arguments", "{}") if isinstance(function, dict) else "{}"
        matched = function_lookup.get(str(function_name))
        if matched is None:
            tool_result = json.dumps({"error": "Tool is not enabled for this workbook"})
            display_name = str(function_name or "unknown")
        else:
            display_name = str(function_name)
            try:
                parsed_arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                if not isinstance(parsed_arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object")
                result_value = matched(parsed_arguments)
                tool_result = json.dumps(result_value, ensure_ascii=False, default=str)
            except Exception as error:
                tool_result = json.dumps({"error": str(error)}, ensure_ascii=False)
        events.append({"role": "tool_call", "content": str(arguments), "name": display_name})
        events.append({"role": "tool_output", "content": tool_result, "name": display_name})
        tool_messages.append({"role": "tool", "tool_call_id": call_id, "content": tool_result})
    return events, tool_messages


def _persist_caller_media(workbook: Any, response: Mapping[str, Any]) -> list[str]:
    links: list[str] = []
    media_items = response.get("media", [])
    if isinstance(media_items, dict):
        media_items = [media_items]
    if not isinstance(media_items, list):
        raise RuntimeError("Caller media must be a media object or an array")
    for media in media_items:
        if not isinstance(media, dict):
            raise RuntimeError("Caller media entries must be objects")
        name = media.get("name")
        content = media.get("content")
        media_type = media.get("media_type", "application/octet-stream")
        if not isinstance(name, str) or not name or not isinstance(content, bytes):
            raise RuntimeError("Caller media must include a filename and bytes content")
        if not isinstance(media_type, str):
            raise RuntimeError("Caller media type must be text")
        folder = media.get("folder", "media")
        if not isinstance(folder, str):
            raise RuntimeError("Caller media folder must be text")
        output = workbook.outputs.add(name, f"Generated by caller ({media_type})", content, folder)
        path = f"{output.folder}/{output.name}" if output.folder else output.name
        links.append(f"[Open {output.name}]({path})")
    return links


def _save_exchange(
    workbook: Any,
    request: ChatRequest,
    events: list[dict[str, str]],
    answer: str,
    response_model: str,
    usage: dict[str, Any],
) -> None:
    chat_entries = [{
        "role": "user",
        "content": request.prompt,
        "meta": {
            "model": request.model,
            "api_key_id": request.api_key_id,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "context_length": request.context_length,
        },
    }]
    for event in events:
        chat_entries.append({
            "role": event["role"],
            "content": event["content"],
            "meta": {"name": event["name"]},
        })
    chat_entries.append({
        "role": "assistant",
        "content": answer,
        "meta": {"model": response_model, "usage": usage},
    })
    workbook.chat.add_many(chat_entries)


def stream_chat_events(profile_id: int, workbook_id: int, request: ChatRequest):
    profile = _profile(profile_id)
    workbook = profile.workbooks.load(workbook_id)
    config = workbook.config.all()
    selected_api_key_ids = config.get("selected_api_key_ids", [])
    if not isinstance(selected_api_key_ids, list) or request.api_key_id not in selected_api_key_ids:
        raise ChatAccessError("Select this API key in the workbook settings before using it")

    api_key = profile.api_keys.get(request.api_key_id)
    caller = profile.callers.load(request.caller_id)
    api_key_data = api_key.data
    base_url, endpoint = endpoint_config(api_key_data, request.endpoint_name)
    prompt = request.prompt
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in request.history
        if turn.content.strip()
    ]    
    history = _trim_history(history, request.context_length)
    tools, function_lookup = _tool_functions(profile, config, workbook)
    settings = request.model_dump()
    settings.update({
        "history": history,
        "messages": [*history, {"role": "user", "content": prompt}],
    })
    if tools:
        settings["tools"] = tools
        settings["tool_choice"] = "auto"

    events: list[dict[str, str]] = []
    answer = ""
    usage: dict[str, Any] = {}
    response_model = request.model
    tool_call_count = 0
    while True:
        result = _call_completion(
            caller, api_key, base_url, endpoint, settings
        )
        media_links = _persist_caller_media(workbook, result)
        message = result.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("Successful INVOKE_OUTPUT must include a message object")
        if media_links:
            message["content"] = f"{_message_text(message.get('content'))}\n\n" + "\n".join(media_links)
        response_model = result.get("model", request.model)
        usage.update(result.get("usage", {}))
        reasoning = result.get("reasoning", "")
        if reasoning:
            events.append({"role": "reasoning", "content": reasoning, "name": "Reasoning"})
            yield {"type": "reasoning", "role": "reasoning", "content": reasoning, "name": "Reasoning"}
        content = _message_text(message.get("content"))
        if content:
            answer += content
            yield {"type": "token", "content": content}
        tool_calls = message.get("tool_calls", [])
        if not isinstance(tool_calls, list) or not tool_calls:
            break
        if request.max_tool_calls is not None and tool_call_count + len(tool_calls) > request.max_tool_calls:
            raise RuntimeError(f"Model exceeded the maximum tool-call limit ({request.max_tool_calls})")
        tool_call_count += len(tool_calls)
        settings["messages"].append(message)
        new_events, tool_messages = _execute_tool_calls(tool_calls, function_lookup)
        events.extend(new_events)
        for event in new_events:
            yield {"type": event["role"], **event}
        settings["messages"].extend(tool_messages)
    if not answer.strip():
        raise RuntimeError("Model endpoint returned an empty assistant response")
    _save_exchange(workbook, request, events, answer, response_model, usage)
    yield {"type": "done", "model": response_model, "usage": usage}


def complete_chat(profile_id: int, workbook_id: int, request: ChatRequest) -> dict[str, Any]:
    profile = _profile(profile_id)
    workbook = profile.workbooks.load(workbook_id)
    config = workbook.config.all()
    selected_api_key_ids = config.get("selected_api_key_ids", [])
    if not isinstance(selected_api_key_ids, list) or request.api_key_id not in selected_api_key_ids:
        raise ChatAccessError("Select this API key in the workbook settings before using it")

    api_key = profile.api_keys.get(request.api_key_id)
    caller = profile.callers.load(request.caller_id)
    api_key_data = api_key.data
    base_url, endpoint = endpoint_config(api_key_data, request.endpoint_name)
    prompt = request.prompt
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in request.history
        if turn.content.strip()
    ]
    history = _trim_history(history, request.context_length)
    messages = [*history, {"role": "user", "content": prompt}]

    tools, function_lookup = _tool_functions(profile, config, workbook)
    
    settings = request.model_dump()
    settings.update({"history": history, "messages": messages})
    if tools:
        settings["tools"] = tools
        settings["tool_choice"] = "auto"
    events: list[dict[str, str]] = []
    usage: dict[str, Any] = {}
    response_model = request.model
    answer = ""
    tool_call_count = 0
    while True:
        result = _call_completion(
            caller, api_key, base_url, endpoint, settings
        )
        media_links = _persist_caller_media(workbook, result)
        message = result.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("Successful INVOKE_OUTPUT must include a message object")
        if media_links:
            message["content"] = f"{_message_text(message.get('content'))}\n\n" + "\n".join(media_links)
        response_model = result.get("model", request.model)
        usage.update(result.get("usage", {}))
        reasoning = result.get("reasoning", "")
        if reasoning:
            events.append({"role": "reasoning", "content": reasoning, "name": "Reasoning"})
        tool_calls = message.get("tool_calls", [])
        if not isinstance(tool_calls, list) or not tool_calls:
            answer = _message_text(message.get("content"))
            break
        valid_tool_calls = [call for call in tool_calls if isinstance(call, dict)]
        if request.max_tool_calls is not None and tool_call_count + len(valid_tool_calls) > request.max_tool_calls:
            raise RuntimeError(f"Model exceeded the maximum tool-call limit ({request.max_tool_calls})")
        tool_call_count += len(valid_tool_calls)

        settings["messages"].append(message)
        new_events, tool_messages = _execute_tool_calls(
            valid_tool_calls,
            function_lookup,
        )
        events.extend(new_events)
        settings["messages"].extend(tool_messages)
    if not answer.strip():
        raise RuntimeError("Model endpoint returned an empty assistant response")

    chat_entries = [{
        "role": "user",
        "content": request.prompt,
        "meta": {
            "model": request.model,
            "api_key_id": request.api_key_id,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "context_length": request.context_length,
        },
    }]
    for event in events:
        chat_entries.append({
            "role": event["role"],
            "content": event["content"],
            "meta": {"name": event["name"]},
        })
    chat_entries.append({
        "role": "assistant",
        "content": answer,
        "meta": {"model": response_model, "usage": usage},
    })
    workbook.chat.add_many(chat_entries)
    return {"role": "assistant", "content": answer, "model": response_model, "usage": usage, "events": events}
