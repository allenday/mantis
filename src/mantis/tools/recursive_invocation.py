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

if TYPE_CHECKING:
    from ..core.orchestrator import SimulationOrchestrator

logger = get_structured_logger(__name__)


async def invoke_agent_by_name(
    agent_name: str,
    query: str,
    orchestrator: "SimulationOrchestrator",
    context: Optional[str] = None,
    max_depth: int = 1
) -> str:
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
        Agent's response text
        
    Raises:
        ValueError: If agent not found in registry
        Exception: If execution fails
    """
    agent_ctx = current_agent_context.get({})
    invoking_agent = agent_ctx.get('agent_name', 'unknown')
    task_id = agent_ctx.get('task_id', 'unknown')
    context_id = agent_ctx.get('context_id', 'unknown')
    
    # Validate agent exists in registry
    await _validate_agent_exists(agent_name)
    
    logger.info("Invoking agent through recursive simulation", structured_data={
        "invoking_agent": invoking_agent,
        "target_agent": agent_name,
        "task_id": task_id,
        "context_id": context_id,
        "max_depth": max_depth
    })
    
    try:
        # Create recursive SimulationInput
        from ..proto.mantis.v1 import mantis_core_pb2
        
        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.context_id = f"{context_id}-recursive-{agent_name.lower().replace(' ', '-')}"
        simulation_input.parent_context_id = context_id
        simulation_input.query = f"""You are {agent_name}. Please provide your perspective on the following:

{query}

{f"Additional context: {context}" if context else ""}

Please respond as {agent_name} would, drawing on your expertise and perspective. Keep your response focused and authentic to your role."""
        
        simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
        simulation_input.max_depth = max_depth
        
        # Execute recursive simulation
        nested_output = await orchestrator.execute_simulation(simulation_input)
        
        # Extract response text
        response_text = "No response generated"
        if nested_output.response_message and nested_output.response_message.content:
            response_text = nested_output.response_message.content[0].text
        
        # Aggregate nested artifacts to parent task
        await _aggregate_nested_output(
            parent_task_id=task_id,
            nested_output=nested_output,
            orchestrator=orchestrator,
            source_agent=agent_name
        )
        
        logger.info("Successfully completed recursive agent invocation", structured_data={
            "invoking_agent": invoking_agent,
            "target_agent": agent_name,
            "response_length": len(response_text),
            "artifacts_in_nested": len(nested_output.response_artifacts)
        })
        
        return response_text
        
    except Exception as e:
        logger.error("Recursive agent invocation failed", structured_data={
            "invoking_agent": invoking_agent,
            "target_agent": agent_name,
            "error": str(e),
            "task_id": task_id
        })
        raise


async def invoke_multiple_agents(
    agent_names: list,
    query_template: str,
    orchestrator: "SimulationOrchestrator",
    individual_contexts: Optional[list] = None,
    max_depth: int = 1
) -> Dict[str, str]:
    """
    Invoke multiple agents in parallel with proper artifact aggregation.
    
    Args:
        agent_names: List of agent names to invoke
        query_template: Base query for all agents
        orchestrator: Orchestrator instance
        individual_contexts: Optional per-agent contexts
        max_depth: Maximum recursion depth
        
    Returns:
        Dictionary mapping agent names to responses
    """
    agent_ctx = current_agent_context.get({})
    invoking_agent = agent_ctx.get('agent_name', 'unknown')
    
    logger.info("Invoking multiple agents in parallel", structured_data={
        "invoking_agent": invoking_agent,
        "target_agents": agent_names,
        "agent_count": len(agent_names)
    })
    
    # Validate all agents exist
    for agent_name in agent_names:
        await _validate_agent_exists(agent_name)
    
    # Create parallel invocation tasks
    tasks = []
    for i, agent_name in enumerate(agent_names):
        context = individual_contexts[i] if individual_contexts and i < len(individual_contexts) else None
        task = invoke_agent_by_name(
            agent_name=agent_name,
            query=query_template,
            orchestrator=orchestrator,
            context=context,
            max_depth=max_depth
        )
        tasks.append((agent_name, task))
    
    # Execute in parallel
    try:
        responses = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        results = {}
        for (agent_name, _), response in zip(tasks, responses):
            if isinstance(response, Exception):
                results[agent_name] = f"Error: {str(response)}"
                logger.error(f"Agent {agent_name} failed", structured_data={"error": str(response)})
            else:
                results[agent_name] = response
        
        successful_count = len([r for r in results.values() if not r.startswith("Error:")])
        logger.info("Multiple agent invocation completed", structured_data={
            "invoking_agent": invoking_agent,
            "successful_invocations": successful_count,
            "total_agents": len(agent_names)
        })
        
        return results
        
    except Exception as e:
        logger.error("Multiple agent invocation failed", structured_data={
            "invoking_agent": invoking_agent,
            "target_agents": agent_names,
            "error": str(e)
        })
        raise


async def _validate_agent_exists(agent_name: str) -> None:
    """Validate that agent exists in registry."""
    from ..tools.agent_registry import list_all_agents
    from ..agent import AgentInterface
    
    try:
        all_agents = await list_all_agents()
        if not all_agents:
            raise ValueError("No agents available in registry")
        
        # Check if agent exists by name or ID
        available_agents = []
        for agent_card in all_agents:
            agent_interface = AgentInterface(agent_card)
            available_agents.extend([agent_interface.agent_id, agent_interface.name])
        
        if agent_name not in available_agents:
            unique_names = list(set(available_agents))[:10]
            available_list = ', '.join(unique_names)
            if len(unique_names) >= 10:
                available_list += "..."
            
            raise ValueError(
                f"Agent '{agent_name}' not found in registry. "
                f"Available agents: {available_list}"
            )
            
    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        raise ValueError(f"Error validating agent registry: {str(e)}")


async def _aggregate_nested_output(
    parent_task_id: str,
    nested_output: "mantis_core_pb2.SimulationOutput",
    orchestrator: "SimulationOrchestrator",
    source_agent: str
) -> None:
    """
    Aggregate artifacts from nested SimulationOutput to parent task.
    
    This ensures artifacts from recursive agent calls are visible in final output.
    """
    try:
        parent_task = orchestrator.get_task_by_id(parent_task_id)
        if not parent_task:
            logger.warning("Cannot aggregate artifacts - parent task not found", 
                         structured_data={
                             "parent_task_id": parent_task_id,
                             "source_agent": source_agent
                         })
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
            logger.info("Successfully aggregated nested artifacts", structured_data={
                "parent_task_id": parent_task_id,
                "source_agent": source_agent,
                "artifacts_added": artifacts_added,
                "total_parent_artifacts": len(parent_task.artifacts)
            })
        else:
            logger.debug("No artifacts to aggregate from nested output", 
                        structured_data={
                            "parent_task_id": parent_task_id,
                            "source_agent": source_agent
                        })
            
    except Exception as e:
        logger.error("Failed to aggregate nested artifacts", structured_data={
            "parent_task_id": parent_task_id,
            "source_agent": source_agent,
            "error": str(e)
        })
        # Don't raise - artifact aggregation failure shouldn't break execution