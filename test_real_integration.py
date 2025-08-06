#!/usr/bin/env python3
"""
Real LLM agent integration test with actual tool usage.
This demonstrates that LLM agents can successfully use our tools.
"""
import asyncio
import os
from typing import Dict, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from mantis.tools import WebFetchTool, WebFetchConfig
from pydantic_ai import Agent, RunContext


async def test_real_webfetch_integration():
    """Test REAL LLM agent with REAL WebFetch tool making actual HTTP requests."""
    print('🧪 Testing REAL LLM agent with REAL WebFetch tool...')
    
    # Create REAL WebFetch tool
    config = WebFetchConfig(timeout=10.0, user_agent="Mantis-Real-Test/1.0")
    web_fetch_tool = WebFetchTool(config)
    
    # Create REAL pydantic-ai agent with Claude Haiku
    agent = Agent(
        'anthropic:claude-3-5-haiku-20241022',
        deps_type=Dict[str, Any],
        system_prompt='You are a helpful assistant that can fetch web content. When asked to fetch content from a URL, use the web_fetch tool to retrieve it and analyze what you find.'
    )
    
    # Register the REAL tool function
    @agent.tool
    async def web_fetch(ctx: RunContext[Dict[str, Any]], url: str) -> str:
        """Fetch content from a web URL."""
        try:
            print(f'  🌐 Making real HTTP request to: {url}')
            response = await web_fetch_tool.fetch_url(url)
            if response.success:
                print(f'  ✅ HTTP {response.status_code} - {len(response.content)} chars received')
                return f'Successfully fetched from {url}. Status: {response.status_code}. Content: {response.content}'
            else:
                print(f'  ❌ HTTP request failed: {response.error_message}')
                return f'Failed to fetch from {url}. Error: {response.error_message}'
        except Exception as e:
            print(f'  💥 Tool error: {str(e)}')
            return f'Tool error: {str(e)}'
    
    # Make REAL LLM call with REAL tool usage
    print('  🤖 Calling LLM agent to fetch and analyze JSON data...')
    result = await agent.run(
        'Please fetch the content from https://httpbin.org/json and tell me about the JSON structure you see.',
        deps={}
    )
    
    print(f'\n📋 Agent response:\n{result.output}')
    print(f'\n📊 Response length: {len(result.output)} characters')
    
    # Verify this was a real interaction
    response_lower = result.output.lower()
    success_indicators = [
        'httpbin' in response_lower,
        'json' in response_lower,
        len(result.output) > 100,
        any(word in response_lower for word in ['slideshow', 'title', 'author', 'slides'])  # httpbin.org/json content
    ]
    
    if all(success_indicators[:3]) and any(success_indicators[3:]):
        print('\n🎉 SUCCESS: Real LLM agent successfully used real WebFetch tool!')
        return True
    else:
        print('\n💥 FAILED: Integration did not work as expected')
        print(f'   Success indicators: {success_indicators}')
        return False


async def test_real_websearch_integration():
    """Test REAL LLM agent with REAL WebSearch tool."""
    print('\n🧪 Testing REAL LLM agent with REAL WebSearch tool...')
    
    from mantis.tools import WebSearchTool, WebSearchConfig
    
    # Create REAL WebSearch tool
    config = WebSearchConfig(max_results=3, timeout=10.0)
    web_search_tool = WebSearchTool(config)
    
    # Create REAL pydantic-ai agent
    agent = Agent(
        'anthropic:claude-3-5-haiku-20241022',
        deps_type=Dict[str, Any],
        system_prompt='You are a helpful assistant that can search the web. Use the web_search tool when asked to find information.'
    )
    
    @agent.tool
    async def web_search(ctx: RunContext[Dict[str, Any]], query: str) -> str:
        """Search the web for information."""
        try:
            print(f'  🔍 Making real web search for: {query}')
            results = await web_search_tool.search(query, max_results=3)
            
            if results.results:
                formatted_results = []
                for i, result in enumerate(results.results, 1):
                    formatted_results.append(f"{i}. {result.title}\n   URL: {result.url}\n   Snippet: {result.snippet}")
                
                search_summary = f"Found {len(results.results)} results for '{query}':\n\n" + "\n\n".join(formatted_results)
                print(f'  ✅ Found {len(results.results)} search results')
                return search_summary
            else:
                print('  ❌ No search results found')
                return f"No search results found for '{query}'"
                
        except Exception as e:
            print(f'  💥 Search error: {str(e)}')
            return f'Search error: {str(e)}'
    
    # Make REAL LLM call with REAL search
    print('  🤖 Calling LLM agent to search and summarize...')
    result = await agent.run(
        'Please search for "pydantic-ai tutorial" and summarize the most relevant resources you find.',
        deps={}
    )
    
    print(f'\n📋 Agent response:\n{result.output}')
    
    # Verify real search happened
    response_lower = result.output.lower()
    if 'pydantic' in response_lower and len(result.output) > 100:
        print('\n🎉 SUCCESS: Real LLM agent successfully used real WebSearch tool!')
        return True
    else:
        print('\n💥 FAILED: WebSearch integration did not work as expected')
        return False


async def main():
    """Run all real integration tests."""
    print('🚀 Starting REAL LLM Agent-Tool Integration Tests')
    print('=' * 60)
    
    tests = [
        test_real_webfetch_integration,
        test_real_websearch_integration,
    ]
    
    results = []
    for test_func in tests:
        try:
            success = await test_func()
            results.append(success)
        except Exception as e:
            print(f'\n💥 Test failed with exception: {e}')
            results.append(False)
    
    print('\n' + '=' * 60)
    print(f'📊 Integration Test Results: {sum(results)}/{len(results)} passed')
    
    if all(results):
        print('🎉 ALL INTEGRATION TESTS PASSED! LLM agents can use our tools!')
    else:
        print('❌ Some integration tests failed. Check the output above.')
    
    return all(results)


if __name__ == '__main__':
    asyncio.run(main())