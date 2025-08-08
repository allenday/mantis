#!/usr/bin/env python3
"""
Test A2A protocol compliance in MantisService simulation execution.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mantis.core import MantisService
from mantis.proto.mantis.v1 import mantis_core_pb2
from mantis.proto import a2a_pb2


async def test_a2a_protocol_compliance():
    """Test full A2A protocol compliance in simulation execution."""
    print("🧪 Testing A2A Protocol Compliance...")
    
    # Initialize MantisService
    service = MantisService()
    print("✅ MantisService initialized")
    
    # Create SimulationInput with proper A2A context threading
    simulation_input = mantis_core_pb2.SimulationInput()
    simulation_input.context_id = "test-context-123"
    simulation_input.parent_context_id = "parent-context-456"
    simulation_input.query = "Test query for A2A protocol compliance verification"
    simulation_input.context = "Testing context for protocol validation"
    simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_A2A
    
    # Add test input artifacts
    test_artifact = a2a_pb2.Artifact()
    test_artifact.artifact_id = "test-artifact-1"
    test_artifact.name = "test-input.txt"
    test_artifact.description = "Test input data for A2A compliance verification"
    
    # Add a text part to the artifact
    text_part = a2a_pb2.Part()
    text_part.text = "Test input data for A2A compliance"
    test_artifact.parts.append(text_part)
    
    simulation_input.input_artifacts.append(test_artifact)
    
    print(f"📦 Created SimulationInput:")
    print(f"   Context ID: {simulation_input.context_id}")
    print(f"   Parent Context: {simulation_input.parent_context_id}")
    print(f"   Query: {simulation_input.query}")
    print(f"   Execution Strategy: {simulation_input.execution_strategy}")
    print(f"   Input Artifacts: {len(simulation_input.input_artifacts)}")
    
    try:
        # Execute simulation with A2A lifecycle
        result = await service.process_simulation_input(simulation_input)
        
        print(f"\n✅ Simulation completed successfully:")
        print(f"   Context ID: {result.context_id}")
        print(f"   Final State: {result.final_state}")
        print(f"   Response Artifacts: {len(result.response_artifacts)}")
        
        # Verify A2A protocol compliance
        compliance_checks = []
        
        # Check 1: Context ID preserved
        if result.context_id == simulation_input.context_id:
            compliance_checks.append("✅ Context ID preserved")
        else:
            compliance_checks.append("❌ Context ID not preserved")
        
        # Check 2: A2A Task created
        if result.HasField('simulation_task'):
            compliance_checks.append("✅ A2A Task created")
            print(f"   Task ID: {result.simulation_task.id}")
            print(f"   Task Status: {result.simulation_task.status.state}")
        else:
            compliance_checks.append("❌ A2A Task not created")
        
        # Check 3: A2A Message response
        if result.HasField('response_message'):
            compliance_checks.append("✅ A2A Message response created")
            print(f"   Message ID: {result.response_message.message_id}")
            print(f"   Message Role: {result.response_message.role}")
            print(f"   Message Parts: {len(result.response_message.content)}")
        else:
            compliance_checks.append("❌ A2A Message response not created")
        
        # Check 4: TaskState compliance
        valid_states = [
            a2a_pb2.TASK_STATE_COMPLETED,
            a2a_pb2.TASK_STATE_FAILED,
            a2a_pb2.TASK_STATE_WORKING
        ]
        if result.final_state in valid_states:
            compliance_checks.append("✅ Valid A2A TaskState")
        else:
            compliance_checks.append("❌ Invalid A2A TaskState")
        
        print(f"\n🔍 A2A Protocol Compliance Results:")
        for check in compliance_checks:
            print(f"   {check}")
        
        # Overall compliance assessment
        passed_checks = len([c for c in compliance_checks if c.startswith("✅")])
        total_checks = len(compliance_checks)
        
        if passed_checks == total_checks:
            print(f"\n🎉 Full A2A Protocol Compliance Achieved! ({passed_checks}/{total_checks})")
            return True
        else:
            print(f"\n⚠️  Partial A2A Protocol Compliance ({passed_checks}/{total_checks})")
            return False
            
    except Exception as e:
        print(f"\n❌ Simulation failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False


async def test_contextual_execution_status():
    """Test context threading and status retrieval."""
    print("\n🧪 Testing Contextual Execution Status...")
    
    service = MantisService()
    
    # Test context status retrieval
    test_context = "test-context-123"
    status_results = service.get_contextual_execution_status(test_context)
    
    print(f"📊 Context Status Results:")
    print(f"   Context ID: {test_context}")
    print(f"   Results Count: {len(status_results)}")
    
    for i, result in enumerate(status_results):
        print(f"   Task {i+1}: {result.context_id} -> {result.final_state}")
    
    print("✅ Contextual execution status test completed")
    return True


async def main():
    """Run all A2A compliance tests."""
    print("🚀 Starting A2A Protocol Compliance Test Suite...\n")
    
    tests = [
        ("A2A Protocol Compliance", test_a2a_protocol_compliance),
        ("Contextual Execution Status", test_contextual_execution_status),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print(f"\n📋 Final Test Results:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🏁 Test Suite Complete: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All A2A protocol compliance tests PASSED!")
        return 0
    else:
        print("⚠️  Some A2A protocol compliance tests FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)