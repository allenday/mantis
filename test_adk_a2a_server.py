#!/usr/bin/env python3
"""
Test script for ADK A2A server implementation.

This tests the FastAPI-based A2A server that wraps ADK agents to verify
proper A2A protocol compliance.
"""

import asyncio
import json
import uuid
import aiohttp
from typing import Dict, Any

async def test_agent_card_endpoint():
    """Test /.well-known/agent.json endpoint."""
    print("🔍 Testing agent card endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:9053/.well-known/agent.json") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✓ Agent card retrieved successfully")
                    print(f"  Agent: {data.get('name')}")
                    print(f"  Description: {data.get('description', '')[:100]}...")
                    print(f"  URL: {data.get('url')}")
                    print(f"  Protocol Version: {data.get('protocolVersion')}")
                    return True
                else:
                    print(f"❌ Agent card request failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Agent card request failed: {e}")
            return False

async def test_message_send():
    """Test A2A message/send endpoint."""
    print("\n🔍 Testing message/send endpoint...")
    
    # Create A2A message/send request
    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello, can you introduce yourself as Chief of Staff?"}],
        "kind": "message",
        "messageId": f"test-msg-{uuid.uuid4().hex[:8]}"
    }
    
    request_data = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": message
        },
        "id": f"req-{uuid.uuid4().hex[:8]}"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            print("Sending A2A message/send request...")
            async with session.post(
                "http://localhost:9053/",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✓ message/send request successful")
                    
                    if "result" in data and "id" in data["result"]:
                        task_id = data["result"]["id"]
                        print(f"  Task ID: {task_id}")
                        return task_id
                    else:
                        print(f"❌ No task ID in response: {data}")
                        return None
                else:
                    text = await response.text()
                    print(f"❌ message/send request failed: {response.status}")
                    print(f"  Response: {text}")
                    return None
        except Exception as e:
            print(f"❌ message/send request failed: {e}")
            return None

async def test_task_get(task_id: str, max_attempts: int = 10):
    """Test A2A tasks/get endpoint."""
    print(f"\n🔍 Testing tasks/get endpoint for task {task_id}...")
    
    request_data = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {
            "id": task_id
        },
        "id": f"req-{uuid.uuid4().hex[:8]}"
    }
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(max_attempts):
            try:
                print(f"  Attempt {attempt + 1}/{max_attempts}...")
                async with session.post(
                    "http://localhost:9053/",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "result" in data:
                            result = data["result"]
                            status = result.get("status", {})
                            state = status.get("state")
                            
                            print(f"  Task state: {state}")
                            
                            if state == "completed":
                                print("✓ Task completed successfully")
                                if "result" in result:
                                    print(f"  Response: {result['result'][:200]}...")
                                elif "history" in result and result["history"]:
                                    # Look for agent response in history
                                    for msg in result["history"]:
                                        if msg.get("role") == "agent":
                                            parts = msg.get("parts", [])
                                            if parts:
                                                print(f"  Response: {parts[0].get('text', '')[:200]}...")
                                            break
                                return True
                            elif state == "failed":
                                print("❌ Task failed")
                                if "error" in status:
                                    print(f"  Error: {status['error']}")
                                return False
                            elif state in ["pending", "running"]:
                                print(f"  Task still {state}, waiting...")
                                await asyncio.sleep(2)
                                continue
                        else:
                            print(f"❌ No result in response: {data}")
                            return False
                    else:
                        text = await response.text()
                        print(f"❌ tasks/get request failed: {response.status}")
                        print(f"  Response: {text}")
                        return False
            except Exception as e:
                print(f"❌ tasks/get request failed: {e}")
                return False
        
        print(f"❌ Task did not complete after {max_attempts} attempts")
        return False

async def test_a2a_server():
    """Test the complete A2A server functionality."""
    print("🧪 Testing ADK A2A Server")
    print("=" * 50)
    
    # Test 1: Agent card
    agent_card_ok = await test_agent_card_endpoint()
    if not agent_card_ok:
        print("❌ Agent card test failed - server may not be running")
        return False
    
    # Test 2: Message/send
    task_id = await test_message_send()
    if not task_id:
        print("❌ Message/send test failed")
        return False
    
    # Test 3: Task/get
    task_completed = await test_task_get(task_id)
    if not task_completed:
        print("❌ Tasks/get test failed")
        return False
    
    print("\n✅ All A2A protocol tests passed!")
    return True

async def start_server_and_test():
    """Start the ADK A2A server and run tests."""
    from src.mantis.adk.a2a_server import create_chief_of_staff_a2a_server
    
    print("🚀 Starting ADK A2A server...")
    server = create_chief_of_staff_a2a_server(port=9053)
    
    # Start server in background
    server_task = asyncio.create_task(server.start_server())
    
    # Give server time to start
    await asyncio.sleep(3)
    
    try:
        # Run tests
        success = await test_a2a_server()
        return success
    finally:
        # Clean up
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    async def main():
        # Check if server is already running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:9053/docs") as response:
                    if response.status == 200:
                        print("📡 Server already running, testing existing instance...")
                        success = await test_a2a_server()
                        return success
        except:
            pass
        
        # Start server and test
        print("📡 Starting new server instance...")
        return await start_server_and_test()
    
    success = asyncio.run(main())
    if success:
        print("\n🎉 ADK A2A server test completed successfully!")
    else:
        print("\n💥 ADK A2A server test failed")