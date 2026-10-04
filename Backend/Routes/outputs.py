"""HTTP CRUD routes for outputs attached to a workbook."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from ..Functions.outputs import (
    MAX_OUTPUT_BYTES,
    create_output as create_output_service,
    delete_output as delete_output_service,
    list_outputs as list_outputs_service,
    read_output as read_output_service,
    replace_output_file as replace_output_file_service,
    update_output as update_output_service,
)
from ..Models.output import OutputContentRead, OutputCreate, OutputRead, OutputUpdate

router = APIRouter(
    prefix="/profiles/{profile_id}/workbooks/{workbook_id}/outputs",
    tags=["outputs"],
)


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail="Profile, workbook, or output not found")


def _invalid(error: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get("", response_model=list[OutputRead])
def list_outputs(profile_id: int, workbook_id: int) -> list[dict]:
    try:
        return list_outputs_service(profile_id, workbook_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("", response_model=OutputRead, status_code=status.HTTP_201_CREATED)
def create_output(profile_id: int, workbook_id: int, payload: OutputCreate) -> dict:
    try:
        return create_output_service(
            profile_id, workbook_id, payload.name, payload.description, payload.content, payload.folder
        )
    except KeyError as error:
        raise _not_found(error) from error
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise _invalid(error) from error


@router.get("/{output_id}/content", response_model=OutputContentRead)
def read_output(profile_id: int, workbook_id: int, output_id: int) -> dict:
    try:
        return read_output_service(profile_id, workbook_id, output_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/{output_id}", response_model=OutputRead)
def update_output(
    profile_id: int, workbook_id: int, output_id: int, payload: OutputUpdate
) -> dict:
    try:
        return update_output_service(
            profile_id,
            workbook_id,
            output_id,
            payload.model_dump(exclude_unset=True, exclude_none=True),
        )
    except KeyError as error:
        raise _not_found(error) from error


@router.put("/{output_id}/file", response_model=OutputRead)
async def replace_output_file(
    profile_id: int,
    workbook_id: int,
    output_id: int,
    file: UploadFile = File(description="Replacement output file, up to 50 MB"),
) -> dict:
    try:
        content = await file.read(MAX_OUTPUT_BYTES + 1)
        return replace_output_file_service(profile_id, workbook_id, output_id, content)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid(error) from error
    finally:
        await file.close()


@router.delete("/{output_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_output(profile_id: int, workbook_id: int, output_id: int) -> Response:
    try:
        delete_output_service(profile_id, workbook_id, output_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)