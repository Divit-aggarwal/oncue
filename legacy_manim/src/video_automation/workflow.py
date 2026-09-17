import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .spec import EngineError, Episode, Plan, Proposal, State, Transition

S = State

DOCUMENTS: dict[str, type[BaseModel]] = {"proposal": Proposal, "plan": Plan}

TRANSITIONS: dict[str, tuple[frozenset[State], State]] = {
    "submit_proposal": (frozenset(set(S) - {S.FINAL}), S.AWAITING_APPROVAL_A),
    "approve_proposal": (frozenset({S.AWAITING_APPROVAL_A}), S.APPROVED_CREATIVE),
    "revise_proposal": (frozenset({S.AWAITING_APPROVAL_A}), S.CREATIVE_PROPOSAL),
    "submit_plan": (
        frozenset(set(S) - {S.IDEA, S.CREATIVE_PROPOSAL, S.AWAITING_APPROVAL_A, S.FINAL}),
        S.AWAITING_APPROVAL_B,
    ),
    "approve_plan": (frozenset({S.AWAITING_APPROVAL_B}), S.APPROVED_PLAN),
    "revise_plan": (frozenset({S.AWAITING_APPROVAL_B}), S.PRODUCTION_PLAN),
    "provide_voice": (
        frozenset({S.APPROVED_PLAN, S.VOICE_INPUT, S.VOICE_ANALYSIS, S.GENERATION, S.PREVIEW}),
        S.VOICE_INPUT,
    ),
    "analyze_voice": (
        frozenset({S.VOICE_INPUT, S.VOICE_ANALYSIS, S.GENERATION, S.PREVIEW}),
        S.VOICE_ANALYSIS,
    ),
    "generate": (frozenset({S.VOICE_ANALYSIS, S.GENERATION, S.PREVIEW}), S.GENERATION),
    "preview": (frozenset({S.GENERATION}), S.PREVIEW),
    "finalize": (frozenset({S.PREVIEW}), S.FINAL),
    "reopen": (frozenset({S.FINAL}), S.PREVIEW),
}

GATES = {S.AWAITING_APPROVAL_A: "proposal", S.AWAITING_APPROVAL_B: "plan"}


class WorkflowError(EngineError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data.encode() if isinstance(data, str) else data
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_model(path: Path, model: BaseModel) -> None:
    atomic_write(path, model.model_dump_json(indent=2) + "\n")


class EpisodeDir:
    def __init__(self, root: Path):
        self.root = root
        self.build = root / "build"
        self.output = root / "output"
        self.voice_dir = root / "voice"

    @property
    def episode_file(self) -> Path:
        return self.root / "episode.json"

    def document_path(self, kind: str) -> Path:
        return self.root / f"{kind}.json"

    def load(self) -> Episode:
        if not self.episode_file.exists():
            raise WorkflowError(f"no episode at {self.root}")
        return Episode.model_validate_json(self.episode_file.read_text())

    def save(self, episode: Episode) -> None:
        write_model(self.episode_file, episode)

    def load_document(self, kind: str) -> BaseModel:
        path = self.document_path(kind)
        if not path.exists():
            raise WorkflowError(f"missing {path}")
        try:
            return DOCUMENTS[kind].model_validate_json(path.read_text())
        except ValidationError as e:
            raise WorkflowError(f"invalid {path.name}:\n{e}") from e

    def voice_file(self) -> Path | None:
        files = sorted(self.voice_dir.glob("narration.*")) if self.voice_dir.exists() else []
        return files[0] if files else None

    @contextmanager
    def lock(self):
        if not self.root.is_dir():
            raise WorkflowError(f"no episode at {self.root}")
        with (self.root / ".lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise WorkflowError("episode is busy: another command is running on it") from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def create_episode(episodes_dir: Path, episode_id: str, idea: str) -> EpisodeDir:
    ep = EpisodeDir(episodes_dir / episode_id)
    if ep.episode_file.exists():
        raise WorkflowError(f"episode {episode_id} already exists")
    ep.root.mkdir(parents=True, exist_ok=True)
    ep.save(Episode(id=episode_id, created_at=datetime.now(UTC), idea=idea))
    return ep


def require_state(ep: EpisodeDir, action: str) -> Episode:
    episode = ep.load()
    allowed, _ = TRANSITIONS[action]
    if episode.state not in allowed:
        raise WorkflowError(
            f"cannot {action.replace('_', ' ')} while episode is {episode.state}; "
            f"allowed from: {', '.join(sorted(allowed))}"
        )
    return episode


def transition(ep: EpisodeDir, action: str, note: str = "") -> Episode:
    episode = require_state(ep, action)
    target = TRANSITIONS[action][1]
    episode.history.append(
        Transition(
            at=datetime.now(UTC), source=episode.state, target=target, action=action, note=note
        )
    )
    episode.state = target
    ep.save(episode)
    return episode


def submit(ep: EpisodeDir, kind: str, note: str = "") -> Episode:
    ep.load_document(kind)
    if kind == "plan":
        require_approval(ep, "proposal")
    episode = transition(ep, f"submit_{kind}", note)
    invalidated = ["proposal", "plan"] if kind == "proposal" else ["plan"]
    for key in invalidated:
        episode.approvals.pop(key, None)
    ep.save(episode)
    return episode


def approve(ep: EpisodeDir, note: str = "") -> Episode:
    episode = ep.load()
    kind = GATES.get(episode.state)
    if kind is None:
        raise WorkflowError(f"nothing awaits approval (state {episode.state})")
    ep.load_document(kind)
    digest = sha256_file(ep.document_path(kind))
    episode = transition(ep, f"approve_{kind}", note)
    episode.approvals[kind] = digest
    ep.save(episode)
    return episode


def request_changes(ep: EpisodeDir, note: str) -> Episode:
    episode = ep.load()
    kind = GATES.get(episode.state)
    if kind is None:
        raise WorkflowError(f"nothing awaits approval (state {episode.state})")
    return transition(ep, f"revise_{kind}", note)


def require_approval(ep: EpisodeDir, kind: str) -> None:
    approved = ep.load().approvals.get(kind)
    if approved is None:
        raise WorkflowError(f"{kind} has not been approved")
    if sha256_file(ep.document_path(kind)) != approved:
        raise WorkflowError(
            f"{kind}.json changed after approval; resubmit it with `submit {kind}` for re-approval"
        )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}
