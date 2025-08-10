# Mantis: Richly Contextual Orchestration Platform
## Product Requirements Document (PRD)

**Version**: 1.0  
**Date**: 2025-08-08  
**Status**: Active Development  

---

## Executive Summary

Mantis is an advanced orchestration platform that enables richly contextual multi-agent coordination through deep integration with the A2A (Agent-to-Agent) ecosystem. By leveraging native A2A protocols for message exchange, task management, and agent discovery, Mantis transforms complex multi-agent scenarios into structured, observable workflows while maintaining conversation continuity through context threading.

### Key Value Propositions

- **Richly Contextual Orchestration**: Advanced prompt contextualization enables agents to receive precisely tailored instructions based on their role, capabilities, and team dynamics
- **Deep A2A Integration**: Native compatibility with the A2A ecosystem through structured Messages, Artifacts, and TaskState management
- **Real-time Visibility**: StreamResponse integration provides live orchestration monitoring and debugging capabilities
- **Semantic Agent Discovery**: Vector-based agent selection through A2A Registry integration for optimal team formation
- **Context Threading**: A2A context_id propagation ensures conversation continuity across complex multi-agent hierarchies

---

## Business Problem & Solution

### Problem Statement

Organizations struggle with coordinating multiple AI agents effectively due to:

1. **Context Loss**: Agents lose conversational context when transitioning between tasks or team members
2. **Poor Agent Selection**: Static agent assignment without consideration of capabilities, context, or team dynamics
3. **Limited Observability**: Black-box multi-agent interactions with minimal monitoring or debugging capabilities
4. **Protocol Fragmentation**: Incompatible agent communication protocols preventing ecosystem integration
5. **Complex Prompt Management**: Overly complex prompt composition systems that obscure business logic

### Solution Overview

Mantis solves these challenges through:

**Richly Contextual Orchestration**
- Simple yet powerful ContextualPrompt design enabling precise agent instruction customization
- Context threading through A2A context_id propagation maintaining conversation continuity
- AgentInterface encapsulation hiding complexity while preserving functionality

**Deep A2A Ecosystem Integration**
- Native A2A Message/Part/Artifact exchange replacing simple text responses
- Full A2A TaskState lifecycle management with streaming updates
- A2A Registry integration for semantic agent discovery and team formation

**Observable Multi-Agent Coordination**
- Real-time StreamResponse updates providing live orchestration visibility
- Comprehensive TaskStatus tracking with state transitions and error handling
- Rich metadata and execution context preservation

---

## Technical Requirements

### Core Functional Requirements

#### FR-1: Context-Threaded Simulation Execution
- **Description**: Execute individual agent simulations with A2A context threading
- **Input**: SimulationInput with context_id, query, input_artifacts, and agent specifications
- **Output**: SimulationOutput with A2A Message, Artifacts, Task, and TaskState
- **Context Propagation**: parent_context_id → context_id hierarchy for conversation continuity

#### FR-2: Multi-Agent Team Coordination
- **Description**: Coordinate multiple agents through flexible ContextualPrompt assembly
- **Input**: TeamExecutionRequest with base query, team size, formation strategy, and contextual prompts
- **Processing**: Simple template assembly (prefixes + base query + suffixes) creating A2A Messages
- **Output**: TeamExecutionResult with streaming updates, member tasks, messages, and artifacts

#### FR-3: Semantic Agent Discovery
- **Description**: Discover and select optimal agents through A2A Registry vector search
- **Capabilities**: Semantic queries, similarity thresholds, capability-based filtering
- **Integration**: AgentSearchCriteria → RegistryAgentCard → AgentInterface encapsulation
- **Team Formation**: RANDOM and HOMOGENEOUS selection strategies

#### FR-4: Real-time Orchestration Monitoring
- **Description**: Provide live visibility into multi-agent execution through streaming
- **Components**: StreamResponse events, TaskStatusUpdateEvent notifications
- **State Tracking**: Complete A2A TaskState lifecycle (SUBMITTED → WORKING → COMPLETED/FAILED)
- **Debugging**: Rich error information with ErrorType categorization and structured details

### Non-Functional Requirements

#### NFR-1: Performance & Scalability
- **Response Time**: < 100ms for single agent execution setup
- **Team Coordination**: < 500ms for team formation up to 10 agents
- **Concurrent Sessions**: Support 1000+ simultaneous contextual executions
- **Context Threading**: Maintain performance with context hierarchies up to 5 levels deep

#### NFR-2: Reliability & Error Handling
- **Availability**: 99.9% uptime for core orchestration services
- **Error Recovery**: Graceful degradation with detailed ErrorInfo responses
- **TaskState Management**: Comprehensive state tracking preventing lost executions
- **Context Integrity**: Guaranteed context_id propagation across all operations

#### NFR-3: A2A Ecosystem Compatibility
- **Protocol Compliance**: Full A2A v1 specification compliance
- **Message Format**: Native A2A Message/Part/Artifact structure support
- **Registry Integration**: Seamless A2A Registry compatibility for agent discovery
- **Extension Support**: A2A AgentExtension and AgentSkill reference capabilities

#### NFR-4: Observability & Monitoring
- **Execution Tracing**: Complete audit trail through context_id threading
- **Real-time Updates**: StreamResponse integration for live orchestration visibility
- **Performance Metrics**: Execution timing, agent utilization, and success rates
- **Error Analytics**: Structured ErrorType categorization and trend analysis

---

## Architecture Overview

### System Architecture Principles

**Context Threading**: A2A context_id propagation ensures conversation continuity across task hierarchies while enabling parallel execution paths.

**Simple Template Assembly**: ContextualPrompt design replaces complex composition engines with straightforward prefix + base + suffix concatenation.

**Direct A2A Message Creation**: ContextualPrompt.message_template generates ready-to-use A2A Messages without intermediate processing.

**Maximal A2A Leverage**: Use A2A infrastructure (Artifacts, TaskState, StreamResponse) instead of rebuilding complexity internally.

**Encapsulated Complexity**: AgentInterface hides rich persona data while preserving essential functionality.

### Core Services

#### MantisService (Primary Orchestration)
- **ProcessSimulationInput**: Context-threaded individual agent execution
- **ProcessTeamExecutionRequest**: Multi-agent coordination with contextual prompting
- **ProcessNarratorRequest**: Team response synthesis and narrative generation

#### A2AService Integration (Native Protocol Support)
- **SendMessage/SendStreamingMessage**: Rich message exchange with Parts and Artifacts
- **GetTask/CancelTask**: Task lifecycle management with comprehensive state tracking
- **TaskSubscription**: Real-time task monitoring through streaming updates

#### A2ARegistryService Integration (Agent Discovery)
- **SearchAgents**: Semantic agent discovery through vector search capabilities
- **GetAgentCard**: Detailed agent capability and persona information retrieval
- **StoreAgentCard**: Agent registration and metadata management

### Core Entities & Data Model

#### SimulationInput (Context-Threaded Request)
```protobuf
message SimulationInput {
  string context_id = 1;                    // A2A context threading
  string parent_context_id = 2;             // Hierarchy support
  string query = 3;                         // Base query
  repeated a2a.v1.Artifact input_artifacts = 5;  // Structured inputs
  ExecutionStrategy execution_strategy = 10;      // DIRECT or A2A
}
```

#### ContextualPrompt (Flexible Template Assembly)
```protobuf
message ContextualPrompt {
  string agent_name = 1;                    // Target agent identification
  string context_content = 2;               // Context for customization
  int32 priority = 3;                       // Ordering within groups
  a2a.v1.Message message_template = 4;     // Ready-to-use A2A Message
}
```

#### TeamExecutionRequest (Multi-Agent Coordination)
```protobuf
message TeamExecutionRequest {
  SimulationInput simulation_input = 1;        // Base context and query
  int32 team_size = 2;                         // Team member count
  TeamFormationStrategy formation_strategy = 3; // RANDOM or HOMOGENEOUS
  repeated ContextualPrompt prefixes = 6;       // Pre-query context
  repeated ContextualPrompt suffixes = 7;       // Post-query context
}
```

#### AgentInterface (Encapsulated Complexity)
```protobuf
message AgentInterface {
  string agent_id = 1;                      // Unique identification
  string capabilities_summary = 4;          // Simplified capabilities
  string persona_summary = 5;               // Essential personality traits
  string role_preference = 6;               // Preferred team role
  bool available = 7;                       // Availability status
  optional a2a.v1.AgentCard agent_card = 8; // Full A2A card reference
}
```

#### SimulationOutput (Rich A2A Results)
```protobuf
message SimulationOutput {
  string context_id = 1;                    // Context continuity
  a2a.v1.Message response_message = 4;     // Rich structured response
  repeated a2a.v1.Artifact response_artifacts = 5; // Output data
  a2a.v1.Task simulation_task = 6;         // Execution tracking
  a2a.v1.TaskState final_state = 7;        // Completion status
}
```

### Integration Patterns

#### 1. Context-Threaded Simulation Flow
```
SimulationInput[context_id] → ContextualExecution → SimulationOutput[Message + Artifacts]
```
- Client submits SimulationInput with context_id and structured Artifacts
- System processes through ContextualExecution with A2A context threading  
- Returns SimulationOutput with rich A2A Message containing Parts and Artifacts

#### 2. Simple Contextual Team Flow
```
base_query + ContextualPrompts[] → A2A Messages → TeamExecutionResult[streaming]
```
- Base query shared across team members
- Individual ContextualPrompts create ready-to-use A2A Messages
- Real-time StreamResponse provides live coordination visibility

#### 3. Template Assembly Pattern
```
prefix_context + agent_base_prompt + postfix_context = contextualized_a2a_message
```
- Simple concatenation replaces complex composition strategies
- Context variables stored as A2A Artifacts (not custom metadata)
- Direct A2A Message creation without intermediate processing

#### 4. Context Propagation Pattern
```
context_id → parent_context_id → task_hierarchy → conversation_continuity
```
- A2A context_id threading maintains conversation state
- Hierarchical context relationships enable parallel execution paths
- Full conversation continuity across multi-level agent interactions

---

## Implementation Roadmap

### Phase 1: Core A2A Integration (MVP)
**Duration**: 4-6 weeks  
**Deliverables**:
- Native A2A Message/Part/Artifact support in SimulationOutput
- A2A TaskState integration replacing boolean success flags
- Basic ContextualPrompt template assembly
- Context threading through context_id propagation

**Success Criteria**:
- A2A Message creation from ContextualPrompt templates
- TaskState lifecycle tracking (SUBMITTED → WORKING → COMPLETED)
- Context propagation across parent-child relationships
- Basic agent execution with A2A protocol compliance

### Phase 2: Multi-Agent Coordination 
**Duration**: 6-8 weeks  
**Deliverables**:
- TeamExecutionRequest with flexible ContextualPrompt design
- Real-time StreamResponse integration for live monitoring
- Team formation strategies (RANDOM, HOMOGENEOUS)
- AgentInterface encapsulation with persona summary

**Success Criteria**:
- Multi-agent team coordination through simple template assembly
- Real-time orchestration visibility through StreamResponse events
- Agent selection based on capabilities and availability
- Context-aware prompt customization for team members

### Phase 3: Semantic Agent Discovery
**Duration**: 4-5 weeks  
**Deliverables**:
- A2A Registry integration for agent discovery
- Vector-based semantic search capabilities
- AgentSearchCriteria with similarity thresholds
- Enhanced team formation through capability matching

**Success Criteria**:
- Semantic agent queries with vector similarity search
- Optimal team formation based on capability analysis
- Registry integration for dynamic agent pool management
- Enhanced context matching through semantic understanding

### Phase 4: Advanced Orchestration Features
**Duration**: 6-8 weeks  
**Deliverables**:
- Advanced error handling with structured ErrorInfo
- Performance optimization for concurrent executions
- Rich metadata preservation and analysis
- Advanced monitoring and analytics dashboards

**Success Criteria**:
- < 100ms single agent execution setup
- 1000+ concurrent contextual executions
- Comprehensive error categorization and recovery
- Production-ready monitoring and observability

---

## Success Metrics

### Technical Performance Metrics
- **Execution Latency**: Average time from SimulationInput to first TaskStatusUpdate < 100ms
- **Team Formation Speed**: Average team assembly time for 5-agent teams < 500ms  
- **Context Propagation Accuracy**: 99.9% successful context_id threading across hierarchies
- **A2A Protocol Compliance**: 100% compatibility with A2A v1 specification

### Business Value Metrics
- **Agent Utilization Efficiency**: Improved agent selection accuracy through semantic discovery
- **Orchestration Success Rate**: > 95% successful multi-agent coordination completion
- **Context Preservation**: Elimination of context loss incidents in multi-turn conversations
- **Developer Experience**: Reduced prompt engineering complexity through ContextualPrompt simplification

### Operational Excellence Metrics  
- **System Availability**: 99.9% uptime for core orchestration services
- **Error Recovery Rate**: < 30 second average recovery time from TaskState failures
- **Resource Efficiency**: Linear scaling performance up to 10-agent team sizes
- **Monitoring Coverage**: 100% execution visibility through StreamResponse integration

---

## Risk Analysis & Mitigation

### Technical Risks

**Risk**: A2A Protocol Evolution
- **Impact**: Medium - Protocol changes could require significant updates
- **Mitigation**: Maintain compatibility layers and version management strategy

**Risk**: Context Threading Performance
- **Impact**: High - Deep context hierarchies could impact response times
- **Mitigation**: Implement context depth limits and performance monitoring

**Risk**: Agent Discovery Scaling  
- **Impact**: Medium - Large agent registries might slow semantic search
- **Mitigation**: Implement caching strategies and search optimization

### Business Risks

**Risk**: Complex Migration Path
- **Impact**: Medium - Existing prompt composition users need migration support
- **Mitigation**: Maintain deprecated services with clear migration documentation

**Risk**: A2A Ecosystem Adoption
- **Impact**: Low - Limited A2A agent availability could reduce platform value
- **Mitigation**: Support both native A2A and adapter patterns for existing agents

---

## Conclusion

Mantis represents a significant evolution in multi-agent orchestration, combining the simplicity of template-based prompt assembly with the power of native A2A ecosystem integration. By focusing on context threading, semantic agent discovery, and real-time orchestration visibility, Mantis enables organizations to build sophisticated multi-agent workflows that maintain conversation continuity while providing comprehensive observability.

The platform's emphasis on "richly contextual orchestration" ensures that each agent receives precisely the context needed for optimal performance, while deep A2A integration provides the foundation for ecosystem-wide compatibility and advanced coordination capabilities.

Through its phased implementation approach and comprehensive success metrics, Mantis is positioned to become the definitive platform for sophisticated multi-agent coordination in enterprise environments.