"""HTTP CRUD routes for sources attached to a workbook."""

from __future__ import annotations

from typing import Annotated
from urllib.error import URLError

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from ..Functions.sources import (
    add_content_source as add_content_source_service,
    add_file_source as add_file_source_service,
    add_url_source as add_url_source_service,
    delete_source as delete_source_service,
    list_sources as list_sources_service,
    read_source as read_source_service,
    redownload_source as redownload_source_service,
    update_source as update_source_service,
)
from ..Models.source import (
    SourceContentCreate,
    SourceContentRead,
    SourceRead,
    SourceUpdate,
    SourceUrlCreate,
)

router = APIRouter(
    prefix="/profiles/{profile_id}/workbooks/{workbook_id}/sources",
    tags=["sources"],
)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail="Profile, workbook, or source not found")


def _invalid(error: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


def _upstream(error: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Could not fetch source URL: {error}")


@router.get("", response_model=list[SourceRead])
def list_sources(profile_id: int, workbook_id: int) -> list[dict]:
    try:
        return list_sources_service(profile_id, workbook_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("/upload", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def add_file_source(
    profile_id: int,
    workbook_id: int,
    name: Annotated[str, Form(min_length=1, max_length=255)],
    file: Annotated[UploadFile, File(description="Source file, up to 10 MB")],
    description: Annotated[str, Form(max_length=1000)] = "",
    folder: Annotated[str, Form(max_length=1024)] = "",
) -> dict:
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        return add_file_source_service(profile_id, workbook_id, name, description, content, folder)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid(error) from error
    finally:
        await file.close()


@router.post("/content", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def add_content_source(
    profile_id: int, workbook_id: int, payload: SourceContentCreate
) -> dict:
    try:
        return add_content_source_service(
            profile_id, workbook_id, payload.name, payload.description, payload.content, payload.folder
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid(error) from error


@router.post("/url", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def add_url_source(profile_id: int, workbook_id: int, payload: SourceUrlCreate) -> dict:
    try:
        return add_url_source_service(
            profile_id,
            workbook_id,
            payload.name,
            payload.description,
            payload.url,
            payload.download,
            payload.folder,
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid(error) from error
    except (URLError, TimeoutError, OSError) as error:
        raise _upstream(error) from error


@router.get("/{source_id}/content", response_model=SourceContentRead)
def read_source(profile_id: int, workbook_id: int, source_id: int) -> dict:
    try:
        return read_source_service(profile_id, workbook_id, source_id)
    except KeyError as error:
        raise _not_found(error) from error
    except (URLError, TimeoutError, OSError, FileNotFoundError) as error:
        raise _upstream(error) from error


@router.post("/{source_id}/redownload", response_model=SourceRead)
def redownload_source(profile_id: int, workbook_id: int, source_id: int) -> dict:
    try:
        return redownload_source_service(profile_id, workbook_id, source_id)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid(error) from error
    except (URLError, TimeoutError, OSError) as error:
        raise _upstream(error) from error


@router.patch("/{source_id}", response_model=SourceRead)
def update_source(
    profile_id: int, workbook_id: int, source_id: int, payload: SourceUpdate
) -> dict:
    try:
        return update_source_service(
            profile_id,
            workbook_id,
            source_id,
            payload.model_dump(exclude_unset=True, exclude_none=True),
        )
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid(error) from error
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(profile_id: int, workbook_id: int, source_id: int) -> Response:
    try:
        delete_source_service(profile_id, workbook_id, source_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
