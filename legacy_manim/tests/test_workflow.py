import json

import pytest

from video_automation import workflow
from video_automation.spec import State
from video_automation.workflow import WorkflowError


def test_full_approval_path(approved_episode):
    ep, _ = approved_episode
    episode = ep.load()
    assert episode.state == State.APPROVED_PLAN
    assert set(episode.approvals) == {"proposal", "plan"}
    assert [t.target for t in episode.history] == [
        State.AWAITING_APPROVAL_A,
        State.APPROVED_CREATIVE,
        State.AWAITING_APPROVAL_B,
        State.APPROVED_PLAN,
    ]


def test_plan_cannot_be_submitted_before_creative_approval(project):
    _, settings = project
    ep = workflow.create_episode(settings.episodes_dir, "x", "idea")
    ep.document_path("plan").write_text(json.dumps({"scenes": []}))
    with pytest.raises(WorkflowError):
        workflow.submit(ep, "plan")


def test_invalid_transitions_are_rejected(project):
    _, settings = project
    ep = workflow.create_episode(settings.episodes_dir, "x", "idea")
    for action in ("approve_proposal", "generate", "finalize", "provide_voice"):
        with pytest.raises(WorkflowError, match="cannot"):
            workflow.transition(ep, action)
    with pytest.raises(WorkflowError, match="nothing awaits approval"):
        workflow.approve(ep)
    assert ep.load().state == State.IDEA


def test_malformed_document_is_not_submitted(project):
    _, settings = project
    ep = workflow.create_episode(settings.episodes_dir, "x", "idea")
    ep.document_path("proposal").write_text('{"title": "only a title"}')
    with pytest.raises(WorkflowError, match="invalid proposal.json"):
        workflow.submit(ep, "proposal")
    assert ep.load().state == State.IDEA


def test_editing_an_approved_plan_requires_reapproval(approved_episode):
    ep, _ = approved_episode
    path = ep.document_path("plan")
    path.write_text(path.read_text().replace("Hum bas", "Hum sirf"))
    with pytest.raises(WorkflowError, match="changed after approval"):
        workflow.require_approval(ep, "plan")


def test_resubmitting_proposal_revokes_both_approvals(approved_episode):
    ep, _ = approved_episode
    episode = workflow.submit(ep, "proposal")
    assert episode.state == State.AWAITING_APPROVAL_A
    assert episode.approvals == {}


def test_request_changes_returns_to_drafting(project):
    from conftest import PROPOSAL

    _, settings = project
    ep = workflow.create_episode(settings.episodes_dir, "x", "idea")
    ep.document_path("proposal").write_text(json.dumps(PROPOSAL))
    workflow.submit(ep, "proposal")
    episode = workflow.request_changes(ep, "funnier hook")
    assert episode.state == State.CREATIVE_PROPOSAL
    assert episode.history[-1].note == "funnier hook"


def test_duplicate_episode_rejected(project):
    _, settings = project
    workflow.create_episode(settings.episodes_dir, "x", "idea")
    with pytest.raises(WorkflowError, match="already exists"):
        workflow.create_episode(settings.episodes_dir, "x", "idea")


def test_lock_blocks_concurrent_runs_and_survives_leftover_lock_file(project):
    _, settings = project
    ep = workflow.create_episode(settings.episodes_dir, "x", "idea")
    with ep.lock():
        with pytest.raises(WorkflowError, match="busy"):
            with ep.lock():
                pass
    assert (ep.root / ".lock").exists()
    with ep.lock():
        pass


def test_voice_cannot_replace_final_narration(approved_episode):
    ep, _ = approved_episode
    episode = ep.load()
    episode.state = State.FINAL
    ep.save(episode)
    with pytest.raises(WorkflowError, match="cannot provide voice"):
        workflow.require_state(ep, "provide_voice")


def test_atomic_write_leaves_no_partial_file(tmp_path):
    target = tmp_path / "a.json"
    workflow.atomic_write(target, "old")
    with pytest.raises(TypeError):
        workflow.atomic_write(target, object())
    assert target.read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]
