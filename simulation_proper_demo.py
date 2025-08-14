#!/usr/bin/env python3
"""
Mantis Coordination Diagnostic Tool

A debugging/QA tool that exposes raw structured logs, actual artifacts,
and SimulationOutput data for system diagnostics. No pretty presentations - 
just raw diagnostic information for debugging coordination issues.
"""

import asyncio
import sys
import json
import aiohttp
import argparse
import uuid
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Mantis Coordination Diagnostic Tool - Debug/QA focused",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--leader-url", 
        required=True,
        help="URL of the leader agent"
    )
    
    parser.add_argument(
        "--narrator-url",
        required=True, 
        help="URL of the narrator agent"
    )
    
    parser.add_argument(
        "--query",
        default="What are the key success factors for modern software product development?",
        help="Query to send"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout per agent call"
    )
    
    return parser.parse_args()


async def extract_structured_logs(container_name: str, since_seconds: int = 120) -> Dict[str, Any]:
    """Extract coordination-related logs from Docker container."""
    try:
        # Get logs containing coordination activity
        coordination_patterns = [
            "get_random_agents_from_registry",
            "Successfully completed recursive agent invocation", 
            "artifacts_count",
            "🎯 ORCHESTRATOR:",
            "bound_invoke_agent_by_name called",
            "bound_invoke_multiple_agents called",
            "Stored structured result",
            "ChiefOfStaffRouter",
            "ADK processing",
            "TOOL_COMPLETED"
        ]
        
        # Build grep pattern
        pattern = "|".join(coordination_patterns)
        cmd = f"docker logs {container_name} --since {since_seconds}s 2>&1 | grep -E '{pattern}' | tail -30"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        raw_logs = []
        structured_logs = []
        
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                raw_logs.append(line.strip())
                # Try to parse as JSON for structured data
                try:
                    log_entry = json.loads(line)
                    structured_logs.append(log_entry)
                except json.JSONDecodeError:
                    # Keep as raw text if not JSON
                    continue
        
        return {
            "container": container_name,
            "coordination_logs_raw": raw_logs,
            "coordination_logs_structured": structured_logs,
            "total_raw_entries": len(raw_logs),
            "total_structured_entries": len(structured_logs)
        }
    except Exception as e:
        return {
            "container": container_name,
            "error": str(e),
            "coordination_logs_raw": [],
            "coordination_logs_structured": []
        }


async def call_agent_and_extract_diagnostics(url: str, query: str, timeout_seconds: int = 60) -> Dict[str, Any]:
    """Call agent and return diagnostic information."""
    diagnostics = {
        "url": url,
        "query_length": len(query),
        "task_id": None,
        "final_state": None,
        "response_text": None,
        "response_length": 0,
        "processing_time_seconds": 0,
        "polling_attempts": 0,
        "errors": []
    }
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as session:
        try:
            # Step 1: Send message
            message_request = {
                "jsonrpc": "2.0",
                "method": "message/send", 
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": query}],
                        "kind": "message",
                        "messageId": str(uuid.uuid4())
                    },
                    "metadata": {
                        "request_type": "direct_agent_request"
                    }
                },
                "id": str(uuid.uuid4())
            }
            
            async with session.post(url, json=message_request, headers={"Content-Type": "application/json"}) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                send_result = await response.json()
                if "error" in send_result and send_result["error"] is not None:
                    raise Exception(f"JSON-RPC error: {send_result['error']}")
                
                task_id = send_result.get("result", {}).get("id")
                if not task_id:
                    raise Exception(f"No task ID: {send_result}")
                
                diagnostics["task_id"] = task_id
            
            # Step 2: Poll for result
            import time
            start_time = time.time()
            poll_count = 0
            
            while (time.time() - start_time) < timeout_seconds - 10:
                poll_count += 1
                await asyncio.sleep(2)
                
                task_request = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get", 
                    "params": {"id": task_id},
                    "id": str(uuid.uuid4())
                }
                
                try:
                    async with session.post(url, json=task_request, headers={"Content-Type": "application/json"}) as task_response:
                        if task_response.status != 200:
                            diagnostics["errors"].append(f"Poll {poll_count}: HTTP {task_response.status}")
                            continue
                        
                        task_result = await task_response.json()
                        if "error" in task_result and task_result["error"] is not None:
                            diagnostics["errors"].append(f"Poll {poll_count}: {task_result['error']}")
                            continue
                        
                        task_data = task_result.get("result", {})
                        task_state = task_data.get("status", {}).get("state")
                        
                        if task_state == "completed":
                            diagnostics["final_state"] = "completed"
                            result = task_data.get("result", "")
                            
                            # CRITICAL: Check if result is structured SimulationOutput or just text
                            if isinstance(result, dict) and "simulation_output" in result:
                                # Full structured response with SimulationOutput
                                diagnostics["response_text"] = result.get("text_response", "")
                                diagnostics["simulation_output"] = result.get("simulation_output", {})
                                diagnostics["structured_results_count"] = result.get("structured_results_count", 0)
                                diagnostics["context_id"] = result.get("context_id", "unknown")
                            else:
                                # Fallback: plain text response
                                diagnostics["response_text"] = str(result) if result else ""
                                
                            diagnostics["response_length"] = len(diagnostics["response_text"] or "")
                            diagnostics["processing_time_seconds"] = time.time() - start_time
                            diagnostics["polling_attempts"] = poll_count
                            return diagnostics
                        
                        elif task_state == "failed":
                            diagnostics["final_state"] = "failed"
                            diagnostics["errors"].append(f"Task failed: {task_data.get('status', {}).get('error', 'Unknown')}")
                            return diagnostics
                        
                        elif task_state in ["pending", "running"]:
                            continue
                        
                        else:
                            diagnostics["errors"].append(f"Unknown state: {task_state}")
                            return diagnostics
                
                except aiohttp.ClientError as e:
                    diagnostics["errors"].append(f"Poll {poll_count} network error: {e}")
                    continue
            
            # Timeout
            diagnostics["final_state"] = "timeout"
            diagnostics["processing_time_seconds"] = time.time() - start_time
            diagnostics["polling_attempts"] = poll_count
            diagnostics["errors"].append(f"Timed out after {timeout_seconds}s")
            return diagnostics
            
        except Exception as e:
            diagnostics["errors"].append(f"Call failed: {str(e)}")
            return diagnostics


def print_diagnostic_header():
    """Print diagnostic header."""
    print("=" * 80)
    print("MANTIS COORDINATION DIAGNOSTIC TOOL")
    print("=" * 80)
    print("Purpose: Raw diagnostic data for debugging and QA")
    print("Output: Structured logs, artifacts, and system state")
    print("=" * 80)


def print_diagnostic_section(title: str, data: Any):
    """Print a diagnostic section."""
    print(f"\n[{title.upper()}]")
    print("-" * len(title))
    if isinstance(data, dict):
        print(json.dumps(data, indent=2, default=str))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            print(f"  {i}: {item}")
    else:
        print(str(data))


async def main():
    """Main diagnostic execution."""
    args = parse_arguments()
    
    print_diagnostic_header()
    print(f"Leader URL: {args.leader_url}")
    print(f"Narrator URL: {args.narrator_url}")
    print(f"Query: {args.query[:100]}{'...' if len(args.query) > 100 else ''}")
    print(f"Timeout: {args.timeout}s per call")
    
    # Diagnostic data collection
    diagnostic_data = {
        "test_config": {
            "leader_url": args.leader_url,
            "narrator_url": args.narrator_url,
            "query_length": len(args.query),
            "timeout": args.timeout
        },
        "leader_diagnostics": {},
        "narrator_diagnostics": {},
        "structured_logs": {},
        "coordination_evidence": {}
    }
    
    try:
        # Step 1: Pre-call diagnostic setup
        print("\n[DIAGNOSTIC SETUP]")
        print("Ready to capture coordination activity during execution")
        
        # Step 2: Call leader with structured simulation query to trigger ChiefOfStaffRouter
        # Format as JSON-RPC simulation input to get full SimulationOutput back
        coordination_query = f"""JSON-RPC Call: process_simulation_input with params: {{
    "context_id": "diagnostic-{uuid.uuid4().hex[:8]}",
    "parent_context_id": "",
    "query": "Use your team formation tools to assemble a team and coordinate an analysis of: {args.query}. Your task: 1. Use get_random_agents_from_registry to select 3 agents, 2. Coordinate their analysis using your leadership approach, 3. Synthesize their insights into a coherent response.",
    "execution_strategy": "DIRECT",
    "max_depth": 2,
    "min_depth": 1,
    "agents": [
        {{
            "count": 1,
            "agent_type": "leader"
        }}
    ]
}}

Execute this simulation and return the full SimulationOutput with nested results and artifacts."""
        
        print_diagnostic_section("LEADER CALL STARTING", {
            "url": args.leader_url,
            "query_preview": coordination_query[:200] + "..."
        })
        
        leader_diagnostics = await call_agent_and_extract_diagnostics(
            args.leader_url,
            coordination_query,
            timeout_seconds=args.timeout
        )
        
        diagnostic_data["leader_diagnostics"] = leader_diagnostics
        print_diagnostic_section("LEADER DIAGNOSTICS", leader_diagnostics)
        
        if leader_diagnostics["final_state"] != "completed":
            print("\n❌ LEADER CALL FAILED - Cannot proceed to narrator")
            print_diagnostic_section("FINAL DIAGNOSTIC DATA", diagnostic_data)
            return
        
        # Step 3: Extract coordination activity logs
        coordination_logs = await extract_structured_logs("agent-server", 180)
        
        print_diagnostic_section("COORDINATION LOGS EXTRACTION", {
            "raw_logs_found": coordination_logs.get("total_raw_entries", 0),
            "structured_logs_found": coordination_logs.get("total_structured_entries", 0),
            "container": coordination_logs.get("container", "unknown"),
            "error": coordination_logs.get("error")
        })
        
        # Show raw coordination logs for debugging
        raw_logs = coordination_logs.get("coordination_logs_raw", [])
        if raw_logs:
            print_diagnostic_section("RAW COORDINATION ACTIVITY", raw_logs[:15])
        else:
            print_diagnostic_section("RAW COORDINATION ACTIVITY", "No coordination logs found")
        
        # Extract evidence from both raw and structured logs
        evidence = {
            "team_formation_calls": 0,
            "agent_invocations": 0,
            "adk_processing_events": 0,
            "orchestrator_events": 0,
            "tool_completions": 0,
            "errors": 0,
            "raw_log_samples": raw_logs[:5]  # First 5 raw logs for inspection
        }
        
        # Analyze raw logs for coordination evidence
        all_log_text = " ".join(raw_logs)
        evidence["team_formation_calls"] = all_log_text.count("get_random_agents_from_registry")
        evidence["agent_invocations"] = all_log_text.count("Successfully completed recursive agent invocation")
        evidence["adk_processing_events"] = all_log_text.count("ADK processing")
        evidence["orchestrator_events"] = all_log_text.count("🎯 ORCHESTRATOR:")
        evidence["tool_completions"] = all_log_text.count("TOOL_COMPLETED")
        
        # Also check structured logs
        structured_logs = coordination_logs.get("coordination_logs_structured", [])
        for log_entry in structured_logs:
            if log_entry.get("level") == "ERROR":
                evidence["errors"] += 1
        
        diagnostic_data["coordination_evidence"] = evidence
        print_diagnostic_section("COORDINATION EVIDENCE", evidence)
        
        # Step 4: Call narrator
        narrator_query = f"""Present the following coordination results in a clear format:

{leader_diagnostics['response_text']}

Format as professional analysis with sections and recommendations."""
        
        print_diagnostic_section("NARRATOR CALL STARTING", {
            "url": args.narrator_url,
            "input_length": len(narrator_query)
        })
        
        narrator_diagnostics = await call_agent_and_extract_diagnostics(
            args.narrator_url,
            narrator_query,
            timeout_seconds=args.timeout
        )
        
        diagnostic_data["narrator_diagnostics"] = narrator_diagnostics
        print_diagnostic_section("NARRATOR DIAGNOSTICS", narrator_diagnostics)
        
        # Step 5: Final diagnostic summary
        print_diagnostic_section("COORDINATION SUMMARY", {
            "leader_success": leader_diagnostics["final_state"] == "completed",
            "narrator_success": narrator_diagnostics["final_state"] == "completed",
            "total_response_chars": (leader_diagnostics["response_length"] + 
                                   narrator_diagnostics["response_length"]),
            "total_processing_time": (leader_diagnostics["processing_time_seconds"] + 
                                    narrator_diagnostics["processing_time_seconds"]),
            "coordination_evidence": evidence,
            "error_count": len(leader_diagnostics["errors"]) + len(narrator_diagnostics["errors"])
        })
        
        # Step 6: SimulationOutput artifacts (if available)
        if "simulation_output" in leader_diagnostics:
            simulation_output = leader_diagnostics["simulation_output"]
            print_diagnostic_section("SIMULATION OUTPUT SUMMARY", {
                "context_id": leader_diagnostics.get("context_id", "unknown"),
                "structured_results_count": leader_diagnostics.get("structured_results_count", 0),
                "response_artifacts_count": len(simulation_output.get("responseArtifacts", [])),
                "nested_results_count": len(simulation_output.get("results", [])),
                "final_state": simulation_output.get("finalState", "unknown")
            })
            
            # Show actual artifacts
            artifacts = simulation_output.get("responseArtifacts", [])
            if artifacts:
                print_diagnostic_section("RESPONSE ARTIFACTS", {
                    "total_artifacts": len(artifacts),
                    "artifacts": [
                        {
                            "artifact_id": artifact.get("artifactId", "unknown"),
                            "name": artifact.get("name", "unknown"),
                            "description": artifact.get("description", ""),
                            "parts_count": len(artifact.get("parts", []))
                        } for artifact in artifacts[:5]  # First 5 artifacts
                    ]
                })
            
            # Show nested coordination results
            nested_results = simulation_output.get("results", [])
            if nested_results:
                print_diagnostic_section("NESTED COORDINATION RESULTS", {
                    "total_nested_results": len(nested_results),
                    "nested_results_summary": [
                        {
                            "context_id": result.get("contextId", "unknown"),
                            "final_state": result.get("finalState", "unknown"),
                            "artifacts_count": len(result.get("responseArtifacts", []))
                        } for result in nested_results[:5]  # First 5 nested results
                    ]
                })
        
        # Step 7: Raw response samples for QA
        if leader_diagnostics["response_text"]:
            print_diagnostic_section("LEADER RESPONSE SAMPLE", 
                leader_diagnostics["response_text"][:500] + "..." if len(leader_diagnostics["response_text"]) > 500 else leader_diagnostics["response_text"])
        
        if narrator_diagnostics["response_text"]:
            print_diagnostic_section("NARRATOR RESPONSE SAMPLE",
                narrator_diagnostics["response_text"][:500] + "..." if len(narrator_diagnostics["response_text"]) > 500 else narrator_diagnostics["response_text"])
        
        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ DIAGNOSTIC FAILED: {str(e)}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())