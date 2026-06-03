"""FastAPI integration example.

Run::

    uvicorn examples.fastapi_app:app --reload

Or::

    python -m examples.fastapi_app

Endpoints:

- POST /markdown — convert uploaded Markdown file to DOCX
- POST /html — convert uploaded HTML file to DOCX
- POST /markdown/text — convert Markdown text to DOCX bytes
- POST /html/text — convert HTML text to DOCX bytes
"""

from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response

from pimd import PiMD

app = FastAPI(title="PiMD Conversion API", version="0.1.0")
engine = PiMD()


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "PiMD", "version": "0.1.0"}


@app.post("/markdown")
async def convert_markdown(file: UploadFile = File(...)) -> Response:
    """Upload a Markdown file and receive a DOCX document."""
    content = await file.read()
    docx_bytes = engine.md_text_to_docx_bytes(content.decode("utf-8"))
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{file.filename or "output"}.docx"'},
    )


@app.post("/html")
async def convert_html(file: UploadFile = File(...)) -> Response:
    """Upload an HTML file and receive a DOCX document."""
    content = await file.read()
    docx_bytes = engine.html_text_to_docx_bytes(content.decode("utf-8"))
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{file.filename or "output"}.docx"'},
    )


@app.post("/markdown/text")
async def convert_markdown_text(
    text: str = Form(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
) -> Response:
    """Convert Markdown text (form-encoded) to DOCX bytes."""
    opts = {}
    if title:
        opts["title"] = title
    if author:
        opts["author"] = author
    docx_bytes = engine.md_text_to_docx_bytes(text, **opts)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/html/text")
async def convert_html_text(
    text: str = Form(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
) -> Response:
    """Convert HTML text (form-encoded) to DOCX bytes."""
    opts = {}
    if title:
        opts["title"] = title
    if author:
        opts["author"] = author
    docx_bytes = engine.html_text_to_docx_bytes(text, **opts)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# For streaming large files
@app.post("/markdown/stream")
async def convert_markdown_stream(file: UploadFile = File(...)) -> Response:
    """Convert Markdown to DOCX with streaming response."""
    content = await file.read()
    docx_bytes = engine.md_text_to_docx_bytes(content.decode("utf-8"))

    import io

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{file.filename or "output"}.docx"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
