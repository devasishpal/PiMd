"""Django integration example.

Add to your Django project's ``views.py``::

    from examples.django_example import convert_markdown_view, convert_html_view

Then wire URLs in ``urls.py``::

    from django.urls import path
    from examples.django_example import convert_markdown_view, convert_html_view

    urlpatterns = [
        path("api/markdown/", convert_markdown_view, name="convert-markdown"),
        path("api/html/", convert_html_view, name="convert-html"),
    ]
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from pimd import PiMD

engine = PiMD()


def convert_markdown_view(request: HttpRequest) -> HttpResponse:
    """Convert POSTed Markdown text to a DOCX response."""
    if request.method != "POST":
        return HttpResponse(status=405)

    text = request.POST.get("text", "")
    if not text:
        return HttpResponse("No text provided", status=400)

    docx_bytes = engine.md_text_to_docx_bytes(text)

    return HttpResponse(
        docx_bytes,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="output.docx"'},
    )


def convert_html_view(request: HttpRequest) -> HttpResponse:
    """Convert POSTed HTML text to a DOCX response."""
    if request.method != "POST":
        return HttpResponse(status=405)

    text = request.POST.get("text", "")
    if not text:
        return HttpResponse("No text provided", status=400)

    docx_bytes = engine.html_text_to_docx_bytes(text)

    return HttpResponse(
        docx_bytes,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="output.docx"'},
    )
