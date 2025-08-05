"""
Example demonstrations of the modular prompt composition system.

This module provides concrete examples showing how persona + modules → final prompts
for different scenarios and agent configurations.
"""

from .composition_engine import PromptCompositionEngine, CompositionContext, CompositionStrategy
from ..proto.mantis.v1.mantis_persona_pb2 import (
    MantisAgentCard,
    PersonaCharacteristics,
    CompetencyScores,
    DomainExpertise,
    RoleAdaptation,
    RolePreference,
)
from ..proto.mantis.v1.mantis_core_pb2 import SimulationInput, AgentSpec
from ..proto.a2a_pb2 import AgentCard


def create_example_strategic_leader() -> MantisAgentCard:
    """Create an example strategic leader agent card for demonstrations."""
    # Create base agent card
    base_card = AgentCard()
    base_card.name = "Marcus Strategy"
    base_card.description = (
        "Experienced strategic leader with expertise in organizational transformation and long-term planning"
    )

    # Create persona characteristics
    characteristics = PersonaCharacteristics()
    characteristics.core_principles.extend(
        [
            "Think systemically about interconnected challenges",
            "Balance short-term execution with long-term vision",
            "Empower teams through clear direction and autonomy",
            "Make decisions based on data and stakeholder impact",
        ]
    )
    characteristics.decision_framework = "Systematic analysis of stakeholder impact, resource requirements, and strategic alignment before making major decisions"
    characteristics.communication_style = (
        "Direct but collaborative, emphasizing clarity and inspiring confidence in the vision"
    )
    characteristics.thinking_patterns.extend(
        [
            "Systems thinking - seeing connections and ripple effects",
            "Strategic patience - willing to invest time for better outcomes",
        ]
    )
    characteristics.characteristic_phrases.extend(
        ["Let's think about the second and third-order effects", "What does success look like in 18 months?"]
    )
    characteristics.original_content = "Strategic leader focused on transformation..."

    # Create competency scores
    competencies = CompetencyScores()
    competencies.competency_scores["strategic planning and long-term vision"] = 0.95
    competencies.competency_scores["team leadership and inspiring others"] = 0.85
    competencies.competency_scores["decisive decision making under pressure"] = 0.8
    competencies.competency_scores["stakeholder relationship management"] = 0.9
    competencies.competency_scores["analytical thinking and logical reasoning"] = 0.75

    # Role adaptation
    role_adaptation = RoleAdaptation()
    role_adaptation.leader_score = 0.9
    role_adaptation.follower_score = 0.4
    role_adaptation.narrator_score = 0.6
    role_adaptation.preferred_role = RolePreference.ROLE_PREFERENCE_LEADER
    role_adaptation.role_flexibility = 0.7
    competencies.role_adaptation.CopyFrom(role_adaptation)

    # Domain expertise
    expertise = DomainExpertise()
    expertise.primary_domains.extend(["Strategic Planning", "Organizational Transformation", "Leadership Development"])
    expertise.secondary_domains.extend(["Change Management", "Business Strategy"])
    expertise.methodologies.extend(["Systems Thinking", "Design Thinking", "Agile Transformation"])

    # Assemble MantisAgentCard
    mantis_card = MantisAgentCard()
    mantis_card.agent_card.CopyFrom(base_card)
    mantis_card.persona_characteristics.CopyFrom(characteristics)
    mantis_card.competency_scores.CopyFrom(competencies)
    mantis_card.domain_expertise.CopyFrom(expertise)
    mantis_card.persona_title = "Strategic Transformation Leader"

    return mantis_card


def create_example_technical_specialist() -> MantisAgentCard:
    """Create an example technical specialist agent card."""
    # Create base agent card
    base_card = AgentCard()
    base_card.name = "Dr. Sarah Chen"
    base_card.description = "Senior data scientist with expertise in machine learning and statistical analysis"

    # Create persona characteristics
    characteristics = PersonaCharacteristics()
    characteristics.core_principles.extend(
        [
            "Let the data guide decisions, not assumptions",
            "Rigorous methodology produces reliable results",
            "Complex problems require systematic decomposition",
        ]
    )
    characteristics.decision_framework = "Evidence-based analysis with statistical validation and peer review"
    characteristics.communication_style = "Precise and methodical, focused on accuracy and reproducibility"
    characteristics.thinking_patterns.extend(
        ["Analytical decomposition of complex problems", "Hypothesis-driven experimentation"]
    )
    characteristics.characteristic_phrases.extend(
        ["What does the data actually tell us?", "Let's validate that assumption with a proper test"]
    )

    # Create competency scores
    competencies = CompetencyScores()
    competencies.competency_scores["analytical thinking and logical reasoning"] = 0.95
    competencies.competency_scores["domain expertise and technical knowledge"] = 0.9
    competencies.competency_scores["decisive decision making under pressure"] = 0.6
    competencies.competency_scores["clear and persuasive communication"] = 0.7
    competencies.competency_scores["team leadership and inspiring others"] = 0.5

    # Role adaptation - prefers follower/specialist role
    role_adaptation = RoleAdaptation()
    role_adaptation.leader_score = 0.4
    role_adaptation.follower_score = 0.9
    role_adaptation.narrator_score = 0.7
    role_adaptation.preferred_role = RolePreference.ROLE_PREFERENCE_FOLLOWER
    role_adaptation.role_flexibility = 0.6
    competencies.role_adaptation.CopyFrom(role_adaptation)

    # Domain expertise
    expertise = DomainExpertise()
    expertise.primary_domains.extend(["Machine Learning", "Statistical Analysis", "Data Science"])
    expertise.secondary_domains.extend(["Python Programming", "Data Visualization"])
    expertise.methodologies.extend(["Scientific Method", "A/B Testing", "Statistical Modeling"])

    # Assemble MantisAgentCard
    mantis_card = MantisAgentCard()
    mantis_card.agent_card.CopyFrom(base_card)
    mantis_card.persona_characteristics.CopyFrom(characteristics)
    mantis_card.competency_scores.CopyFrom(competencies)
    mantis_card.domain_expertise.CopyFrom(expertise)
    mantis_card.persona_title = "Senior Data Scientist"

    return mantis_card


def create_example_simulation_input(query: str, context: str = "") -> SimulationInput:
    """Create an example simulation input for demonstrations."""
    sim_input = SimulationInput()
    sim_input.query = query
    if context:
        sim_input.context = context
    sim_input.max_depth = 3
    return sim_input


def demonstrate_leader_team_building():
    """Demonstrate leader module for team building scenario."""
    print("=" * 80)
    print("DEMONSTRATION: Leader Team Building")
    print("=" * 80)

    # Create strategic leader
    leader_card = create_example_strategic_leader()

    # Create team building scenario
    sim_input = create_example_simulation_input(
        "We need to develop a comprehensive digital transformation strategy for a mid-size manufacturing company. The strategy should cover technology modernization, process optimization, and change management.",
        "The company has 500 employees, legacy systems, and resistance to change. Timeline is 18 months with a $2M budget.",
    )

    # Create context for leader at top level
    context = CompositionContext(
        agent_card=leader_card,
        simulation_input=sim_input,
        agent_spec=AgentSpec(),
        current_depth=0,
        max_depth=3,
        team_size=1,  # Starting solo
        is_leader=True,
        requires_delegation=True,
    )

    # Generate prompt
    engine = PromptCompositionEngine()
    prompt = engine.compose_prompt(context, CompositionStrategy.LAYERED)

    print("SCENARIO: Strategic leader needs to build team for digital transformation")
    print("CONTEXT: Top-level (depth 0/3), solo start, delegation expected")
    print("\nGENERATED PROMPT:")
    print("-" * 40)
    print(prompt)
    print("\n")


def demonstrate_specialist_execution():
    """Demonstrate specialist in execution role."""
    print("=" * 80)
    print("DEMONSTRATION: Technical Specialist Execution")
    print("=" * 80)

    # Create technical specialist
    specialist_card = create_example_technical_specialist()

    # Create analysis task
    sim_input = create_example_simulation_input(
        "Analyze the customer churn data to identify the top 3 factors driving customer departures and recommend retention strategies.",
        "Dataset includes 50K customers over 2 years with behavioral, demographic, and transaction data.",
    )

    # Create context for specialist as follower
    context = CompositionContext(
        agent_card=specialist_card,
        simulation_input=sim_input,
        agent_spec=AgentSpec(),
        current_depth=1,
        max_depth=3,
        team_size=3,
        is_follower=True,
        team_composition=["Marcus Strategy (Leader)", "Sarah Chen (Data Science)", "Alex Kumar (Product)"],
    )

    # Generate prompt
    engine = PromptCompositionEngine()
    prompt = engine.compose_prompt(context, CompositionStrategy.BLENDED)

    print("SCENARIO: Data scientist executing analysis task as part of team")
    print("CONTEXT: Mid-level (depth 1/3), 3-person team, follower role")
    print("\nGENERATED PROMPT:")
    print("-" * 40)
    print(prompt)
    print("\n")


def demonstrate_composition_strategies():
    """Demonstrate different composition strategies."""
    print("=" * 80)
    print("DEMONSTRATION: Composition Strategy Comparison")
    print("=" * 80)

    leader_card = create_example_strategic_leader()
    sim_input = create_example_simulation_input("Develop a go-to-market strategy for our new AI product.")

    context = CompositionContext(
        agent_card=leader_card, simulation_input=sim_input, agent_spec=AgentSpec(), current_depth=0, is_leader=True
    )

    engine = PromptCompositionEngine()

    print("SAME CONTEXT, DIFFERENT STRATEGIES:")
    print("\n1. LAYERED STRATEGY (sections with clear separators):")
    print("-" * 60)
    layered_prompt = engine.compose_prompt(context, CompositionStrategy.LAYERED)
    print(layered_prompt[:500] + "...\n")

    print("2. BLENDED STRATEGY (seamlessly integrated):")
    print("-" * 60)
    blended_prompt = engine.compose_prompt(context, CompositionStrategy.BLENDED)
    print(blended_prompt[:500] + "...\n")


def demonstrate_context_adaptation():
    """Demonstrate how prompts adapt to different contexts."""
    print("=" * 80)
    print("DEMONSTRATION: Context Adaptation")
    print("=" * 80)

    leader_card = create_example_strategic_leader()
    sim_input = create_example_simulation_input("Review and improve our customer onboarding process.")

    scenarios = [
        ("Top Level Leader", {"current_depth": 0, "is_leader": True, "team_size": 1}),
        ("Mid Level Coordinator", {"current_depth": 1, "is_leader": True, "team_size": 4}),
        ("Near Max Depth", {"current_depth": 2, "is_leader": True, "team_size": 2}),
    ]

    for scenario_name, context_params in scenarios:
        print(f"\nSCENARIO: {scenario_name}")
        print("-" * 40)

        context = CompositionContext(
            agent_card=leader_card, simulation_input=sim_input, agent_spec=AgentSpec(), max_depth=3, **context_params
        )

        # Just show the context module output for brevity
        from .modules.context import ContextModule

        context_module = ContextModule()
        if context_module.is_applicable(context):
            # Update variables
            from .variables import VariableSystem

            var_system = VariableSystem()
            context.variables = var_system.create_variables(context)

            context_content = context_module.generate_content(context)
            context_rendered = var_system.substitute_variables(context_content, context.variables)
            print(context_rendered[:400] + "...")


def run_all_demonstrations():
    """Run all prompt composition demonstrations."""
    demonstrate_leader_team_building()
    demonstrate_specialist_execution()
    demonstrate_composition_strategies()
    demonstrate_context_adaptation()


if __name__ == "__main__":
    run_all_demonstrations()
