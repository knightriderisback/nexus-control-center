from orchestrator.agents import get_agent_list, get_agent_by_id

def test_agent_swarm_registry():
    agents = get_agent_list()
    assert len(agents) == 13
    agent_ids = [a.id for a in agents]
    assert "agent-security" in agent_ids
    assert "agent-dev" in agent_ids
    assert "agent-qa" in agent_ids
    assert "agent-infra" in agent_ids
    assert "agent-cost" in agent_ids

def test_agent_lookup():
    agent = get_agent_by_id("agent-security")
    assert agent is not None
    assert agent.role == "Secret Leak Auditor & AST Vulnerability Scanner"
    assert "secret_detector" in agent.allowed_tools
