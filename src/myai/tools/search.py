"""Search-related tool factories."""

from __future__ import annotations

import os
from typing import Any, Iterable, List, Optional, Sequence, TypedDict, Union, cast
from urllib.parse import quote_plus, unquote

import requests

from myai.llm.tool import ToolBlueprint

from .base import ToolDependencyError, ToolProvider
from .registry import ToolRegistry
from .settings import ToolSettings

GOOGLE_SEARCH_DESCRIPTION = """
    Search for current information and fetch detailed content from result pages.
    Use this when you need up-to-date information, facts, news, or research on any topic.
    This tool not only finds relevant pages but also extracts their full content for detailed analysis.

    :param query: The search query (required)
    :param num_results: Number of results to return, 1-5 (optional, defaults to 3)
    :param fetch_content: Whether to fetch full page content for detailed info (optional, defaults to True)
    :return: Dictionary with search results including titles, URLs, snippets, and full page content
    """


class SearchResult(TypedDict):
    """Basic search result information."""

    title: str
    url: str
    snippet: str


class EnhancedSearchResult(SearchResult, total=False):
    """Search result optionally containing full page content."""

    full_content: str


class SearchResponse(TypedDict, total=False):
    """Structured search response returned to callers."""

    query: str
    results: List[EnhancedSearchResult]
    total_found: int
    search_info: Any


class SearchToolkit:
    """Encapsulates search and web-scraping helpers."""

    def __init__(self, settings: ToolSettings, *, session: Optional[requests.Session] = None) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._headers = {"User-Agent": settings.user_agent}
        self._headers.update(settings.extra_http_headers)

    @property
    def session(self) -> requests.Session:
        return self._session

    def google_search_simple(self, query: str, num_results: int = 5) -> Union[SearchResponse, str]:
        """Perform a DuckDuckGo HTML search and parse results."""
        try:
            soup = self._fetch_html(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
        except requests.RequestException as exc:
            return f"Search failed: {exc}"
        except ToolDependencyError as exc:
            return str(exc)

        results: List[EnhancedSearchResult] = []
        nodes = cast(Sequence[Any], soup.find_all("div", attrs={"class": "web-result"}))

        for node in nodes[:num_results]:
            tag = cast(Any, node)
            title_tag = tag.find("h2")
            link_tag = tag.find("a", attrs={"class": "result__a"})
            snippet_tag = tag.find("a", attrs={"class": "result__snippet"})

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text().strip()
            url = link_tag.get("href", "")
            snippet = snippet_tag.get_text().strip() if snippet_tag else "No description available"
            results.append(
                EnhancedSearchResult(title=title, url=url, snippet=snippet)
            )

        if not results:
            return self.search_alternative(query, num_results)

        return SearchResponse(query=query, results=results, total_found=len(results))

    def search_alternative(self, query: str, num_results: int = 5) -> SearchResponse:
        """Use Bing as a fallback search provider."""
        try:
            soup = self._fetch_html(
                f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}"
            )
        except requests.RequestException as exc:
            return SearchResponse(
                query=query,
                results=[
                    EnhancedSearchResult(
                        title="Search Error",
                        url="",
                        snippet=f"Unable to perform search: {exc}",
                    )
                ],
                total_found=0,
            )
        except ToolDependencyError as exc:
            return SearchResponse(
                query=query,
                results=[
                    EnhancedSearchResult(title="Dependency Error", url="", snippet=str(exc))
                ],
                total_found=0,
            )

        results: List[EnhancedSearchResult] = []
        nodes = cast(Sequence[Any], soup.find_all("li", attrs={"class": "b_algo"}))

        for node in nodes[:num_results]:
            tag = cast(Any, node)
            title_tag = tag.find("h2")
            link_tag = tag.find("a")
            snippet_tag = tag.find("p") or tag.find("div", attrs={"class": "b_caption"})

            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text().strip()
            url = link_tag.get("href", "")
            snippet = (
                snippet_tag.get_text().strip() if snippet_tag else "No description available"
            )
            if len(snippet) > 200:
                snippet = f"{snippet[:200]}..."

            results.append(
                EnhancedSearchResult(title=title, url=url, snippet=snippet)
            )

        return SearchResponse(query=query, results=results, total_found=len(results))

    def fetch_page_content(self, url: str, max_length: int = 2000) -> str:
        """Download and sanitize page text for a given URL."""
        cleaned_url = self._normalize_duckduckgo_redirect(url)

        try:
            response = self.session.get(
                cleaned_url,
                headers=self._headers,
                timeout=self._settings.http_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return f"Could not fetch content from {cleaned_url}: {exc}"

        try:
            soup = self._to_soup(response.text)
        except ToolDependencyError as exc:
            return str(exc)

        for tag in ["script", "style", "nav", "header", "footer", "aside"]:
            for element in cast(Sequence[Any], soup.find_all(tag)):
                cast(Any, element).decompose()

        text = self._collapse_text(soup.get_text())
        if len(text) > max_length:
            return f"{text[:max_length]}..."
        return text

    def google_search_enhanced(
        self,
        query: str,
        num_results: int = 3,
        fetch_content: bool = True,
    ) -> Union[SearchResponse, str]:
        """Perform search and optionally hydrate full page content."""
        search_results = self.google_search_simple(query, num_results)

        if isinstance(search_results, str) or not fetch_content:
            return search_results

        results = []
        for result in search_results.get("results", []):
            if not result.get("url"):
                result["full_content"] = "No URL available"
                results.append(result)
                continue

            content = self.fetch_page_content(result["url"])
            result["full_content"] = content
            results.append(result)

        return SearchResponse(
            query=search_results.get("query", query),
            results=results,
            total_found=len(results),
        )

    def google_search_api(self, query: str, num_results: int = 5) -> Union[SearchResponse, str]:
        """Query the Google Custom Search JSON API when credentials exist."""
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        if not api_key or not engine_id:
            return (
                "Error: Google Search API credentials not found. Set GOOGLE_SEARCH_API_KEY "
                "and GOOGLE_SEARCH_ENGINE_ID environment variables."
            )

        try:
            response = self.session.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": engine_id,
                    "q": query,
                    "num": min(num_results, 10),
                },
                timeout=self._settings.http_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return f"API search failed: {exc}"

        data = response.json()
        items = data.get("items", [])
        results: List[EnhancedSearchResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                EnhancedSearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", "No description available"),
                )
            )

        return SearchResponse(
            query=query,
            results=results,
            total_found=len(results),
            search_info=data.get("searchInformation"),
        )

    def _fetch_html(self, url: str, params: Optional[dict[str, Any]] = None):
        response = self.session.get(
            url,
            headers=self._headers,
            params=params,
            timeout=self._settings.http_timeout,
        )
        response.raise_for_status()
        return self._to_soup(response.text)

    @staticmethod
    def _normalize_duckduckgo_redirect(url: str) -> str:
        if url.startswith("//duckduckgo.com/l/?uddg="):
            return unquote(url.split("uddg=")[1].split("&")[0])
        return url

    @staticmethod
    def _collapse_text(text: str) -> str:
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return " ".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _to_soup(html: str):
        try:
            from bs4 import BeautifulSoup  # type: ignore import
        except ImportError as exc:  # pragma: no cover - dependency error path
            raise ToolDependencyError(
                "beautifulsoup4 package not installed. Run: pip install beautifulsoup4"
            ) from exc

        return cast(Any, BeautifulSoup(html, "html.parser"))


def create_search_toolkit(settings: ToolSettings) -> SearchToolkit:
    """Factory that builds a search toolkit instance."""

    return SearchToolkit(settings)


def create_search_tools(
    settings: ToolSettings, *, toolkit: Optional[SearchToolkit] = None
) -> Iterable[ToolBlueprint]:
    """Construct web-search tool blueprints."""

    toolkit = toolkit or create_search_toolkit(settings)

    return (
        ToolBlueprint(
            name="google_search",
            base_description=GOOGLE_SEARCH_DESCRIPTION.strip(),
            function=toolkit.google_search_enhanced,
        ),
    )


class SearchToolProvider(ToolProvider):
    """Register search related tools with a registry."""

    def __init__(self, settings: ToolSettings) -> None:
        self._settings = settings

    def register_tools(self, registry: ToolRegistry) -> None:
        registry.extend(create_search_tools(self._settings))


__all__ = [
    "SearchResult",
    "EnhancedSearchResult",
    "SearchResponse",
    "SearchToolkit",
    "create_search_toolkit",
    "create_search_tools",
    "SearchToolProvider",
]
