from typing import Any, List, cast

import pytest  # type: ignore[import]
import requests

pytest.importorskip("bs4")

from myai.tools.search import SearchToolkit  # noqa: E402
from myai.tools.settings import ToolSettings  # noqa: E402


class FakeResponse:
    def __init__(self, *, text: str = "", status_code: int = 200, json_data: Any | None = None):
        self.text = text
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status code {self.status_code}")

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("JSON data not provided")
        return self._json_data


class FakeSession:
    def __init__(self, responses: List[FakeResponse]):
        self._responses = list(responses)
        self.calls = []

    def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
        if not self._responses:
            raise AssertionError("Unexpected extra HTTP request")
        self.calls.append((args, kwargs))
        return self._responses.pop(0)


@pytest.fixture
def tool_settings(tmp_path) -> ToolSettings:
    return ToolSettings(data_directory=tmp_path)


def test_google_search_simple_parses_results(tool_settings: ToolSettings) -> None:
    duck_html = """
    <div class='web-result'>
        <h2>Example Title</h2>
        <a class='result__a' href='https://example.com'>Example</a>
        <a class='result__snippet'>Snippet text</a>
    </div>
    """
    session = FakeSession([FakeResponse(text=duck_html)])
    toolkit = SearchToolkit(tool_settings, session=cast(requests.Session, session))

    result = toolkit.google_search_simple("test query", num_results=1)

    assert isinstance(result, dict)
    payload = cast(dict[str, Any], result)
    assert payload["query"] == "test query"
    assert payload["total_found"] == 1
    first_result = cast(dict[str, Any], payload["results"][0])
    assert first_result["title"] == "Example Title"
    assert first_result["url"] == "https://example.com"


def test_google_search_simple_falls_back_to_bing(tool_settings: ToolSettings) -> None:
    empty_html = "<html></html>"
    bing_html = """
    <li class='b_algo'>
        <h2>Fallback Title</h2>
        <a href='https://fallback.example'>Fallback</a>
        <p>Fallback snippet content</p>
    </li>
    """
    session = FakeSession([FakeResponse(text=empty_html), FakeResponse(text=bing_html)])
    toolkit = SearchToolkit(tool_settings, session=cast(requests.Session, session))

    result = toolkit.google_search_simple("fallback test", num_results=1)

    assert isinstance(result, dict)
    payload = cast(dict[str, Any], result)
    assert payload["total_found"] == 1
    first_result = cast(dict[str, Any], payload["results"][0])
    assert first_result["title"] == "Fallback Title"


def test_google_search_enhanced_fetches_full_content(tool_settings: ToolSettings) -> None:
    duck_html = """
    <div class='web-result'>
        <h2>Example Title</h2>
        <a class='result__a' href='https://example.com'>Example</a>
        <a class='result__snippet'>Snippet text</a>
    </div>
    """
    page_html = """
    <html>
        <body>
            <header>Header should be removed</header>
            <p>Content that remains</p>
            <script>Should be removed</script>
        </body>
    </html>
    """
    session = FakeSession([FakeResponse(text=duck_html), FakeResponse(text=page_html)])
    toolkit = SearchToolkit(tool_settings, session=cast(requests.Session, session))

    result = toolkit.google_search_enhanced("test", num_results=1, fetch_content=True)

    assert isinstance(result, dict)
    payload = cast(dict[str, Any], result)
    assert payload["total_found"] == 1
    enhanced = cast(dict[str, Any], payload["results"][0])
    assert "Content that remains" in enhanced["full_content"]
    assert "Header" not in enhanced["full_content"]


def test_google_search_api_missing_credentials_returns_error(tool_settings: ToolSettings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)

    toolkit = SearchToolkit(
        tool_settings, session=cast(requests.Session, FakeSession([]))
    )

    result = toolkit.google_search_api("test")

    assert isinstance(result, str)
    assert "credentials" in result


def test_google_search_api_returns_results(tool_settings: ToolSettings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "engine")

    api_response = {
        "items": [
            {"title": "API Title", "link": "https://api.example", "snippet": "API snippet"}
        ],
        "searchInformation": {"totalResults": "1"},
    }
    session = FakeSession([FakeResponse(json_data=api_response)])
    toolkit = SearchToolkit(tool_settings, session=cast(requests.Session, session))

    result = toolkit.google_search_api("api test")

    assert isinstance(result, dict)
    payload = cast(dict[str, Any], result)
    assert payload["total_found"] == 1
    first_result = cast(dict[str, Any], payload["results"][0])
    assert first_result["title"] == "API Title"