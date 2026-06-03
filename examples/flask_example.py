"""Flask integration example.

Run::

    python examples/flask_example.py

Endpoints:

- POST /markdown — convert Markdown text to DOCX
- POST /html — convert HTML text to DOCX
"""

from __future__ import annotations

from flask import Flask, Response, request

from pimd import PiMD

app = Flask(__name__)
engine = PiMD()


@app.route("/")
def root() -> dict:
    return {"service": "PiMD", "version": "0.1.0"}


@app.route("/markdown", methods=["POST"])
def convert_markdown():
    """Convert Markdown text (form field ``text``) to DOCX."""
    text = request.form.get("text", "")
    if not text:
        return {"error": "No text provided"}, 400

    docx_bytes = engine.md_text_to_docx_bytes(text)

    return Response(
        docx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=output.docx"},
    )


@app.route("/html", methods=["POST"])
def convert_html():
    """Convert HTML text (form field ``text``) to DOCX."""
    text = request.form.get("text", "")
    if not text:
        return {"error": "No text provided"}, 400

    docx_bytes = engine.html_text_to_docx_bytes(text)

    return Response(
        docx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=output.docx"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
