#!/usr/bin/env python3
"""
Proper SimulationInput Demo with Chief of Staff Agent

This demonstrates the correct A2A protocol architecture where:
1. SimulationInput specifies the Chief of Staff agent
2. The JSON-RPC service orchestrates the whole process automatically
3. Chief of Staff uses team formation tools to coordinate sub-agents
4. Sub-agents execute without tools (disable_tools=True)

This is the essence of the A2A protocol and proper simulation architecture.
"""

import asyncio
import sys
import os
import json
import aiohttp
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env file loading")

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mantis.proto.mantis.v1 import mantis_core_pb2
from mantis.service.jsonrpc_service import create_app


async def demonstrate_a2a_protocol():
    """Demonstrate proper A2A protocol usage with SimulationInput."""
    
    print("🎯 A2A Protocol Demonstration with SimulationInput")
    print("=" * 70)
    
    print("""
🔍 Architecture Overview:

1. SimulationInput specifies Chief of Staff as coordination agent
2. JSON-RPC service receives and processes the simulation request  
3. Chief of Staff agent is automatically instantiated with team formation tools
4. Chief of Staff uses get_random_agents_from_registry tool to select team
5. Sub-agents are invoked with disable_tools=True (no inappropriate tool usage)
6. Responses are aggregated and synthesized through the A2A protocol
7. Final SimulationOutput contains complete orchestration results

This is the essence of proper A2A protocol implementation!
""")
    
    # Show what the ideal SimulationInput looks like
    print("📋 Example SimulationInput JSON-RPC Request:")
    print("-" * 50)
    
    example_request = {
        "jsonrpc": "2.0",
        "method": "process_simulation_input",
        "params": {
            "context_id": "philosophical-inquiry-001",
            "parent_context_id": "",
            "query": "What are the characteristics of a life well lived?",
            "context": "Deep philosophical inquiry requiring multiple perspectives",
            "execution_strategy": "DIRECT",
            "min_depth": 0,
            "max_depth": 3,
            "agents": [
                {
                    "count": 1,
                    # In full implementation, this would specify Chief of Staff agent
                    # For now, the orchestrator defaults to Chief of Staff
                }
            ]
        },
        "id": "philosophical-inquiry-001"
    }
    
    print(json.dumps(example_request, indent=2))
    
    print("""
🚀 Key Benefits of this Architecture:

✅ Proper A2A protocol compliance through JSON-RPC
✅ Automatic orchestration - no manual agent driving  
✅ Chief of Staff uses appropriate team formation tools
✅ Sub-agents execute without tools (no inappropriate usage)
✅ Full context threading and artifact management
✅ Structured SimulationOutput with all protocol fields
✅ Recursive agent invocation capability
✅ Clean separation of concerns

This enables the codebase to do what it was designed for!
""")


async def test_simulation_input_jsonrpc():
    """Test SimulationInput through JSON-RPC service."""
    
    print("🎯 Testing SimulationInput with Chief of Staff via JSON-RPC")
    print("=" * 70)
    
    # Start the JSON-RPC service in the background
    print("🚀 Starting JSON-RPC service...")
    
    app = await create_app()
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    
    site = aiohttp.web.TCPSite(runner, "localhost", 8081)  # Use different port to avoid conflicts
    await site.start()
    
    print("✅ JSON-RPC service started on http://localhost:8081")
    
    try:
        # Test 1: Service Info
        print("\n📋 Test 1: Service Info")
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8081/info") as response:
                if response.status == 200:
                    info = await response.json()
                    print(f"✅ Service: {info['service_name']}")
                    print(f"✅ Version: {info['version']}")
                    print(f"✅ A2A Compliant: {info['a2a_compliant']}")
                    print(f"✅ Supported Methods: {', '.join(info['supported_methods'])}")
                else:
                    print(f"❌ Service info failed: HTTP {response.status}")
                    return
        
        # Test 2: Health Check
        print("\n🏥 Test 2: Health Check")
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8081/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Status: {health['status']}")
                    print(f"✅ Orchestrator: {health['orchestrator_initialized']}")
                else:
                    print(f"❌ Health check failed: HTTP {response.status}")
                    return
        
        # Test 3: Process SimulationInput - Chief of Staff Coordination
        print("\n🎭 Test 3: SimulationInput with Chief of Staff")
        
        # Create SimulationInput request with RECURSION_POLICY_MUST
        simulation_request = {
            "jsonrpc": "2.0",
            "method": "process_simulation_input",
            "params": {
                "context_id": "philosophical-inquiry-001",
                "query": """As Chief of Staff, coordinate a comprehensive philosophical analysis of the question: "What are the characteristics of a life well lived?"

Your task:
1. Use your team formation tools to assemble a diverse team of 3 specialists (philosophers, ethicists, etc.)
2. Coordinate their analysis from different philosophical perspectives
3. Synthesize their insights into a coherent philosophical framework

Focus on multiple schools of thought including virtue ethics, existentialism, and eudaimonia.""",
                "execution_strategy": "DIRECT",
                "max_depth": 1,
                "min_depth": 1,
                "context": "Deep philosophical inquiry requiring coordinated multi-perspective analysis",
                "agents": [{
                    "count": 1,
                    "recursion_policy": "RECURSION_POLICY_MUST"
                }]
            },
            "id": 1
        }
        
        print(f"📤 Sending SimulationInput request...")
        print(f"📋 Context ID: {simulation_request['params']['context_id']}")
        print(f"📋 Query Length: {len(simulation_request['params']['query'])} characters")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8081/jsonrpc", 
                json=simulation_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                response_data = await response.json()
                
                if response.status == 200 and "result" in response_data:
                    result = response_data["result"]
                    print("\n✅ SimulationInput processed successfully!")
                    print(f"📋 Context ID: {result['context_id']}")
                    print(f"📋 Execution Strategy: {result.get('execution_strategy', 'N/A')}")
                    print(f"📋 Recursion Depth: {result.get('recursion_depth', 'N/A')}")
                    
                    # Count artifacts to show team effectiveness
                    artifact_count = len(result.get('response_artifacts', []))
                    print(f"📋 Team Artifacts Created: {artifact_count}")
                    
                    # Show execution result
                    if "execution_result" in result:
                        exec_result = result["execution_result"]
                        print(f"📋 Execution Status: {exec_result['status']}")
                        
                        if "error_info" in exec_result:
                            print(f"❌ Error: {exec_result['error_info']['error_message']}")
                    
                    # Show response message
                    if "response_message" in result and result["response_message"]:
                        response_msg = result["response_message"]
                        print(f"📋 Response Message ID: {response_msg['message_id']}")
                        
                        if "content" in response_msg and response_msg["content"]:
                            content_text = response_msg["content"][0]["text"]
                            
                            # Check if this looks like wrapped output (AgentRunResult)
                            if content_text.startswith("AgentRunResult(output='"):
                                # Extract the actual output from the wrapper
                                try:
                                    import ast
                                    # Try to parse as literal
                                    start = content_text.find("output='") + 8
                                    end = content_text.rfind("'")
                                    if start > 7 and end > start:
                                        unwrapped_text = content_text[start:end]
                                        # Unescape the content
                                        unwrapped_text = unwrapped_text.replace("\\'", "'").replace("\\n", "\n")
                                        content_text = unwrapped_text
                                except:
                                    # If parsing fails, show as-is
                                    pass
                            
                            print("\n📜 Chief of Staff Response:")
                            print("=" * 60)
                            print(content_text)
                            print("=" * 60)
                    
                    # Show artifacts - FULL CONTENT
                    if "response_artifacts" in result and result["response_artifacts"]:
                        print(f"\n📦 Artifacts Created: {len(result['response_artifacts'])}")
                        for i, artifact in enumerate(result["response_artifacts"], 1):
                            print(f"\n📦 Artifact {i}: {artifact['name']}")
                            print(f"📝 Description: {artifact['description']}")
                            print("📄 Content:")
                            print("-" * 40)
                            
                            # Show full artifact content
                            for part in artifact.get("parts", []):
                                part_text = part.get("text", "")
                                
                                # Check if this looks like wrapped output
                                if part_text.startswith("AgentRunResult(output='"):
                                    try:
                                        start = part_text.find("output='") + 8
                                        end = part_text.rfind("'")
                                        if start > 7 and end > start:
                                            unwrapped_text = part_text[start:end]
                                            # Unescape the content
                                            unwrapped_text = unwrapped_text.replace("\\'", "'").replace("\\n", "\n")
                                            part_text = unwrapped_text
                                    except:
                                        pass
                                
                                print(part_text)
                            print("-" * 40)
                
                elif "error" in response_data:
                    error = response_data["error"]
                    print(f"❌ JSON-RPC Error: {error['code']} - {error['message']}")
                    if "data" in error:
                        print(f"❌ Error Data: {error['data']}")
                else:
                    print(f"❌ Unexpected response format: {response.status}")
                    print(f"Response: {response_data}")
        
        print("\n🎉 JSON-RPC test completed!")
        
    except Exception as e:
        print(f"❌ Test execution error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up the service
        print("\n🧹 Cleaning up JSON-RPC service...")
        await runner.cleanup()


async def main():
    """Main demonstration function."""
    
    # Check environment
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Please set your Anthropic API key to run this demo")
        sys.exit(1)
    
    print("🚀 Mantis SimulationInput + JSON-RPC A2A Protocol Demo")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Run A2A protocol demonstration
    await demonstrate_a2a_protocol()
    
    print("\n" + "=" * 70)
    
    # Run actual JSON-RPC service test
    await test_simulation_input_jsonrpc()


if __name__ == "__main__":
    asyncio.run(main())