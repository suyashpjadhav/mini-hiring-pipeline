"""Web page view routes."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def index_page() -> HTMLResponse:
    """Render placeholder index page."""
    html_content = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "  <title>Mini Hiring Pipeline</title>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Mini Hiring Pipeline</h1>\n"
        "  <p>Scaffold ready</p>\n"
        "</body>\n"
        "</html>\n"
    )
    return HTMLResponse(content=html_content)
