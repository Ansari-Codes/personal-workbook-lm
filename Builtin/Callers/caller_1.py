import base64
import binascii
import inspect
from uuid import uuid4
from urllib.parse import urlsplit, urlunsplit

from groq import Groq


def _sdk_base_url(base_url: str, endpoint: str) -> str:
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    endpoint_path = "/" + endpoint.split("?", 1)[0].strip("/")
    if base_path and (endpoint_path == base_path or endpoint_path.startswith(f"{base_path}/")):
        return urlunsplit(parsed._replace(path="", query="", fragment="")).rstrip("/")
    return base_url.rstrip("/")


def _audio_media(message, settings):
    audio = message.get("audio")
    if not isinstance(audio, dict) or not isinstance(audio.get("data"), str):
        return None
    try:
        content = base64.b64decode(audio["data"], validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("OpenAI returned invalid base64 audio data") from error

    audio_settings = settings.get("additional_parameters", {}).get("audio", {})
    audio_format = audio_settings.get("format", "wav") if isinstance(audio_settings, dict) else "wav"
    formats = {
        "flac": ("flac", "audio/flac"),
        "mp3": ("mp3", "audio/mpeg"),
        "opus": ("opus", "audio/opus"),
        "pcm16": ("pcm", "audio/pcm"),
        "wav": ("wav", "audio/wav"),
    }
    extension, media_type = formats.get(str(audio_format).lower(), ("bin", "application/octet-stream"))
    audio_id = audio.get("id")
    name = f"openai-{audio_id}.{extension}" if isinstance(audio_id, str) and audio_id else f"openai-audio.{extension}"
    return {"name": name, "folder": "audio", "media_type": media_type, "content": content}


def _invoke_audio_speech(settings, client, model):
    text = next(
        (settings[name] for name in ("text", "user_text", "prompt")
         if isinstance(settings.get(name), str) and settings[name].strip()),
        None,
    )
    if text is None:
        return {"success": False, "error": "text or prompt is required for speech generation"}

    additional = settings.get("additional_parameters")
    if not isinstance(additional, dict):
        additional = {}
    try:
        response_format = additional.get("response_format", "wav")
        response = client.audio.speech.create(
            model=model,
            input=text,
            **{
                name: value
                for name, value in additional.items()
                if name not in {"model", "input"}
            },
        )
        response_headers = getattr(getattr(response, "response", None), "headers", {})
        media_type = response_headers.get("content-type", "").split(";", 1)[0].strip()
        formats = {
            "audio/flac": "flac",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/opus": "opus",
            "audio/pcm": "pcm",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
        }
        extension = formats.get(media_type, str(response_format))
        media_type = media_type or {
            "flac": "audio/flac",
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "pcm": "audio/pcm",
            "wav": "audio/wav",
        }.get(extension, "application/octet-stream")
        return {
            "success": True,
            "model": model,
            "text": "Speech generated.",
            "message": {"role": "assistant", "content": "Speech generated."},
            "media": [{
                "name": f"speech-{uuid4().hex[:12]}.{extension}",
                "folder": "audio",
                "media_type": media_type,
                "content": response.read(),
            }],
            "raw": {
                "status_code": getattr(getattr(response, "response", None), "status_code", None),
                "content_type": media_type,
                "headers": dict(response_headers),
            },
        }
    except Exception as error:
        return {"success": False, "error": str(error)}


def INVOKE(**kwargs):
    settings = kwargs
    base_url = settings.get("base_url")
    endpoint = settings.get("endpoint")
    key = settings.get("key")
    model = settings.get("model")
    messages = settings.get("messages")
    if (
        not isinstance(base_url, str) or not base_url
        or not isinstance(endpoint, str) or not endpoint
        or not isinstance(key, str) or not key
        or not isinstance(model, str) or not model
    ):
        return {"success": False, "error": "base_url, endpoint, key, and model are required"}
    try:
        client = Groq(api_key=key, base_url=_sdk_base_url(base_url, endpoint), timeout=90.0)
        normalized_endpoint = endpoint.rstrip("/").lower()
        if normalized_endpoint.endswith("/audio/speech"):
            return _invoke_audio_speech(settings, client, model)
        if not normalized_endpoint.endswith("/chat/completions"):
            return {"success": False, "error": f"Unsupported INVOKE endpoint: {endpoint}"}
        if not isinstance(messages, list) or not messages:
            return {"success": False, "error": "messages must be a non-empty array"}

        parameters = dict(settings.get("payload") or {})
        parameters.update({"model": model, "messages": messages, "stream": False})
        for name in ("temperature", "top_p", "tools", "tool_choice"):
            if name in settings and settings[name] is not None:
                parameters[name] = settings[name]
        additional = settings.get("additional_parameters")
        if isinstance(additional, dict) and additional:
            supported_parameters = inspect.signature(client.chat.completions.create).parameters
            provider_options = {}
            for name, value in additional.items():
                if name in supported_parameters:
                    parameters[name] = value
                else:
                    provider_options[name] = value
            if provider_options:
                parameters["extra_body"] = {
                    **parameters.get("extra_body", {}),
                    **provider_options,
                }
        response = client.chat.completions.create(**parameters).model_dump()
        choices = response.get("choices", [])
        if not choices or not isinstance(choices[0], dict) or not isinstance(choices[0].get("message"), dict):
            return {"success": False, "error": "OpenAI returned no assistant message"}

        choice = choices[0]
        source_message = choice["message"]
        message = {"role": "assistant", "content": source_message.get("content") or ""}
        tool_calls = source_message.get("tool_calls")
        if isinstance(tool_calls, list):
            message["tool_calls"] = [
                {
                    "id": call.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": call.get("function", {}).get("name", ""),
                        "arguments": call.get("function", {}).get("arguments", "{}"),
                    },
                }
                for call in tool_calls
                if isinstance(call, dict) and isinstance(call.get("function"), dict)
            ]

        output = {
            "success": True,
            "model": response.get("model", model),
            "text": source_message.get("content") or "",
            "choices": choices,
            "message": message,
            "usage": response.get("usage") or {},
            "finish_reason": choice.get("finish_reason"),
            "raw": response,
        }
        if message.get("tool_calls"):
            output["tool_calls"] = message["tool_calls"]
        reasoning = source_message.get("reasoning_content") or source_message.get("reasoning")
        if isinstance(reasoning, str) and reasoning:
            output["reasoning"] = reasoning
        media = _audio_media(source_message, settings)
        if media is not None:
            output["media"] = [media]
            if not message["content"]:
                message["content"] = source_message.get("audio", {}).get("transcript", "")
        return output
    except Exception as error:
        return {"success": False, "error": str(error)}


def MODEL(**kwargs):
    settings = kwargs
    base_url = settings.get("base_url")
    key = settings.get("key")
    try:
        client = Groq(api_key=key, base_url=base_url, timeout=15.0)
        response = client.models.list()
        raw = response.model_dump()
        models = [
            {**item, "id": item["id"], "name": item.get("name", item["id"])}
            for item in raw.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        return {"success": True, "models": models, "raw": raw}
    except Exception as error:
        return {"success": False, "models": [], "error": str(error)}