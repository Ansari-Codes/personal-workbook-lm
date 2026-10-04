"""HTTP routes for profile CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..Functions.profiles import (
    create_profile as create_profile_service,
    delete_profile as delete_profile_service,
    get_profile as get_profile_service,
    list_profiles as list_profiles_service,
    update_profile as update_profile_service,
)
from ..Models.profile import ProfileCreate, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("", response_model=list[ProfileRead])
def list_profiles() -> list[dict]:
    return list_profiles_service()


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate) -> dict:
    try:
        return create_profile_service(payload.name, payload.description, payload.thumbnail)
    except ValueError as error:
        raise _conflict(error) from error


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: int) -> dict:
    try:
        return get_profile_service(profile_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: int, payload: ProfileUpdate) -> dict:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    try:
        return update_profile_service(profile_id, updates)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _conflict(error) from error


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int) -> Response:
    try:
        delete_profile_service(profile_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
