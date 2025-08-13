"""
Clean Recursive Agent Invocation

Implements recursive agent calls with proper protobuf SimulationOutput aggregation.
No global state, clean dependency injection.
"""

import asyncio
from typing import Dict, Optional, TYPE_CHECKING
from ..observability.logger import get_structured_logger
from ..core.orchestrator import current_agent_context
from ..proto.mantis.v1 import mantis_core_pb2
from ..proto import a2a_pb2

if TYPE_CHECKING:
    from ..core.orchestrator import SimulationOrchestrator

logger = get_structured_logger(__name__)


async def invoke_agent_by_url(
    agent_url: str,
    query: str,
    agent_name: Optional[str] = None,
    context: Optional[str] = None,
) -> mantis_core_pb2.SimulationOutput:
    """
    Invoke agent directly by URL, bypassing registry lookup.

    Useful for direct coordination and N-replica querying where we know
    the exact agent endpoints.

    Args:
        agent_url: Direct URL to the agent (e.g., http://localhost:9203)
        query: Query to send to agent
        agent_name: Optional display name for the agent
        context: Optional context

    Returns:
        Complete SimulationOutput from the invoked agent

    Raises:
        Exception: If agent call fails
    """
    from .base import log_tool_invocation, log_tool_result

    agent_ctx = current_agent_context.get({})
    invoking_agent = agent_ctx.get("agent_name", "unknown")
    task_id = agent_ctx.get("task_id", "unknown")
    context_id = agent_ctx.get("context_id", "unknown")

    display_name = agent_name or f"Agent@{agent_url}"

    log_tool_invocation(
        "recursive_invocation",
        "invoke_agent_by_url",
        {"agent_url": agent_url, "agent_name": display_name, "query_length": len(query)},
    )

    logger.info(
        "Invoking agent directly by URL",
        structured_data={
            "invoking_agent": invoking_agent,
            "target_url": agent_url,
            "target_agent": display_name,
            "task_id": task_id,
            "context_id": context_id,
        },
    )

    try:
        # Use the existing direct A2A call function
        result = await _call_agent_directly_a2a(
            agent_name=display_name, agent_url=agent_url, query=query, context=context
        )

        log_tool_result(
            "recursive_invocation",
            "invoke_agent_by_url",
            {
                "agent_url": agent_url,
                "agent_name": display_name,
                "success": True,
                "response_length": (
                    len(result.response_message.content[0].text) if result.response_message.content else 0
                ),
            },
        )

        logger.info(
            "Successfully completed direct agent invocation by URL",
            structured_data={
                "invoking_agent": invoking_agent,
                "target_url": agent_url,
                "target_agent": display_name,
                "success": True,
            },
        )

        return result

    except Exception as e:
        logger.error(
            "Direct agent invocation by URL failed",
            structured_data={
                "invoking_agent": invoking_agent,
                "target_url": agent_url,
                "target_agent": display_name,
                "error": str(e),
                "task_id": task_id,
            },
        )
        raise


async def invoke_agent_by_name(
    agent_name: str,
    query: str,
    orchestrator: "SimulationOrchestrator",
    context: Optional[str] = None,
    max_depth: int = 1,
) -> mantis_core_pb2.SimulationOutput:
    """
    Invoke specific agent through recursive SimulationInput execution.

    Uses proper protobuf SimulationOutput with nested results aggregation.

    Args:
        agent_name: Agent to invoke (must exist in registry)
        query: Query to send to agent
        orchestrator: Orchestrator instance for execution
        context: Optional context
        max_depth: Maximum recursion depth

    Returns:
        Complete SimulationOutput from the invoked agent

    Raises:
        ValueError: If agent not found in registry
        Exception: If execution fails
    """
    agent_ctx = current_agent_context.get({})
    invoking_agent = agent_ctx.get("agent_name", "unknown")
    task_id = agent_ctx.get("task_id", "unknown")
    context_id = agent_ctx.get("context_id", "unknown")

    # Validate agent exists in registry
    await _validate_agent_exists(agent_name)

    # HOTFIX: Bypass registry complexity - hardcode agent URLs for basic coordination
    # This is a temporary fix to get coordination working without registry dependency

    logger.info(
        "🔧 HOTFIX: Using hardcoded agent URLs, bypassing registry",
        structured_data={
            "invoking_agent": invoking_agent,
            "target_agent": agent_name,
            "original_max_depth": max_depth,
        },
    )

    # Map actual Docker agent names to their container ports
    # These are the agents running in Docker containers with proper registry registration
    agent_url_map = {
        "John Malone": "http://localhost:9202",
        "Steve Jobs": "http://localhost:9203",
        "Peter Drucker": "http://localhost:9204",
        "Chief Of Staff": "http://localhost:9201",
        # Note: Other agents like Niccolo Machiavelli, Andrew Carnegie are available via agent-server multiplex
        # but we'll use direct container agents first for reliability
    }

    if agent_name in agent_url_map:
        # Use direct A2A call instead of recursive simulation
        return await _call_agent_directly_a2a(
            agent_name=agent_name, agent_url=agent_url_map[agent_name], query=query, context=context
        )

    # Fallback: Force max_depth to 0 for safety if not in hardcoded list
    max_depth = 0
    logger.warning(
        "Agent not in hardcoded list, using fallback with max_depth=0",
        structured_data={"agent_name": agent_name, "available_agents": list(agent_url_map.keys())},
    )

    logger.info(
        "Invoking agent through recursive simulation",
        structured_data={
            "invoking_agent": invoking_agent,
            "target_agent": agent_name,
            "task_id": task_id,
            "context_id": context_id,
            "max_depth": max_depth,
        },
    )

    try:
        # Create recursive SimulationInput
        from ..proto.mantis.v1 import mantis_core_pb2
        from ..tools.agent_registry import get_agent_by_name

        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.context_id = f"{context_id}-recursive-{agent_name.lower().replace(' ', '-')}"
        simulation_input.parent_context_id = context_id
        simulation_input.query = f"""You are {agent_name}. Please provide your perspective on the following:

{query}

{f"Additional context: {context}" if context else ""}

Please respond as {agent_name} would, drawing on your expertise and perspective. Keep your response focused and authentic to your role."""

        simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
        simulation_input.max_depth = max_depth

        # CRITICAL FIX: Specify which agent to use instead of defaulting to Chief of Staff
        try:
            target_agent_card = await get_agent_by_name(agent_name)
            if target_agent_card:
                # Create AgentSpec with the specific agent - populate the AgentInterface correctly
                from ..agent import AgentInterface as AgentInterfaceWrapper

                agent_wrapper = AgentInterfaceWrapper(target_agent_card)

                agent_spec = mantis_core_pb2.AgentSpec()
                # Populate the mantis_core AgentInterface (not a2a AgentInterface!)
                agent_spec.agent.agent_id = agent_wrapper.agent_id
                agent_spec.agent.name = agent_wrapper.name
                agent_spec.agent.description = agent_wrapper.description
                agent_spec.agent.capabilities_summary = agent_wrapper.capabilities_summary
                agent_spec.agent.persona_summary = agent_wrapper.persona_summary
                agent_spec.agent.role_preference = agent_wrapper.role_preference
                agent_spec.count = 1
                simulation_input.agents.append(agent_spec)

                logger.info(
                    "Added specific agent to simulation input",
                    structured_data={
                        "agent_name": agent_name,
                        "agent_id": agent_wrapper.agent_id,
                        "context_id": simulation_input.context_id,
                    },
                )
            else:
                logger.warning(
                    "Could not load specific agent, will use default", structured_data={"agent_name": agent_name}
                )
        except Exception as e:
            logger.warning(
                "Failed to load specific agent, will use default",
                structured_data={"agent_name": agent_name, "error": str(e)},
            )

        # Execute recursive simulation
        nested_output = await orchestrator.execute_simulation(simulation_input)

        # Aggregate nested artifacts to parent task (for legacy compatibility)
        await _aggregate_nested_output(
            parent_task_id=task_id, nested_output=nested_output, orchestrator=orchestrator, source_agent=agent_name
        )

        # Extract response text for logging
        response_text = "No response generated"
        if nested_output.response_message and nested_output.response_message.content:
            response_text = nested_output.response_message.content[0].text

        logger.info(
            "Successfully completed recursive agent invocation",
            structured_data={
                "invoking_agent": invoking_agent,
                "target_agent": agent_name,
                "response_length": len(response_text),
                "artifacts_in_nested": len(nested_output.response_artifacts),
            },
        )

        # Return the complete structured SimulationOutput instead of just text
        return nested_output

    except Exception as e:
        logger.error(
            "Recursive agent invocation failed",
            structured_data={
                "invoking_agent": invoking_agent,
                "target_agent": agent_name,
                "error": str(e),
                "task_id": task_id,
            },
        )
        raise


async def invoke_multiple_agents(
    agent_names: list,
    query_template: str,
    orchestrator: "SimulationOrchestrator",
    individual_contexts: Optional[list] = None,
    max_depth: int = 1,
) -> Dict[str, mantis_core_pb2.SimulationOutput]:
    """
    Invoke multiple agents in parallel with proper artifact aggregation.

    Args:
        agent_names: List of agent names to invoke
        query_template: Base query for all agents
        orchestrator: Orchestrator instance
        individual_contexts: Optional per-agent contexts
        max_depth: Maximum recursion depth

    Returns:
        Dictionary mapping agent names to complete SimulationOutput objects
    """
    agent_ctx = current_agent_context.get({})
    invoking_agent = agent_ctx.get("agent_name", "unknown")

    logger.info(
        "Invoking multiple agents in parallel",
        structured_data={
            "invoking_agent": invoking_agent,
            "target_agents": agent_names,
            "agent_count": len(agent_names),
        },
    )

    # Validate all agents exist
    for agent_name in agent_names:
        await _validate_agent_exists(agent_name)

    # Create parallel invocation tasks
    tasks = []
    for i, agent_name in enumerate(agent_names):
        context = individual_contexts[i] if individual_contexts and i < len(individual_contexts) else None
        task = invoke_agent_by_name(
            agent_name=agent_name, query=query_template, orchestrator=orchestrator, context=context, max_depth=max_depth
        )
        tasks.append((agent_name, task))

    # Execute in parallel
    try:
        responses = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        results: Dict[str, mantis_core_pb2.SimulationOutput] = {}
        for (agent_name, _), response in zip(tasks, responses):
            if isinstance(response, Exception):
                # Create error SimulationOutput for failed agents
                error_output = mantis_core_pb2.SimulationOutput()
                error_output.context_id = f"error-{agent_name}"
                error_output.final_state = a2a_pb2.TASK_STATE_FAILED

                # Create error message
                error_msg = a2a_pb2.Message()
                error_msg.role = a2a_pb2.ROLE_AGENT
                error_part = a2a_pb2.Part()
                error_part.text = f"Error: {str(response)}"
                error_msg.content.append(error_part)
                error_output.response_message.CopyFrom(error_msg)

                results[agent_name] = error_output
                logger.error(f"Agent {agent_name} failed", structured_data={"error": str(response)})
            else:
                # Type guard: response should be SimulationOutput if not an Exception
                assert isinstance(response, mantis_core_pb2.SimulationOutput), (
                    f"Expected SimulationOutput, got {type(response)}"
                )
                results[agent_name] = response

        successful_count = len([r for r in results.values() if r.final_state != a2a_pb2.TASK_STATE_FAILED])
        logger.info(
            "Multiple agent invocation completed",
            structured_data={
                "invoking_agent": invoking_agent,
                "successful_invocations": successful_count,
                "total_agents": len(agent_names),
            },
        )

        return results

    except Exception as e:
        logger.error(
            "Multiple agent invocation failed",
            structured_data={"invoking_agent": invoking_agent, "target_agents": agent_names, "error": str(e)},
        )
        raise


async def _call_agent_directly_a2a(
    agent_name: str, agent_url: str, query: str, context: Optional[str] = None
) -> mantis_core_pb2.SimulationOutput:
    """
    HOTFIX: Call agent directly via A2A protocol, bypassing registry complexity.
    """
    import aiohttp
    import uuid
    import asyncio

    logger.info(f"🔧 HOTFIX: Calling {agent_name} directly at {agent_url}")

    # CRITICAL FIX: Add agent availability validation before attempting coordination
    try:
        await _validate_agent_availability(agent_url, agent_name)
    except Exception as validation_error:
        logger.error(f"❌ HOTFIX: Agent {agent_name} at {agent_url} is not available: {validation_error}")
        return _create_unavailable_agent_output(agent_name, str(validation_error))

    try:
        # Format query with context
        full_query = f"""You are {agent_name}. Please provide your perspective on the following:

{query}

{f"Additional context: {context}" if context else ""}

Please respond as {agent_name} would, drawing on your expertise and perspective. Keep your response focused and authentic to your role."""

        async with aiohttp.ClientSession() as session:
            # Step 1: Send message/send
            message_request = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": full_query}],
                        "kind": "message",
                        "messageId": str(uuid.uuid4()),
                    }
                },
                "id": str(uuid.uuid4()),
            }

            async with session.post(
                agent_url,
                json=message_request,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    raise Exception(f"Message send failed: HTTP {response.status}")

                send_result = await response.json()
                if "error" in send_result and send_result["error"] is not None:
                    raise Exception(f"JSON-RPC error: {send_result['error']}")

                task_id = send_result.get("result", {}).get("id")
                if not task_id:
                    raise Exception(f"No task ID returned: {send_result}")

            # Step 2: Poll for result with reasonable timeout
            for poll_attempt in range(30):  # 60 seconds max
                await asyncio.sleep(2)

                tasks_request = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"id": task_id},
                    "id": str(uuid.uuid4()),
                }

                async with session.post(
                    agent_url,
                    json=tasks_request,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        continue

                    task_result = await response.json()
                    if "error" in task_result and task_result["error"] is not None:
                        raise Exception(f"Poll error: {task_result['error']}")

                    task_data = task_result.get("result", {})
                    task_state = task_data.get("status", {}).get("state")

                    if task_state == "completed":
                        result_text = task_data.get("result", "No response generated")

                        # Create SimulationOutput for consistency
                        output = mantis_core_pb2.SimulationOutput()
                        output.context_id = f"hotfix-{agent_name.lower().replace(' ', '-')}"
                        output.final_state = a2a_pb2.TASK_STATE_COMPLETED

                        # Create response message
                        response_msg = a2a_pb2.Message()
                        response_msg.role = a2a_pb2.ROLE_AGENT
                        response_part = a2a_pb2.Part()
                        response_part.text = result_text
                        response_msg.content.append(response_part)
                        output.response_message.CopyFrom(response_msg)

                        logger.info(f"✅ HOTFIX: {agent_name} responded successfully in {poll_attempt * 2} seconds")
                        return output

                    elif task_state == "failed":
                        error_info = task_data.get("status", {}).get("error", "Unknown error")
                        raise Exception(f"Task failed: {error_info}")

                    elif task_state in ["pending", "running"]:
                        continue

            raise Exception(f"Polling timeout after 60 seconds for {agent_name}")

    except Exception as e:
        logger.error(f"❌ HOTFIX: Direct A2A call to {agent_name} failed: {e}")

        # Return error SimulationOutput
        error_output = mantis_core_pb2.SimulationOutput()
        error_output.context_id = f"error-{agent_name.lower().replace(' ', '-')}"
        error_output.final_state = a2a_pb2.TASK_STATE_FAILED

        error_msg = a2a_pb2.Message()
        error_msg.role = a2a_pb2.ROLE_AGENT
        error_part = a2a_pb2.Part()
        error_part.text = f"Error calling {agent_name}: {str(e)}"
        error_msg.content.append(error_part)
        error_output.response_message.CopyFrom(error_msg)

        return error_output


async def _validate_agent_availability(agent_url: str, agent_name: str) -> None:
    """
    CRITICAL FIX: Validate that agent is reachable before attempting coordination.

    Performs a quick health check to prevent coordination failures and server disconnections.
    """
    import aiohttp
    import asyncio

    try:
        # Quick health check with short timeout
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5, connect=2)) as session:
            # Try to get agent card first
            async with session.get(f"{agent_url}/.well-known/agent.json") as response:
                if response.status == 200:
                    agent_card = await response.json()
                    actual_name = agent_card.get("name", "Unknown")
                    logger.info(
                        f"✅ HOTFIX: Agent {agent_name} is available at {agent_url} (actual name: {actual_name})"
                    )
                    return
                else:
                    raise Exception(f"Agent card endpoint returned HTTP {response.status}")

    except asyncio.TimeoutError:
        raise Exception("Agent health check timeout after 5s")
    except aiohttp.ClientError as e:
        raise Exception(f"Network error: {e}")
    except Exception as e:
        raise Exception(f"Health check failed: {e}")


def _create_unavailable_agent_output(agent_name: str, error_msg: str) -> mantis_core_pb2.SimulationOutput:
    """Create SimulationOutput for unavailable agent."""
    error_output = mantis_core_pb2.SimulationOutput()
    error_output.context_id = f"unavailable-{agent_name.lower().replace(' ', '-')}"
    error_output.final_state = a2a_pb2.TASK_STATE_FAILED

    error_msg_obj = a2a_pb2.Message()
    error_msg_obj.role = a2a_pb2.ROLE_AGENT
    error_part = a2a_pb2.Part()
    error_part.text = f"Agent {agent_name} is not available for coordination: {error_msg}"
    error_msg_obj.content.append(error_part)
    error_output.response_message.CopyFrom(error_msg_obj)

    return error_output


async def _validate_agent_exists(agent_name: str) -> None:
    """Validate that agent exists in registry - fail fast if not available."""
    from ..tools.agent_registry import list_all_agents
    from ..agent import AgentInterface

    try:
        # Get agents from registry - fail fast if unavailable
        all_agents = await list_all_agents()
        if not all_agents:
            raise RuntimeError("Registry returned no agents - agent validation failed")

        # Check if agent exists by name or ID
        available_agents = []
        for agent_card in all_agents:
            agent_interface = AgentInterface(agent_card)
            available_agents.extend([agent_interface.agent_id, agent_interface.name])

        if agent_name not in available_agents:
            unique_names = list(set(available_agents))[:10]
            available_list = ", ".join(unique_names)
            if len(unique_names) >= 10:
                available_list += "..."

            raise ValueError(f"Agent '{agent_name}' not found in registry. Available agents: {available_list}")

    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        raise ValueError(f"Error validating agent registry: {str(e)}")


async def _aggregate_nested_output(
    parent_task_id: str,
    nested_output: "mantis_core_pb2.SimulationOutput",
    orchestrator: "SimulationOrchestrator",
    source_agent: str,
) -> None:
    """
    Aggregate artifacts from nested SimulationOutput to parent task.

    This ensures artifacts from recursive agent calls are visible in final output.
    """
    try:
        parent_task = orchestrator.get_task_by_id(parent_task_id)
        if not parent_task:
            logger.warning(
                "Cannot aggregate artifacts - parent task not found",
                structured_data={"parent_task_id": parent_task_id, "source_agent": source_agent},
            )
            return

        artifacts_added = 0

        # Add all artifacts from nested output to parent task with proper attribution
        for artifact in nested_output.response_artifacts:
            # Create a copy to avoid protobuf reference issues
            new_artifact = parent_task.artifacts.add()
            new_artifact.CopyFrom(artifact)

            # Update artifact attribution to reflect the actual generating agent
            new_artifact.name = f"{source_agent}_response"
            new_artifact.description = f"Response from {source_agent}"
            artifacts_added += 1

        # Also add artifacts from any nested results (recursive case)
        for nested_result in nested_output.results:
            for artifact in nested_result.response_artifacts:
                new_artifact = parent_task.artifacts.add()
                new_artifact.CopyFrom(artifact)

                # Try to extract the source agent from the artifact name or description
                # The artifact name often contains the agent name
                original_name = artifact.name
                if "_response" in original_name:
                    # Extract agent name from pattern "AgentName_response"
                    extracted_agent = original_name.replace("_response", "")
                    new_artifact.name = f"{extracted_agent}_response"
                    new_artifact.description = f"Response from {extracted_agent}"
                else:
                    # Fallback: use the context or leave as-is but note it's nested
                    new_artifact.name = f"nested_{original_name}"
                    new_artifact.description = f"Nested response: {artifact.description}"

                artifacts_added += 1

        if artifacts_added > 0:
            logger.info(
                "Successfully aggregated nested artifacts",
                structured_data={
                    "parent_task_id": parent_task_id,
                    "source_agent": source_agent,
                    "artifacts_added": artifacts_added,
                    "total_parent_artifacts": len(parent_task.artifacts),
                },
            )
        else:
            logger.debug(
                "No artifacts to aggregate from nested output",
                structured_data={"parent_task_id": parent_task_id, "source_agent": source_agent},
            )

    except Exception as e:
        logger.error(
            "Failed to aggregate nested artifacts",
            structured_data={"parent_task_id": parent_task_id, "source_agent": source_agent, "error": str(e)},
        )
        # Don't raise - artifact aggregation failure shouldn't break execution
