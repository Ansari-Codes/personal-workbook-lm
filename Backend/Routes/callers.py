"""HTTP CRUD routes for profile Callers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..Functions.callers import (
    create_caller as create_caller_service,
    delete_caller as delete_caller_service,
    get_caller as get_caller_service,
    list_callers as list_callers_service,
    update_caller as update_caller_service,
)
from ..Models.caller import CallerCreate, CallerRead, CallerUpdate

router = APIRouter(prefix="/profiles/{profile_id}/callers", tags=["callers"])


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail="Profile or caller not found")


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def _bad_caller(error: (SyntaxError | ValueError | TypeError)) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get("", response_model=list[CallerRead])
def list_callers(profile_id: int) -> list[dict]:
    try:
        return list_callers_service(profile_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("", response_model=CallerRead, status_code=status.HTTP_201_CREATED)
def create_caller(profile_id: int, payload: CallerCreate) -> dict:
    try:
        return create_caller_service(profile_id, payload.model_dump())
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        if "unique" in str(error).lower():
            raise _conflict(error) from error
        raise _bad_caller(error) from error
    except SyntaxError as error:
        raise _bad_caller(error) from error


@router.get("/{caller_id}", response_model=CallerRead)
def get_caller(profile_id: int, caller_id: int) -> dict:
    try:
        return get_caller_service(profile_id, caller_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/{caller_id}", response_model=CallerRead)
def update_caller(profile_id: int, caller_id: int, payload: CallerUpdate) -> dict:
    try:
        return update_caller_service(
            profile_id, caller_id, payload.model_dump(exclude_unset=True, exclude_none=True)
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        if "unique" in str(error).lower():
            raise _conflict(error) from error
        raise _bad_caller(error) from error
    except SyntaxError as error:
        raise _bad_caller(error) from error


@router.delete("/{caller_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_caller(profile_id: int, caller_id: int) -> Response:
    try:
        delete_caller_service(profile_id, caller_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
