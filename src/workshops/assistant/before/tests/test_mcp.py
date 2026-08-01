from assistant.agent import Step, run
from assistant.mcp_client import extend_assistant
from assistant.tools import REGISTRY


def _fake_invoker(name, kwargs):
    return {"tool": name, "args": kwargs, "result": "ok"}


def test_discovered_tools_are_added_by_discovery_not_hardcoding():
    discovered = [
        {"name": "get_habit_streak", "description": "read a habit streak"},
        {"name": "log_habit", "description": "log a habit", "requires_approval": True},
    ]
    merged = extend_assistant(REGISTRY, discovered, _fake_invoker)
    # existing tools still present; new ones discovered
    assert "read_emails" in merged
    assert "get_habit_streak" in merged
    assert merged["log_habit"].requires_approval is True


def test_assistant_can_call_a_discovered_tool():
    discovered = [{"name": "get_habit_streak", "description": "read streak"}]
    merged = extend_assistant(REGISTRY, discovered, _fake_invoker)
    script = [
        Step(tool="get_habit_streak", args={"name": "reading"}),
        Step(tool="", args={}, is_final=True, answer="streak is 5"),
    ]
    it = iter(script)
    res = run("check my streak", lambda g, s: next(it), registry=merged)
    assert res.text == "streak is 5"


def test_adding_a_server_tool_needs_no_agent_code_change():
    # simulate the server gaining a new tool between runs — assistant picks it up
    v1 = extend_assistant(REGISTRY, [{"name": "a", "description": "x"}], _fake_invoker)
    v2 = extend_assistant(REGISTRY, [{"name": "a", "description": "x"},
                                     {"name": "b", "description": "y"}], _fake_invoker)
    assert "b" not in v1 and "b" in v2  # no code change — just re-discovery
