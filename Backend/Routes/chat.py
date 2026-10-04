"""Workbook chat completion endpoint."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from ..Functions.chat import ChatAccessError, clear_chat_history, complete_chat, get_chat_history, stream_chat_events
from ..Models.chat import ChatRequest, ChatResponse

router = APIRouter(
    prefix="/profiles/{profile_id}/workbooks/{workbook_id}/chat",
    tags=["chat"],
)


@router.get("", response_model=list[dict[str, Any]])
def read_chat_history(profile_id: int, workbook_id: int) -> list[dict[str, Any]]:
    try:
        return get_chat_history(profile_id, workbook_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Profile or workbook not found") from error


@router.post("", response_model=ChatResponse)
def send_chat_message(profile_id: int, workbook_id: int, payload: ChatRequest) -> Any:
    if payload.stream:
        def event_stream():
            stream_events = stream_chat_events(profile_id, workbook_id, payload)
            try:
                for event in stream_events:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except KeyError:
                yield f"data: {json.dumps({'type': 'error', 'status': 404, 'message': 'Profile, workbook, API key, or tool not found'})}\n\n"
            except ChatAccessError as error:
                yield f"data: {json.dumps({'type': 'error', 'status': 403, 'message': str(error)})}\n\n"
            except OSError:
                yield f"data: {json.dumps({'type': 'error', 'status': 500, 'message': 'Could not access workbook chat storage'})}\n\n"
            except ValueError as error:
                yield f"data: {json.dumps({'type': 'error', 'status': 422, 'message': str(error)})}\n\n"
            except Exception as error:
                yield f"data: {json.dumps({'type': 'error', 'status': 502, 'message': str(error)})}\n\n"
            finally:
                stream_events.close()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    try:
        return complete_chat(profile_id, workbook_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Profile, workbook, API key, or tool not found") from error
    except ChatAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(status_code=500, detail="Could not access workbook chat storage") from error


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_history(profile_id: int, workbook_id: int) -> Response:
    try:
        clear_chat_history(profile_id, workbook_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Profile or workbook not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
