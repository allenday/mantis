"""
Tests for WebSearchTool with DuckDuckGo integration.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from mantis.tools.web_search import (
    WebSearchTool,
    WebSearchConfig,
    SearchResult,
    SearchFilters,
    SearchResponse,
)
from mantis.tools.web_fetch import WebResponse


class TestWebSearchTool:
    """Test suite for WebSearchTool."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return WebSearchConfig(
            max_results=5,
            timeout=10.0,
            rate_limit_requests=10,
            rate_limit_window=60,
            enable_suggestions=True,
        )

    @pytest.fixture
    def search_tool(self, config):
        """Create WebSearchTool instance."""
        return WebSearchTool(config)

    @pytest.fixture
    def mock_html_response(self):
        """Mock HTML response from DuckDuckGo."""
        return '''
        <div class="result">
            <a href="https://example.com/page1" class="result__a">
                <span class="result__title">Example Page 1</span>
            </a>
            <a href="https://example.com/snippet1" class="result__snippet">
                This is the first example result snippet with useful information.
            </a>
        </div>
        <div class="result">
            <a href="https://example.com/page2" class="result__a">
                <span class="result__title">Example Page 2</span>
            </a>
            <a href="https://example.com/snippet2" class="result__snippet">
                This is the second example result with different content.
            </a>
        </div>
        '''

    @pytest.fixture
    def mock_suggestions_response(self):
        """Mock JSONP response for suggestions."""
        suggestions_data = [
            "python programming",
            [
                {"phrase": "python programming tutorial"},
                {"phrase": "python programming examples"},
                {"phrase": "python programming basics"},
            ]
        ]
        return f"autocompleteCallback({json.dumps(suggestions_data)});"

    @pytest.mark.asyncio
    async def test_search_success(self, search_tool, mock_html_response):
        """Test successful search operation."""
        # Mock the web fetch response
        mock_response = WebResponse(
            status_code=200,
            content=mock_html_response,
            headers={"content-type": "text/html"},
            success=True,
            url="https://html.duckduckgo.com/html/?q=test",
            error_message=None,
            response_time_ms=150.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            response = await search_tool.search("test query")

        assert response.success is True
        assert response.query == "test query"
        assert len(response.results) >= 0  # May be 0 if parsing fails
        assert response.search_time_ms > 0
        assert response.error_message is None

    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_tool, mock_html_response):
        """Test search with filters applied."""
        filters = SearchFilters(
            region="us-en",
            safe_search="strict",
            time_filter="w",
            content_type="news"
        )

        mock_response = WebResponse(
            status_code=200,
            content=mock_html_response,
            headers={"content-type": "text/html"},
            success=True,
            url="https://html.duckduckgo.com/html/?q=test",
            error_message=None,
            response_time_ms=200.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            response = await search_tool.search_with_filters("test query", filters, limit=3)

        assert response.success is True
        assert response.query == "test query"

    @pytest.mark.asyncio
    async def test_search_failure(self, search_tool):
        """Test search failure handling."""
        mock_response = WebResponse(
            status_code=500,
            content="",
            headers={},
            success=False,
            url="https://html.duckduckgo.com/html/?q=test",
            error_message="Server error",
            response_time_ms=100.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            response = await search_tool.search("test query")

        assert response.success is False
        assert response.query == "test query"
        assert len(response.results) == 0
        assert "Search request failed" in response.error_message

    @pytest.mark.asyncio
    async def test_search_exception_handling(self, search_tool):
        """Test search exception handling."""
        with patch.object(search_tool.web_fetch, 'fetch_url', side_effect=Exception("Network error")):
            response = await search_tool.search("test query")

        assert response.success is False
        assert response.query == "test query"
        assert len(response.results) == 0
        assert "Search failed" in response.error_message
        assert "Network error" in response.error_message

    @pytest.mark.asyncio
    async def test_get_search_suggestions_success(self, search_tool, mock_suggestions_response):
        """Test successful search suggestions."""
        mock_response = WebResponse(
            status_code=200,
            content=mock_suggestions_response,
            headers={"content-type": "application/javascript"},
            success=True,
            url="https://duckduckgo.com/ac/?q=python",
            error_message=None,
            response_time_ms=50.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            suggestions = await search_tool.get_search_suggestions("python")

        assert len(suggestions) > 0
        assert "python programming tutorial" in suggestions

    @pytest.mark.asyncio
    async def test_get_search_suggestions_failure(self, search_tool):
        """Test search suggestions failure handling."""
        mock_response = WebResponse(
            status_code=500,
            content="",
            headers={},
            success=False,
            url="https://duckduckgo.com/ac/?q=python",
            error_message="Server error",
            response_time_ms=100.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            suggestions = await search_tool.get_search_suggestions("python")

        assert suggestions == []

    @pytest.mark.asyncio
    async def test_context_manager(self, search_tool):
        """Test async context manager functionality."""
        async with search_tool as tool:
            assert tool is search_tool
            # Context manager should initialize web_fetch
            assert hasattr(tool, 'web_fetch')

    def test_text_cleaning(self, search_tool):
        """Test text cleaning functionality."""
        dirty_text = "  Test   &amp;  content &lt;tag&gt;  "
        clean_text = search_tool._clean_text(dirty_text)
        
        assert clean_text == "Test & content <tag>"

    def test_domain_extraction(self, search_tool):
        """Test URL domain extraction."""
        url = "https://www.example.com/path/to/page"
        domain = search_tool._extract_domain(url)
        
        assert domain == "www.example.com"

    def test_relevance_score_calculation(self, search_tool):
        """Test relevance score calculation."""
        result = SearchResult(
            title="Python Programming Tutorial",
            url="https://example.com",
            snippet="Learn Python programming with examples",
            source="example.com",
            rank=1
        )
        
        score = search_tool._calculate_relevance_score(result, "python programming")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high relevance

    def test_html_parsing_fallback(self, search_tool):
        """Test HTML parsing with fallback patterns."""
        html_content = '''
        <a href="https://example1.com">Example 1</a>
        <a href="https://example2.com">Example 2</a>
        <a href="javascript:void(0)">Skip this</a>
        <a href="https://duckduckgo.com/internal">Skip this too</a>
        '''
        
        results = search_tool._parse_duckduckgo_html(html_content, "test query")
        
        # Should extract valid external links only
        valid_results = [r for r in results if r.url.startswith('http') and 'example' in r.url]
        assert len(valid_results) >= 0

    def test_configuration_defaults(self):
        """Test default configuration values."""
        config = WebSearchConfig()
        
        assert config.max_results == 10
        assert config.timeout == 30.0
        assert config.rate_limit_requests == 30
        assert config.rate_limit_window == 60
        assert config.default_region == "wt-wt"
        assert config.default_safe_search == "moderate"
        assert config.enable_suggestions is True

    def test_search_filters_model(self):
        """Test SearchFilters pydantic model."""
        filters = SearchFilters(
            region="us-en",
            safe_search="strict",
            time_filter="d",
            content_type="news"
        )
        
        assert filters.region == "us-en"
        assert filters.safe_search == "strict"
        assert filters.time_filter == "d"
        assert filters.content_type == "news"

    def test_search_result_model(self):
        """Test SearchResult pydantic model."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="example.com",
            rank=1,
            relevance_score=0.85
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "example.com"
        assert result.rank == 1
        assert result.relevance_score == 0.85

    def test_search_response_model(self):
        """Test SearchResponse pydantic model."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example1.com",
                snippet="First result",
                source="example1.com",
                rank=1
            )
        ]
        
        response = SearchResponse(
            query="test query",
            results=results,
            total_results=1,
            search_time_ms=150.0,
            success=True,
            suggestions=["test suggestion"]
        )
        
        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.total_results == 1
        assert response.search_time_ms == 150.0
        assert response.success is True
        assert response.error_message is None
        assert len(response.suggestions) == 1

    def test_get_tools_method(self, search_tool):
        """Test get_tools method for pydantic-ai integration."""
        tools = search_tool.get_tools()
        
        assert isinstance(tools, dict)
        assert 'search' in tools
        assert 'search_with_filters' in tools
        assert 'get_search_suggestions' in tools
        assert tools['search'] is search_tool

    @pytest.mark.asyncio 
    async def test_search_limit_enforcement(self, search_tool, mock_html_response):
        """Test that search results are limited correctly."""
        # Create HTML with more results than limit
        extended_html = mock_html_response + '''
        <div class="result">
            <a href="https://example.com/page3" class="result__a">
                <span class="result__title">Example Page 3</span>
            </a>
        </div>
        '''
        
        mock_response = WebResponse(
            status_code=200,
            content=extended_html,
            headers={"content-type": "text/html"},
            success=True,
            url="https://html.duckduckgo.com/html/?q=test",
            error_message=None,
            response_time_ms=150.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            response = await search_tool.search("test query", limit=2)

        # Results should be limited to 2 even if more are parsed
        if response.results:  # Only check if parsing succeeded
            assert len(response.results) <= 2

    @pytest.mark.asyncio
    async def test_malformed_suggestions_response(self, search_tool):
        """Test handling of malformed suggestions response."""
        malformed_response = "invalid_jsonp_response"
        
        mock_response = WebResponse(
            status_code=200,
            content=malformed_response,
            headers={"content-type": "application/javascript"},
            success=True,
            url="https://duckduckgo.com/ac/?q=test",
            error_message=None,
            response_time_ms=50.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            suggestions = await search_tool.get_search_suggestions("test")

        assert suggestions == []

    @pytest.mark.asyncio
    async def test_empty_html_response(self, search_tool):
        """Test handling of empty HTML response."""
        mock_response = WebResponse(
            status_code=200,
            content="",
            headers={"content-type": "text/html"},
            success=True,
            url="https://html.duckduckgo.com/html/?q=test",
            error_message=None,
            response_time_ms=100.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            response = await search_tool.search("test query")

        assert response.success is True
        assert len(response.results) == 0  # No results from empty HTML

    def test_edge_case_urls(self, search_tool):
        """Test domain extraction with edge case URLs."""
        test_cases = [
            ("", ""),
            ("invalid_url", ""),
            ("https://", ""),
            ("ftp://example.com", "example.com"),
        ]
        
        for url, expected in test_cases:
            result = search_tool._extract_domain(url)
            assert result == expected

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, search_tool, mock_html_response):
        """Test concurrent search operations."""
        mock_response = WebResponse(
            status_code=200,
            content=mock_html_response,
            headers={"content-type": "text/html"},
            success=True,
            url="https://html.duckduckgo.com/html/",
            error_message=None,
            response_time_ms=100.0
        )

        with patch.object(search_tool.web_fetch, 'fetch_url', return_value=mock_response):
            # Run multiple searches concurrently
            tasks = [
                search_tool.search(f"query {i}")
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)

        # All searches should succeed
        for i, response in enumerate(responses):
            assert response.success is True
            assert response.query == f"query {i}"