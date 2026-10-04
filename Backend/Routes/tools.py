"""HTTP CRUD routes for profile tool ZIP packages."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from ..Functions.tools import (
    create_tool as create_tool_service,
    delete_tool as delete_tool_service,
    get_tool as get_tool_service,
    list_tools as list_tools_service,
    update_tool as update_tool_service,
)
from ..Models.tool import ToolRead, ToolUpdate

router = APIRouter(prefix="/profiles/{profile_id}/tools", tags=["tools"])


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail="Profile or tool not found")


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def _invalid_package(error: ValueError) -> HTTPException:
    if "unique" in str(error).lower():
        return _conflict(error)
    return HTTPException(status_code=422, detail=str(error))


@router.get("", response_model=list[ToolRead])
def list_tools(profile_id: int) -> list[dict]:
    try:
        return list_tools_service(profile_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.post("", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
async def create_tool(
    profile_id: int,
    title: Annotated[str, Form(min_length=1, max_length=150)],
    package: Annotated[UploadFile, File(description="ZIP with main.py, README.md, and schema.json")],
    description: Annotated[str, Form(max_length=1000)] = "",
) -> dict:
    try:
        content = await package.read(10 * 1024 * 1024 + 1)
        return create_tool_service(profile_id, title, description, content)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid_package(error) from error
    finally:
        await package.close()


@router.get("/{tool_id}", response_model=ToolRead)
def get_tool(profile_id: int, tool_id: int) -> dict:
    try:
        return get_tool_service(profile_id, tool_id)
    except KeyError as error:
        raise _not_found(error) from error


@router.patch("/{tool_id}", response_model=ToolRead)
async def update_tool(profile_id: int, tool_id: int, request: Request) -> dict:
    try:
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            form = await request.form()
            updates = {
                field: str(form[field])
                for field in ("title", "description")
                if field in form
            }
            package = form.get("package")
            if isinstance(package, StarletteUploadFile):
                updates["package"] = await package.read(10 * 1024 * 1024 + 1)
                await package.close()
        else:
            try:
                payload = ToolUpdate.model_validate(await request.json())
            except (json.JSONDecodeError, ValidationError) as error:
                raise HTTPException(status_code=422, detail="Invalid tool update payload") from error
            updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        return update_tool_service(profile_id, tool_id, updates)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _invalid_package(error) from error


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(profile_id: int, tool_id: int) -> Response:
    try:
        delete_tool_service(profile_id, tool_id)
    except KeyError as error:
        raise _not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
