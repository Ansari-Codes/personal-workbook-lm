"""HTTP routes for profile-scoped workbook CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..Functions.workbooks import (
    create_workbook as create_workbook_service,
    delete_workbook as delete_workbook_service,
    get_workbook_config as get_workbook_config_service,
    get_workbook as get_workbook_service,
    list_workbooks as list_workbooks_service,
    update_workbook as update_workbook_service,
    update_workbook_config as update_workbook_config_service,
)
from ..Models.workbook import WorkbookCreate, WorkbookRead, WorkbookUpdate

router = APIRouter(
    prefix="/profiles/{profile_id}/workbooks",
    tags=["workbooks"],
)


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Profile or workbook not found",
    )


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("", response_model=list[WorkbookRead])
def list_workbooks(profile_id: int) -> list[dict]:
    try:
        return list_workbooks_service(profile_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("", response_model=WorkbookRead, status_code=status.HTTP_201_CREATED)
def create_workbook(profile_id: int, payload: WorkbookCreate) -> dict:
    try:
        return create_workbook_service(
            profile_id,
            payload.title,
            payload.description,
            payload.thumbnail,
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _conflict(error) from error


@router.get("/{workbook_id}", response_model=WorkbookRead)
def get_workbook(profile_id: int, workbook_id: int) -> dict:
    try:
        return get_workbook_service(profile_id, workbook_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/{workbook_id}", response_model=WorkbookRead)
def update_workbook(
    profile_id: int, workbook_id: int, payload: WorkbookUpdate
) -> dict:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    try:
        return update_workbook_service(profile_id, workbook_id, updates)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _conflict(error) from error


@router.delete("/{workbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workbook(profile_id: int, workbook_id: int) -> Response:
    try:
        delete_workbook_service(profile_id, workbook_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workbook_id}/config")
def get_workbook_config(profile_id: int, workbook_id: int) -> dict:
    try:
        return get_workbook_config_service(profile_id, workbook_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/{workbook_id}/config")
def update_workbook_config(profile_id: int, workbook_id: int, updates: dict) -> dict:
    try:
        return update_workbook_config_service(profile_id, workbook_id, updates)
    except KeyError as error:
        raise _not_found(error) from error
