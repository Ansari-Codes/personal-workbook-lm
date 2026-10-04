"""HTTP CRUD routes for profile API keys and caller selection."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..Functions.api_keys import (
    create_api_key as create_api_key_service,
    delete_api_key as delete_api_key_service,
    get_api_key as get_api_key_service,
    list_api_keys as list_api_keys_service,
    list_api_key_models as list_api_key_models_service,
    update_api_key as update_api_key_service,
)
from ..Models.api_key import APIKeyCreate, APIKeyRead, APIKeyUpdate, APIModelOption

router = APIRouter(prefix="/profiles/{profile_id}", tags=["API keys"])


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Profile, API key, or caller not found",
    )


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("/api-keys", response_model=list[APIKeyRead])
def list_api_keys(profile_id: int) -> list[dict]:
    try:
        return list_api_keys_service(profile_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.get("/api-keys/{api_key_id}/models", response_model=list[APIModelOption])
def list_api_key_models(
    profile_id: int, api_key_id: int, caller_id: int, endpoint_name: str = "chat"
) -> list[dict]:
    try:
        return list_api_key_models_service(profile_id, api_key_id, caller_id, endpoint_name)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/api-keys",
    response_model=APIKeyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(profile_id: int, payload: APIKeyCreate) -> dict:
    try:
        return create_api_key_service(profile_id, payload.model_dump())
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _conflict(error) from error


@router.get("/api-keys/{api_key_id}", response_model=APIKeyRead)
def get_api_key(profile_id: int, api_key_id: int) -> dict:
    try:
        return get_api_key_service(profile_id, api_key_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/api-keys/{api_key_id}", response_model=APIKeyRead)
def update_api_key(
    profile_id: int, api_key_id: int, payload: APIKeyUpdate
) -> dict:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    try:
        return update_api_key_service(profile_id, api_key_id, updates)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _conflict(error) from error


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(profile_id: int, api_key_id: int) -> Response:
    try:
        delete_api_key_service(profile_id, api_key_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
