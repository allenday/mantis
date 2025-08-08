"""
Orchestrator with A2A TaskState integration and ContextualPrompt template assembly.

Integrates A2A Task lifecycle management with flexible prompt architecture.
"""

from typing import Optional, Dict, Any, List
import asyncio
import uuid
from google.protobuf import timestamp_pb2
from .contextual_prompt import create_simulation_prompt, ContextualPromptBuilder
from ..proto.mantis.v1 import mantis_persona_pb2
from ..proto import a2a_pb2
from ..config import DEFAULT_MODEL
from ..observability.logger import get_structured_logger

logger = get_structured_logger(__name__)


class SimulationOutput:
    """
    Wraps simulation results in native A2A Messages and Artifacts for clean protocol compatibility.
    
    Uses A2A protobuf types exclusively to avoid serialization overhead and ensure 
    wire protocol compatibility.
    """
    
    def __init__(self, task: a2a_pb2.Task) -> None:
        """Initialize with completed A2A Task."""
        if not isinstance(task, a2a_pb2.Task):
            raise TypeError(f"Expected a2a_pb2.Task, got {type(task)}")
        
        if task.status.state != a2a_pb2.TASK_STATE_COMPLETED:
            logger.warning(
                "Creating SimulationOutput from incomplete task",
                structured_data={
                    "task_id": task.id,
                    "task_state": task.status.state,
                    "expected_state": a2a_pb2.TASK_STATE_COMPLETED
                }
            )
        
        self._task = task
        logger.debug(
            "Created SimulationOutput", 
            structured_data={
                "task_id": task.id,
                "context_id": task.context_id,
                "message_count": len(task.history),
                "artifact_count": len(task.artifacts)
            }
        )
    
    @property
    def task(self) -> a2a_pb2.Task:
        """Get the underlying A2A Task."""
        return self._task
    
    @property
    def messages(self) -> List[a2a_pb2.Message]:
        """Get all A2A Messages from task history."""
        return list(self._task.history)
    
    @property
    def artifacts(self) -> List[a2a_pb2.Artifact]:
        """Get all A2A Artifacts from task."""
        return list(self._task.artifacts)
    
    def get_user_messages(self) -> List[a2a_pb2.Message]:
        """Get only USER role messages."""
        user_messages = [msg for msg in self._task.history if msg.role == a2a_pb2.ROLE_USER]
        logger.debug("Retrieved user messages", structured_data={"count": len(user_messages), "task_id": self._task.id})
        return user_messages
    
    def get_agent_messages(self) -> List[a2a_pb2.Message]:
        """Get only AGENT role messages."""
        agent_messages = [msg for msg in self._task.history if msg.role == a2a_pb2.ROLE_AGENT]
        logger.debug("Retrieved agent messages", structured_data={"count": len(agent_messages), "task_id": self._task.id})
        return agent_messages
    
    def get_final_response(self) -> Optional[a2a_pb2.Message]:
        """Get the final non-status agent response message."""
        agent_messages = self.get_agent_messages()
        
        # Find last non-status message
        for msg in reversed(agent_messages):
            if msg.content and len(msg.content) > 0:
                content_text = msg.content[0].text
                if not content_text.startswith("[STATUS UPDATE]"):
                    logger.debug("Found final response message", structured_data={"message_id": msg.message_id, "task_id": self._task.id})
                    return msg
        
        logger.warning("No final response message found", structured_data={"task_id": self._task.id})
        return None
    
    def create_artifact_from_response(
        self, 
        name: str, 
        description: str, 
        response_message: Optional[a2a_pb2.Message] = None
    ) -> a2a_pb2.Artifact:
        """Create an A2A Artifact from a response message."""
        if response_message is None:
            response_message = self.get_final_response()
            if response_message is None:
                raise ValueError("No response message provided and no final response found")
        
        # Create artifact
        artifact = a2a_pb2.Artifact()
        artifact.artifact_id = f"artifact-{uuid.uuid4().hex[:12]}"
        artifact.name = name
        artifact.description = description
        
        # Copy content from message to artifact
        for part in response_message.content:
            artifact.parts.append(part)
        
        # Add to task artifacts
        self._task.artifacts.append(artifact)
        
        logger.info(
            "Created artifact from response",
            structured_data={
                "artifact_id": artifact.artifact_id,
                "name": name,
                "task_id": self._task.id,
                "parts_count": len(artifact.parts)
            }
        )
        
        return artifact
    
    def to_a2a_message(self, role: Optional[int] = None) -> a2a_pb2.Message:
        """Convert the entire simulation output to a single A2A Message."""
        if role is None:
            role = a2a_pb2.ROLE_AGENT
        
        # Create summary message
        summary_msg = a2a_pb2.Message()
        summary_msg.message_id = f"summary-{uuid.uuid4().hex[:12]}"
        summary_msg.context_id = self._task.context_id
        summary_msg.task_id = self._task.id
        summary_msg.role = role  # type: ignore[assignment]
        
        # Create summary text
        final_response = self.get_final_response()
        if final_response and final_response.content:
            # Use final response as main content
            for part in final_response.content:
                summary_msg.content.append(part)
        else:
            # Fallback: create summary of all messages
            text_part = a2a_pb2.Part()
            text_part.text = f"Simulation completed for task {self._task.id} with {len(self.messages)} messages"
            summary_msg.content.append(text_part)
        
        logger.debug(
            "Converted simulation output to A2A message",
            structured_data={
                "message_id": summary_msg.message_id,
                "task_id": self._task.id,
                "content_parts": len(summary_msg.content)
            }
        )
        
        return summary_msg


class SimpleOrchestrator:
    """Orchestrator with A2A TaskState integration and ContextualPrompt template assembly."""
    
    def __init__(self) -> None:
        self.tools: Dict[str, Any] = {}
        self.active_tasks: Dict[str, a2a_pb2.Task] = {}  # Track active tasks by ID
        self._initialize_basic_tools()
        logger.info("Initialized SimpleOrchestrator", structured_data={"tools_count": len(self.tools)})
    
    async def execute_with_contextual_prompt(
        self,
        query: str,
        agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        custom_prefixes: Optional[list] = None,
        custom_suffixes: Optional[list] = None
    ) -> str:
        """
        Execute a query using ContextualPrompt template assembly.
        
        This demonstrates the flexible template system where prompts are assembled
        from modular components rather than fixed schemas.
        """
        
        # Create contextual prompt using template assembly
        if custom_prefixes or custom_suffixes:
            # Use custom template assembly
            builder = ContextualPromptBuilder()
            
            # Add custom prefixes
            if custom_prefixes:
                for prefix in custom_prefixes:
                    builder.add_prefix(prefix)
            else:
                builder.add_prefix("You are a specialized AI agent participating in a collaborative simulation.")
            
            # Core content
            builder.set_core_content(f"## Task\n{query}")
            
            # Add agent context
            if agent_card:
                builder.with_agent(agent_card)
            
            # Add custom suffixes
            if custom_suffixes:
                for suffix in custom_suffixes:
                    builder.add_suffix(suffix)
            else:
                builder.add_suffix("Provide a detailed, thoughtful response leveraging your expertise.")
            
            contextual_prompt = builder.build()
        else:
            # Use standard template
            contextual_prompt = create_simulation_prompt(
                query=query,
                agent_card=agent_card,
                context_id=context_id,
                task_id=task_id
            )
        
        # Assemble the final prompt
        assembled_prompt = contextual_prompt.assemble()
        
        # Execute using LLM
        result = await self._execute_with_llm(assembled_prompt, query)
        
        return result
    
    async def _execute_with_llm(self, prompt: str, query: str) -> str:
        """Execute the assembled prompt using the LLM with tools."""
        try:
            from ..llm.structured_extractor import StructuredExtractor
            
            extractor = StructuredExtractor()
            
            # Use the contextual prompt as system prompt and query as user input
            result = await extractor.extract_text_response_with_tools(
                prompt=prompt,
                query=query,
                model=DEFAULT_MODEL,
                tools=self.tools
            )
            
            return result
            
        except ImportError:
            # Fallback if structured extractor is not available
            return f"[Contextual Prompt Template]\n\n{prompt}\n\n[Query]\n{query}\n\n[Response]\nContextual template assembly working! Tools: {list(self.tools.keys())}"
    
    def _initialize_basic_tools(self):
        """Initialize a basic set of tools for demonstration."""
        try:
            # Import available tools
            from ..tools.web_fetch import web_fetch_url
            from ..tools.web_search import web_search
            from ..tools.divination import get_random_number, draw_tarot_card
            
            self.tools.update({
                "web_fetch_url": web_fetch_url,
                "web_search": web_search,
                "get_random_number": get_random_number,
                "draw_tarot_card": draw_tarot_card,
            })
            
        except ImportError:
            # Tools not available, continue with empty tool set
            pass
    
    def get_available_tools(self) -> list:
        """Get list of available tool names."""
        return list(self.tools.keys())
    
    # ===== A2A TaskState Integration Methods =====
    
    def create_task_from_query(
        self, 
        query: str, 
        context_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> a2a_pb2.Task:
        """Create an A2A Task from a user query with SUBMITTED state."""
        
        # Generate IDs if not provided
        if not task_id:
            task_id = f"task-{uuid.uuid4().hex[:12]}"
        if not context_id:
            context_id = f"context-{uuid.uuid4().hex[:8]}"
        
        # Create initial task status 
        task_status = a2a_pb2.TaskStatus()
        task_status.state = a2a_pb2.TASK_STATE_SUBMITTED
        
        # Set timestamp
        timestamp = timestamp_pb2.Timestamp()
        timestamp.GetCurrentTime()
        task_status.timestamp.CopyFrom(timestamp)
        
        # Create task
        task = a2a_pb2.Task()
        task.id = task_id
        task.context_id = context_id
        task.status.CopyFrom(task_status)
        
        # Create initial message from query
        initial_message = a2a_pb2.Message()
        initial_message.message_id = f"msg-{uuid.uuid4().hex[:12]}"
        initial_message.context_id = context_id
        initial_message.task_id = task_id
        initial_message.role = a2a_pb2.ROLE_USER
        
        # Add query as text part
        text_part = a2a_pb2.Part()
        text_part.text = query
        initial_message.content.append(text_part)
        
        # Add to task history
        task.history.append(initial_message)
        
        # Track the task
        self.active_tasks[task_id] = task
        
        return task
    
    def update_task_status(
        self, 
        task_id: str, 
        new_state: int, 
        status_message: Optional[str] = None
    ) -> None:
        """Update task status and add status update message."""
        
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.active_tasks[task_id]
        
        # Update task status
        task.status.state = new_state  # type: ignore[assignment]
        
        # Update timestamp
        timestamp = timestamp_pb2.Timestamp()
        timestamp.GetCurrentTime()
        task.status.timestamp.CopyFrom(timestamp)
        
        # Add status update message if provided
        if status_message:
            status_update_msg = a2a_pb2.Message()
            status_update_msg.message_id = f"status-{uuid.uuid4().hex[:12]}"
            status_update_msg.context_id = task.context_id
            status_update_msg.task_id = task_id
            status_update_msg.role = a2a_pb2.ROLE_AGENT
            
            text_part = a2a_pb2.Part()
            text_part.text = f"[STATUS UPDATE] {status_message}"
            status_update_msg.content.append(text_part)
            
            task.history.append(status_update_msg)
    
    def create_a2a_response_message(
        self,
        task_id: str,
        response_text: str,
        role: Optional[int] = None
    ) -> a2a_pb2.Message:
        """Create an A2A Message from a response string."""
        
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.active_tasks[task_id]
        
        # Create response message
        response_message = a2a_pb2.Message()
        response_message.message_id = f"resp-{uuid.uuid4().hex[:12]}"
        response_message.context_id = task.context_id
        response_message.task_id = task_id
        response_message.role = role or a2a_pb2.ROLE_AGENT  # type: ignore[assignment]
        
        # Add response text as part
        text_part = a2a_pb2.Part()
        text_part.text = response_text
        response_message.content.append(text_part)
        
        return response_message
    
    async def execute_task_with_a2a_lifecycle(
        self,
        query: str,
        agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        custom_prefixes: Optional[list] = None,
        custom_suffixes: Optional[list] = None
    ) -> a2a_pb2.Task:
        """
        Execute a task with full A2A lifecycle management.
        
        This method creates an A2A Task, manages its lifecycle through 
        SUBMITTED -> WORKING -> COMPLETED/FAILED states, and returns
        the completed Task with all messages and artifacts.
        """
        
        # Create A2A Task from query
        task = self.create_task_from_query(query, context_id, task_id)
        task_id = task.id  # Use the actual task ID
        
        try:
            # Update status to WORKING
            self.update_task_status(
                task_id, 
                a2a_pb2.TASK_STATE_WORKING, 
                "Task processing started"
            )
            
            # Execute the query using existing contextual prompt logic
            response_text = await self.execute_with_contextual_prompt(
                query=query,
                agent_card=agent_card,
                context_id=task.context_id,
                task_id=task_id,
                custom_prefixes=custom_prefixes,
                custom_suffixes=custom_suffixes
            )
            
            # Create A2A response message
            response_message = self.create_a2a_response_message(
                task_id, 
                response_text
            )
            
            # Add response to task history
            task.history.append(response_message)
            
            # Update status to COMPLETED
            self.update_task_status(
                task_id,
                a2a_pb2.TASK_STATE_COMPLETED,
                "Task completed successfully"
            )
            
            return task
            
        except Exception as e:
            # Update status to FAILED
            error_message = f"Task failed: {str(e)}"
            self.update_task_status(
                task_id,
                a2a_pb2.TASK_STATE_FAILED, 
                error_message
            )
            
            # Add error response message
            error_response = self.create_a2a_response_message(
                task_id,
                f"Error occurred during task execution: {str(e)}"
            )
            task.history.append(error_response)
            
            return task
    
    def get_task_by_id(self, task_id: str) -> Optional[a2a_pb2.Task]:
        """Retrieve a task by its ID."""
        return self.active_tasks.get(task_id)
    
    def get_tasks_by_context(self, context_id: str) -> List[a2a_pb2.Task]:
        """Retrieve all tasks for a given context ID."""
        context_tasks = [
            task for task in self.active_tasks.values() 
            if task.context_id == context_id
        ]
        logger.debug("Retrieved tasks by context", structured_data={"context_id": context_id, "task_count": len(context_tasks)})
        return context_tasks
    
    def create_simulation_output(self, task_id: str) -> SimulationOutput:
        """Create a SimulationOutput from a completed task."""
        if task_id not in self.active_tasks:
            error_msg = f"Task {task_id} not found in active tasks"
            logger.error("Failed to create simulation output", structured_data={"task_id": task_id, "error": error_msg})
            raise ValueError(error_msg)
        
        task = self.active_tasks[task_id]
        
        if task.status.state != a2a_pb2.TASK_STATE_COMPLETED:
            logger.warning(
                "Creating simulation output from incomplete task",
                structured_data={
                    "task_id": task_id,
                    "current_state": task.status.state,
                    "expected_state": a2a_pb2.TASK_STATE_COMPLETED
                }
            )
        
        simulation_output = SimulationOutput(task)
        logger.info(
            "Created simulation output", 
            structured_data={
                "task_id": task_id,
                "message_count": len(simulation_output.messages),
                "artifact_count": len(simulation_output.artifacts)
            }
        )
        
        return simulation_output
    
    async def execute_simulation_with_output(
        self,
        query: str,
        agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        custom_prefixes: Optional[List[str]] = None,
        custom_suffixes: Optional[List[str]] = None
    ) -> SimulationOutput:
        """
        Execute a simulation and return a structured SimulationOutput with native A2A types.
        
        This is the recommended high-level interface for running simulations that need
        structured A2A protocol outputs.
        """
        logger.info(
            "Starting simulation with output",
            structured_data={
                "query_preview": query[:100] + "..." if len(query) > 100 else query,
                "context_id": context_id,
                "task_id": task_id,
                "has_agent_card": agent_card is not None
            }
        )
        
        try:
            # Execute with A2A lifecycle
            completed_task = await self.execute_task_with_a2a_lifecycle(
                query=query,
                agent_card=agent_card,
                context_id=context_id,
                task_id=task_id,
                custom_prefixes=custom_prefixes,
                custom_suffixes=custom_suffixes
            )
            
            # Create structured output
            simulation_output = SimulationOutput(completed_task)
            
            logger.info(
                "Completed simulation with output",
                structured_data={
                    "task_id": completed_task.id,
                    "final_state": completed_task.status.state,
                    "message_count": len(simulation_output.messages),
                    "artifact_count": len(simulation_output.artifacts)
                }
            )
            
            return simulation_output
            
        except Exception as e:
            logger.error(
                "Simulation execution failed",
                structured_data={
                    "query_preview": query[:100] + "..." if len(query) > 100 else query,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            raise


async def demo_contextual_prompt_assembly():
    """Demonstrate the flexible ContextualPrompt template system."""
    
    orchestrator = SimpleOrchestrator()
    
    # Create a sample agent card
    agent_card = mantis_persona_pb2.MantisAgentCard()
    
    # Basic agent info
    basic_agent = agent_card.agent_card
    basic_agent.name = "Strategic Analyst"
    basic_agent.description = "Expert in strategic planning and analysis"
    basic_agent.version = "1.0.0"
    
    # Add persona characteristics
    persona = mantis_persona_pb2.PersonaCharacteristics()
    persona.core_principles.extend([
        "Data-driven decision making",
        "Long-term strategic thinking", 
        "Systems-level analysis"
    ])
    persona.decision_framework = "Analytical and methodical, considering multiple perspectives"
    persona.communication_style = "Clear, structured, and evidence-based"
    agent_card.persona_characteristics.CopyFrom(persona)
    
    # Add domain expertise
    expertise = mantis_persona_pb2.DomainExpertise()
    expertise.primary_domains.extend(["Strategic Planning", "Business Analysis", "Market Research"])
    expertise.methodologies.extend(["SWOT Analysis", "Porter's Five Forces", "Scenario Planning"])
    agent_card.domain_expertise.CopyFrom(expertise)
    
    print("🎯 Demonstrating ContextualPrompt Template Assembly")
    print("=" * 60)
    
    # Example 1: Standard template
    print("\n📋 Example 1: Standard Template Assembly")
    result1 = await orchestrator.execute_with_contextual_prompt(
        query="Analyze the competitive landscape for AI-powered productivity tools",
        agent_card=agent_card,
        context_id="demo-001"
    )
    print("Result:", result1[:200] + "..." if len(result1) > 200 else result1)
    
    # Example 2: Custom template with specific prefixes/suffixes
    print("\n🔧 Example 2: Custom Template Assembly")
    result2 = await orchestrator.execute_with_contextual_prompt(
        query="What are the key trends in remote work technology?",
        agent_card=agent_card,
        custom_prefixes=[
            "You are participating in a strategic foresight exercise.",
            "Focus on emerging trends and their implications for the next 3-5 years."
        ],
        custom_suffixes=[
            "Structure your response with: 1) Current State, 2) Emerging Trends, 3) Strategic Implications",
            "Provide specific examples and actionable insights."
        ]
    )
    print("Result:", result2[:200] + "..." if len(result2) > 200 else result2)
    
    # Example 3: Template with tools
    print(f"\n🛠️  Available Tools: {orchestrator.get_available_tools()}")
    
    print("\n✅ ContextualPrompt template assembly demonstration complete!")


async def demo_a2a_taskstate_integration():
    """Demonstrate A2A TaskState integration with lifecycle management."""
    
    orchestrator = SimpleOrchestrator()
    
    # Create a sample agent card
    agent_card = mantis_persona_pb2.MantisAgentCard()
    
    # Basic agent info
    basic_agent = agent_card.agent_card
    basic_agent.name = "A2A Test Agent"
    basic_agent.description = "Agent for testing A2A Task lifecycle"
    basic_agent.version = "1.0.0"
    
    print("🎯 Demonstrating A2A TaskState Integration")
    print("=" * 60)
    
    # Example 1: Basic A2A task execution with lifecycle
    print("\n📋 Example 1: A2A Task Lifecycle Management")
    task = await orchestrator.execute_task_with_a2a_lifecycle(
        query="What are the key benefits of A2A protocol integration?",
        agent_card=agent_card,
        context_id="a2a-demo-001"
    )
    
    print(f"Task ID: {task.id}")
    print(f"Context ID: {task.context_id}")
    print(f"Final Status: {task.status.state} (COMPLETED={a2a_pb2.TASK_STATE_COMPLETED})")
    print(f"Messages in History: {len(task.history)}")
    
    # Show message details
    for i, msg in enumerate(task.history):
        role_name = "USER" if msg.role == a2a_pb2.ROLE_USER else "AGENT"
        content_preview = msg.content[0].text[:100] + "..." if len(msg.content[0].text) > 100 else msg.content[0].text
        print(f"  Message {i+1} [{role_name}]: {content_preview}")
    
    # Example 2: Context threading - multiple tasks in same context
    print("\n🔗 Example 2: Context Threading")
    context_id = "shared-context-001"
    
    task1 = await orchestrator.execute_task_with_a2a_lifecycle(
        query="Explain task state management",
        context_id=context_id
    )
    
    _task2 = await orchestrator.execute_task_with_a2a_lifecycle(
        query="How does context threading work?",
        context_id=context_id
    )
    
    # Show context threading
    context_tasks = orchestrator.get_tasks_by_context(context_id)
    print(f"Tasks in context '{context_id}': {len(context_tasks)}")
    for task in context_tasks:
        print(f"  - Task {task.id}: Status {task.status.state}")
    
    # Example 3: Task retrieval by ID
    print("\n🔍 Example 3: Task Retrieval")
    retrieved_task = orchestrator.get_task_by_id(task1.id)
    if retrieved_task:
        print(f"Retrieved task {retrieved_task.id} with {len(retrieved_task.history)} messages")
    
    print("\n✅ A2A TaskState integration demonstration complete!")


async def demo_simulation_output():
    """Demonstrate SimulationOutput with native A2A Messages and Artifacts."""
    
    orchestrator = SimpleOrchestrator()
    
    print("🎯 Demonstrating SimulationOutput with A2A Messages/Artifacts")
    print("=" * 60)
    
    # Example 1: Create simulation output with artifacts
    print("\n📋 Example 1: SimulationOutput with Artifact Creation")
    
    simulation_output = await orchestrator.execute_simulation_with_output(
        query="Create a strategic analysis of AI agent coordination protocols",
        context_id="simulation-demo-001"
    )
    
    print(f"Simulation Task ID: {simulation_output.task.id}")
    print(f"Total Messages: {len(simulation_output.messages)}")
    print(f"User Messages: {len(simulation_output.get_user_messages())}")
    print(f"Agent Messages: {len(simulation_output.get_agent_messages())}")
    
    # Create an artifact from the response
    artifact = simulation_output.create_artifact_from_response(
        name="Strategic Analysis Report", 
        description="Comprehensive analysis of AI agent coordination protocols"
    )
    
    print(f"Created Artifact: {artifact.name} (ID: {artifact.artifact_id})")
    print(f"Artifact Parts: {len(artifact.parts)}")
    
    # Example 2: Convert to A2A Message
    print("\n🔄 Example 2: Convert to A2A Message")
    
    a2a_message = simulation_output.to_a2a_message()
    print(f"A2A Message ID: {a2a_message.message_id}")
    print(f"Message Role: {'AGENT' if a2a_message.role == a2a_pb2.ROLE_AGENT else 'USER'}")
    print(f"Content Parts: {len(a2a_message.content)}")
    
    # Show final response extraction
    final_response = simulation_output.get_final_response()
    if final_response:
        content_preview = final_response.content[0].text[:150] + "..." if len(final_response.content[0].text) > 150 else final_response.content[0].text
        print(f"Final Response Preview: {content_preview}")
    
    print("\n✅ SimulationOutput demonstration complete!")


if __name__ == "__main__":
    print("Running ContextualPrompt, A2A TaskState, and SimulationOutput demos...")
    asyncio.run(demo_contextual_prompt_assembly())
    print("\n" + "="*80 + "\n")
    asyncio.run(demo_a2a_taskstate_integration())
    print("\n" + "="*80 + "\n")
    asyncio.run(demo_simulation_output())