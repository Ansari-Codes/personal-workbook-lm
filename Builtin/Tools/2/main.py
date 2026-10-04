from __future__ import annotations

import base64
import os
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

import requests


def _metadata(record: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: record.data[field] for field in fields if field in record.data}


def _content_value(content: str | bytes) -> dict[str, str]:
    if isinstance(content, bytes):
        return {"content_base64": base64.b64encode(content).decode("ascii"), "encoding": "base64"}
    return {"content": content, "encoding": "utf-8"}


def _truncate(value: str, limit: int = 8000) -> str:
    return value if len(value) <= limit else value[:limit] + f"\n... [truncated {len(value) - limit} chars]"


def list_sources(workbook: Any) -> list[dict[str, Any]]:
    fields = ("id", "name", "description", "kind", "folder", "created_at", "updated_at")
    return [_metadata(source, fields) for source in workbook.sources.list()]


def read_source(id: int, workbook: Any) -> dict[str, Any]:
    source = workbook.sources.load(id)
    return {"id": source.id, "name": source.name, **_content_value(source.read())}


def list_outputs(workbook: Any) -> list[dict[str, Any]]:
    fields = ("id", "name", "description", "folder", "created_at", "updated_at")
    return [_metadata(output, fields) for output in workbook.outputs.list()]


def read_output(id: int, workbook: Any) -> dict[str, Any]:
    output = workbook.outputs.load(id)
    return {"id": output.id, "name": output.name, **_content_value(output.read())}


def read_pdf(workbook: Any, source_id: int | None = None, output_id: int | None = None, max_pages: int = 30) -> dict[str, Any]:
    if (source_id is None) == (output_id is None):
        raise ValueError("Choose exactly one PDF source or output")
    record = workbook.sources.load(source_id) if source_id is not None else workbook.outputs.load(output_id)
    if Path(record.name).suffix.lower() != ".pdf":
        raise ValueError(f"{record.name} is not a PDF file")
    content = record.read()
    raw = content if isinstance(content, bytes) else content.encode("utf-8")
    if len(raw) > 50 * 1024 * 1024:
        raise ValueError("PDFs must be 50 MB or smaller")
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(raw), strict=False)
    page_limit = min(100, max(1, int(max_pages)))
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages[:page_limit])
    return {"name": record.name, "pages_total": len(reader.pages), "pages_read": min(len(reader.pages), page_limit), "truncated": len(reader.pages) > page_limit or len(text) > 30000, "text": _truncate(text, 30000)}


def create_output(name: str, content: str, workbook: Any, description: str = "", folder: str = "") -> dict[str, Any]:
    output = workbook.outputs.add(name=name, description=description, content=content, folder=folder)
    return _metadata(output, ("id", "name", "description", "folder", "created_at", "updated_at"))


def edit_output(id: int, workbook: Any, name: str | None = None, description: str | None = None, folder: str | None = None, content: str | None = None) -> dict[str, Any]:
    output = workbook.outputs.load(id)
    if name is not None:
        output.rename(name)
    if description is not None:
        output.redescribe(description)
    if folder is not None:
        output.set_folder(folder)
    if content is not None:
        output.write(content)
    return _metadata(output, ("id", "name", "description", "folder", "created_at", "updated_at"))


def web_search(query: str, max_results: int = 5, workbook: Any = None) -> dict[str, Any]:
    response = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1, "no_redirect": 1}, timeout=15).json()
    limit = min(20, max(1, int(max_results)))
    results = []
    if response.get("AbstractText"):
        results.append({"title": response.get("Heading", query), "url": response.get("AbstractURL", ""), "snippet": response["AbstractText"]})
    for topic in response.get("RelatedTopics", []):
        if len(results) >= limit:
            break
        if isinstance(topic, dict) and "Text" in topic:
            results.append({"title": topic["Text"][:80], "url": topic.get("FirstURL", ""), "snippet": topic["Text"]})
    return {"query": query, "results": results[:limit]}


def fetch_url(url: str, timeout: float = 15, workbook: Any = None) -> dict[str, Any]:
    response = requests.get(url, timeout=float(timeout), headers={"User-Agent": "pawm-workbook/1.0"})
    return {"url": response.url, "status": response.status_code, "content_type": response.headers.get("content-type", ""), "content": _truncate(response.text)}


def http_request(method: str, url: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None, body: Any = None, timeout: float = 15, workbook: Any = None) -> dict[str, Any]:
    options: dict[str, Any] = {"headers": headers or {}, "params": params or {}, "timeout": float(timeout)}
    if isinstance(body, (dict, list)):
        options["json"] = body
    elif body is not None:
        options["data"] = body
    response = requests.request(method.upper(), url, **options)
    try:
        parsed = response.json()
    except ValueError:
        parsed = _truncate(response.text)
    return {"status": response.status_code, "headers": dict(response.headers), "body": parsed}


def _run(command: list[str], timeout: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pawm-tool-") as directory:
        env = {key: os.environ[key] for key in ("PATH", "LANG", "TZ", "SYSTEMROOT", "COMSPEC") if key in os.environ}
        env.update({"HOME": directory, "TMPDIR": directory, "TEMP": directory, "TMP": directory})
        try:
            result = subprocess.run(command, cwd=directory, env=env, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"returncode": -9, "stdout": "", "stderr": f"timed out after {timeout}s"}
        return {"returncode": result.returncode, "stdout": _truncate(result.stdout.decode("utf-8", "replace")), "stderr": _truncate(result.stderr.decode("utf-8", "replace"))}


def run_python(code: str, timeout: float = 10, workbook: Any = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pawm-python-") as directory:
        script = Path(directory) / "script.py"
        script.write_text(code, encoding="utf-8")
        return _run([sys.executable, "-I", "-B", str(script)], float(timeout))


def run_shell(command: str, timeout: float = 10, workbook: Any = None) -> dict[str, Any]:
    shell_command = [os.environ.get("COMSPEC", "cmd.exe"), "/c", command] if os.name == "nt" else ["/bin/sh", "-c", command]
    return _run(shell_command, float(timeout))


def remember(key: str, value: Any = None, workbook: Any = None) -> dict[str, Any]:
    if workbook is None:
        return {"error": "Workbook context is required"}
    memory = workbook.config.get("tool_memory", {})
    if not isinstance(memory, dict):
        memory = {}
    memory[key] = value
    workbook.config.set("tool_memory", memory)
    return {"ok": True, "key": key}


def recall(key: str | None = None, workbook: Any = None) -> dict[str, Any]:
    if workbook is None:
        return {"error": "Workbook context is required"}
    memory = workbook.config.get("tool_memory", {})
    if not isinstance(memory, dict):
        memory = {}
    return {"entries": memory} if key is None else {"key": key, "value": memory.get(key)}
