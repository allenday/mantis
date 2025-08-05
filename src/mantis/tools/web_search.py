"""
Web search tool with DuckDuckGo integration.

This tool enables agents to perform web searches using DuckDuckGo, providing
relevant results for research and information gathering with rate limiting,
result processing, and comprehensive error handling.
"""

import re
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

from pydantic import BaseModel, Field, ConfigDict

from .web_fetch import WebFetchTool, WebFetchConfig


class SearchResult(BaseModel):
    """Individual search result from web search."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Text snippet/description from the result")
    source: Optional[str] = Field(None, description="Source domain of the result")
    rank: int = Field(..., description="Ranking position in search results")
    relevance_score: Optional[float] = Field(None, description="Calculated relevance score")


class SearchFilters(BaseModel):
    """Filters for web search operations."""

    region: Optional[str] = Field(None, description="Region code for search results (e.g., 'us-en')")
    safe_search: str = Field("moderate", description="Safe search level: 'strict', 'moderate', 'off'")
    time_filter: Optional[str] = Field(None, description="Time filter: 'd' (day), 'w' (week), 'm' (month), 'y' (year)")
    content_type: Optional[str] = Field(None, description="Content type filter: 'news', 'images', 'videos'")


class SearchResponse(BaseModel):
    """Response model for web search operations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(default_factory=list, description="List of search results")
    total_results: int = Field(..., description="Total number of results found")
    search_time_ms: float = Field(..., description="Time taken for search in milliseconds")
    success: bool = Field(..., description="Whether the search was successful")
    error_message: Optional[str] = Field(None, description="Error message if search failed")
    suggestions: List[str] = Field(default_factory=list, description="Search suggestions if available")


class WebSearchConfig(BaseModel):
    """Configuration for web search operations."""

    max_results: int = Field(10, description="Maximum number of results to return")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    user_agent: str = Field("Mantis-Agent/1.0 (Web Search Tool)", description="User agent string for searches")
    rate_limit_requests: int = Field(30, description="Max requests per minute")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")
    default_region: str = Field("wt-wt", description="Default region for searches")
    default_safe_search: str = Field("moderate", description="Default safe search level")
    enable_suggestions: bool = Field(True, description="Enable search suggestions")


class WebSearchTool:
    """Web search tool with DuckDuckGo integration."""

    def __init__(self, config: Optional[WebSearchConfig] = None):
        self.config = config or WebSearchConfig()

        # Create WebFetchTool for HTTP requests with search-specific settings
        fetch_config = WebFetchConfig(
            timeout=self.config.timeout,
            user_agent=self.config.user_agent,
            rate_limit_requests=self.config.rate_limit_requests,
            rate_limit_window=self.config.rate_limit_window,
            verify_ssl=True,
            # Allow DuckDuckGo domains
            allowed_domains=["duckduckgo.com", "html.duckduckgo.com", "api.duckduckgo.com"],
        )
        self.web_fetch = WebFetchTool(fetch_config)

        # DuckDuckGo endpoints
        self.search_url = "https://html.duckduckgo.com/html/"
        self.suggestions_url = "https://duckduckgo.com/ac/"

    async def __aenter__(self):
        """Async context manager entry."""
        await self.web_fetch.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.web_fetch.__aexit__(exc_type, exc_val, exc_tb)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove extra whitespace and normalize
        text = re.sub(r"\s+", " ", text.strip())

        # Remove HTML entities (basic ones)
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        return text

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    def _calculate_relevance_score(self, result: SearchResult, query: str) -> float:
        """Calculate relevance score for a search result."""
        try:
            query_lower = query.lower()
            title_lower = result.title.lower()
            snippet_lower = result.snippet.lower()

            score = 0.0

            # Base score from rank (higher rank = lower score)
            score += max(0, 1.0 - (result.rank - 1) * 0.1)

            # Title relevance (weighted heavily)
            title_matches = sum(1 for word in query_lower.split() if word in title_lower)
            score += (title_matches / len(query_lower.split())) * 0.5

            # Snippet relevance
            snippet_matches = sum(1 for word in query_lower.split() if word in snippet_lower)
            score += (snippet_matches / len(query_lower.split())) * 0.3

            # Exact phrase bonus
            if query_lower in title_lower:
                score += 0.3
            elif query_lower in snippet_lower:
                score += 0.2

            return min(1.0, score)

        except Exception:
            # Fallback to rank-based scoring
            return max(0, 1.0 - (result.rank - 1) * 0.1)

    def _parse_duckduckgo_html(self, html_content: str, query: str) -> List[SearchResult]:
        """Parse DuckDuckGo HTML search results."""
        results = []

        try:
            # Basic HTML parsing using regex (simple but effective for DuckDuckGo)
            # Look for result divs with class="result" or similar patterns

            # Pattern for DuckDuckGo results
            result_pattern = r'<div[^>]*class="[^"]*result[^"]*"[^>]*>.*?</div>'
            result_matches = re.findall(result_pattern, html_content, re.DOTALL | re.IGNORECASE)

            if not result_matches:
                # Try alternative pattern for web results
                result_pattern = r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>.*?<span[^>]*class="[^"]*result__title[^"]*"[^>]*>(.*?)</span>.*?<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>'
                alt_matches = re.findall(result_pattern, html_content, re.DOTALL | re.IGNORECASE)

                for i, (url, title, snippet) in enumerate(alt_matches[: self.config.max_results]):
                    results.append(
                        SearchResult(
                            title=self._clean_text(re.sub(r"<[^>]+>", "", title)),
                            url=url.strip(),
                            snippet=self._clean_text(re.sub(r"<[^>]+>", "", snippet)),
                            source=self._extract_domain(url),
                            rank=i + 1,
                        )
                    )

            # If still no results, try a more generic approach
            if not results:
                # Look for any links that might be results
                link_pattern = r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
                links = re.findall(link_pattern, html_content)

                # Filter out DuckDuckGo internal links and create basic results
                external_links = [
                    (url, title)
                    for url, title in links
                    if not any(domain in url for domain in ["duckduckgo.com", "javascript:", "mailto:", "#"])
                    and url.startswith("http")
                ]

                for i, (url, title) in enumerate(external_links[: self.config.max_results]):
                    results.append(
                        SearchResult(
                            title=self._clean_text(title),
                            url=url.strip(),
                            snippet="",  # No snippet available in this parsing method
                            source=self._extract_domain(url),
                            rank=i + 1,
                        )
                    )

        except Exception:
            # If parsing fails completely, return empty results
            # This ensures the tool fails gracefully
            pass

        # Calculate relevance scores
        for result in results:
            result.relevance_score = self._calculate_relevance_score(result, query)

        return results

    async def search(
        self, query: str, limit: Optional[int] = None, filters: Optional[SearchFilters] = None
    ) -> SearchResponse:
        """
        Perform a web search using DuckDuckGo.

        Args:
            query: Search query string
            limit: Maximum number of results to return (defaults to config.max_results)
            filters: Optional search filters

        Returns:
            SearchResponse with search results and metadata
        """
        start_time = time.time()
        limit = limit or self.config.max_results
        filters = filters or SearchFilters()

        try:
            # Build search parameters
            params = {
                "q": query,
                "kl": filters.region or self.config.default_region,
                "p": "1" if filters.safe_search == "strict" else "0" if filters.safe_search == "off" else "-1",
            }

            # Add time filter if specified
            if filters.time_filter:
                params["df"] = filters.time_filter

            # Make the search request
            search_url_with_params = f"{self.search_url}?{urlencode(params)}"

            response = await self.web_fetch.fetch_url(search_url_with_params)

            if not response.success:
                return SearchResponse(
                    query=query,
                    results=[],
                    total_results=0,
                    search_time_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error_message=f"Search request failed: {response.error_message}",
                )

            # Parse results from HTML
            results = self._parse_duckduckgo_html(response.content, query)

            # Limit results
            if limit and limit < len(results):
                results = results[:limit]

            # Get search suggestions if enabled
            suggestions = []
            if self.config.enable_suggestions:
                suggestions = await self._get_suggestions(query)

            search_time = (time.time() - start_time) * 1000

            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
                success=True,
                suggestions=suggestions,
            )

        except Exception as e:
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=f"Search failed: {str(e)}",
            )

    async def search_with_filters(
        self, query: str, filters: SearchFilters, limit: Optional[int] = None
    ) -> SearchResponse:
        """
        Perform a web search with specific filters.

        Args:
            query: Search query string
            filters: Search filters to apply
            limit: Maximum number of results to return

        Returns:
            SearchResponse with filtered search results
        """
        return await self.search(query, limit=limit, filters=filters)

    async def _get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions for a query."""
        try:
            # DuckDuckGo autocomplete endpoint
            params = {"q": query, "callback": "autocompleteCallback"}

            suggestions_url = f"{self.suggestions_url}?{urlencode(params)}"
            response = await self.web_fetch.fetch_url(suggestions_url)

            if response.success:
                # Parse JSONP response
                content = response.content
                if content.startswith("autocompleteCallback(") and content.endswith(");"):
                    json_content = content[21:-2]  # Remove JSONP wrapper

                    import json

                    data = json.loads(json_content)

                    # Extract suggestions (DuckDuckGo format)
                    if isinstance(data, list) and len(data) > 1:
                        suggestions = data[1]  # Second element contains suggestions
                        return [s.get("phrase", "") for s in suggestions if isinstance(s, dict)]

            return []

        except Exception:
            return []

    async def get_search_suggestions(self, query: str) -> List[str]:
        """
        Get search suggestions for a query.

        Args:
            query: Query to get suggestions for

        Returns:
            List of suggested search queries
        """
        return await self._get_suggestions(query)

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "search": self,
            "search_with_filters": self,
            "get_search_suggestions": self,
        }
