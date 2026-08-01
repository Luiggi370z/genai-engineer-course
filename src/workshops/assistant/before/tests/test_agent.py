from assistant.agent import Pending, Step, run


def test_readonly_tool_runs_and_finishes():
    script = [
        Step(tool="read_emails", args={"limit": 1}),
        Step(tool="", args={}, is_final=True, answer="you have 1 email"),
    ]
    it = iter(script)
    res = run("summarize inbox", lambda g, s: next(it))
    assert res.text == "you have 1 email"
    assert res.pending is None


def test_gated_tool_pauses_without_approval():
    script = [Step(tool="send_telegram", args={"chat_id": "1", "message": "hi"})]
    it = iter(script)
    res = run("message the team", lambda g, s: next(it))
    assert isinstance(res.pending, Pending)
    assert res.pending.tool == "send_telegram"
    assert not res.fired_irreversible_tool_without_approval


def test_gated_tool_fires_with_approval():
    script = [
        Step(tool="send_telegram", args={"chat_id": "1", "message": "hi"}),
        Step(tool="", args={}, is_final=True, answer="sent"),
    ]
    it = iter(script)
    res = run("message the team", lambda g, s: next(it), approvals={"send_telegram": True})
    assert res.text == "sent"
