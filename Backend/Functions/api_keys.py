"""Profile-scoped API-key operations backed by shared storage."""

from __future__ import annotations

from typing import Any

from Pawm.Manage_ApiKeys import ApiKey
from Pawm.Manage_Profile import Profile
from Pawm.CallerTypes import MODEL_ITEM, MODEL_OUTPUT

from ..commons import STORAGE

def _profile(profile_id: int) -> Profile:
    return STORAGE.profiles.load(profile_id)


def _serialize_api_key(api_key: ApiKey) -> dict[str, Any]:
    data = api_key.data
    secret = str(data.get("secret", ""))
    return {
        "id": data["id"],
        "name": data["name"],
        "description": data.get("description", ""),
        "base_url": data["base_url"],
        "endpoints": data["endpoints"],
        "key_preview": f"****{secret[-4:]}" if secret else "",
        "meta": data.get("meta", {}),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def list_api_keys(profile_id: int) -> list[dict[str, Any]]:
    profile = _profile(profile_id)
    return [_serialize_api_key(key) for key in profile.api_keys.list()]


def create_api_key(profile_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    profile = _profile(profile_id)
    api_key = profile.api_keys.add(**fields)
    return _serialize_api_key(api_key)


def get_api_key(profile_id: int, api_key_id: int) -> dict[str, Any]:
    profile = _profile(profile_id)
    return _serialize_api_key(profile.api_keys.get(api_key_id))


def update_api_key(
    profile_id: int, api_key_id: int, updates: dict[str, Any]
) -> dict[str, Any]:
    profile = _profile(profile_id)
    api_key = profile.api_keys.update(api_key_id, updates)
    return _serialize_api_key(api_key)


def delete_api_key(profile_id: int, api_key_id: int) -> None:
    profile = _profile(profile_id)
    profile.api_keys.delete(api_key_id)


def endpoint_config(api_key_data: dict[str, Any], endpoint_name: str) -> tuple[str, str]:
    endpoints = api_key_data.get("endpoints")
    if not isinstance(endpoints, dict) or endpoint_name not in endpoints:
        raise ValueError(f"API key has no endpoint named {endpoint_name!r}")
    base_url = api_key_data.get("base_url")
    endpoint = endpoints[endpoint_name]
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("API key base_url must be a non-empty string")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError(f"API key endpoint {endpoint_name!r} must be a non-empty string")
    return base_url, endpoint


def list_api_key_models(
    profile_id: int,
    api_key_id: int,
    caller_id: int,
    endpoint_name: str,
) -> list[dict[str, Any]]:
    profile = _profile(profile_id)
    api_key = profile.api_keys.get(api_key_id)
    caller = profile.callers.load(caller_id)
    data = api_key.data
    try:
        model_endpoint_name = "models" if "models" in data.get("endpoints", {}) else endpoint_name
        base_url, endpoint = endpoint_config(data, model_endpoint_name)
        result: MODEL_OUTPUT = caller.MODEL(
            base_url=base_url,
            endpoint=endpoint,
            key=str(data["secret"]),
            api_key=str(data["secret"]),
            api_key_id=api_key_id,
            endpoint_name=model_endpoint_name,
        )
    except Exception as error:
        raise RuntimeError(f"API caller model discovery failed: {error}") from error
    if not isinstance(result, dict) or result.get("success") is not True:
        detail = result.get("error", "Caller returned an unsuccessful MODEL_OUTPUT") if isinstance(result, dict) else "Caller must return a MODEL_OUTPUT object"
        raise RuntimeError(str(detail))
    models = result.get("models")
    if not isinstance(models, list):
        raise RuntimeError("Successful MODEL_OUTPUT must include a models array")
    return [
        {
            "id": model["id"],
            "name": model.get("name", model["id"]),
            "properties": {key: value for key, value in model.items() if key not in {"id", "name"}},
        }
        for model in models
        if isinstance(model, dict)
        and isinstance(model.get("id"), str)
    ]
