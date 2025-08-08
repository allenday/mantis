"""
Simplified orchestrator demonstrating ContextualPrompt template assembly.

This showcases the new flexible prompt architecture without complex proto dependencies.
"""

from typing import Optional, Dict, Any
import asyncio
from .contextual_prompt import create_simulation_prompt, ContextualPromptBuilder
from ..proto.mantis.v1 import mantis_persona_pb2
from ..config import DEFAULT_MODEL


class SimpleOrchestrator:
    """Simplified orchestrator for demonstrating ContextualPrompt template assembly."""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self._initialize_basic_tools()
    
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


if __name__ == "__main__":
    asyncio.run(demo_contextual_prompt_assembly())