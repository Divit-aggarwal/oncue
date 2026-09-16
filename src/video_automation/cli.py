import argparse
import json
import logging
import sys
from pathlib import Path

from . import workflow
from .config import load_settings
from .spec import EngineError, Plan, Proposal
from .workflow import EpisodeDir

NEXT_STEPS = {
    "IDEA": "write proposal.json, then `submit {id} proposal`",
    "CREATIVE_PROPOSAL": "revise proposal.json, then `submit {id} proposal`",
    "AWAITING_APPROVAL_A": "creator reviews proposal.json: `approve {id}` or `changes {id} --note`",
    "APPROVED_CREATIVE": "write plan.json, then `submit {id} plan`",
    "PRODUCTION_PLAN": "revise plan.json, then `submit {id} plan`",
    "AWAITING_APPROVAL_B": "creator reviews plan.json: `approve {id}` or `changes {id} --note`",
    "APPROVED_PLAN": "record narration, then `voice {id} <file>`",
    "VOICE_INPUT": "`generate {id}` (or `analyze {id}` to inspect timing first)",
    "VOICE_ANALYSIS": "check build/timeline.json, then `generate {id}`",
    "GENERATION": "generation did not finish; fix the reported problem and rerun `generate {id}`",
    "PREVIEW": "review output/final.mp4: `finalize {id}`, or change a layer and regenerate",
    "FINAL": "done; `reopen {id}` to revise",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-automation")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="project root containing engine.toml and episodes/",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="create an episode from an idea")
    new.add_argument("episode")
    new.add_argument("--idea", required=True)

    sub.add_parser("list", help="list episodes and their states")
    for name, text in [
        ("status", "show episode state and next step"),
        ("approve", "approve the document awaiting approval"),
        ("analyze", "transcribe narration and build the timeline"),
        ("generate", "render, mix, caption, compose and validate"),
        ("finalize", "accept the preview as final"),
        ("reopen", "reopen a final episode for revision"),
    ]:
        p = sub.add_parser(name, help=text)
        p.add_argument("episode")
        if name == "approve":
            p.add_argument("--note", default="")

    changes = sub.add_parser("changes", help="request changes to the document awaiting approval")
    changes.add_argument("episode")
    changes.add_argument("--note", required=True)

    submit = sub.add_parser("submit", help="validate a document and submit it for approval")
    submit.add_argument("episode")
    submit.add_argument("document", choices=["proposal", "plan"])
    submit.add_argument("--note", default="")

    check = sub.add_parser("check", help="validate a proposal or plan file without submitting")
    check.add_argument("document", choices=["proposal", "plan"])
    check.add_argument("path", type=Path)

    voice_cmd = sub.add_parser("voice", help="provide the creator's narration recording")
    voice_cmd.add_argument("episode")
    voice_cmd.add_argument("file", type=Path)
    return parser


def run(args: argparse.Namespace) -> int:
    settings = load_settings(args.project.resolve())
    if args.command == "check":
        model = {"proposal": Proposal, "plan": Plan}[args.document]
        model.model_validate_json(args.path.read_text())
        print(f"{args.path} is a valid {args.document}")
        return 0
    if args.command == "list":
        for path in sorted(settings.episodes_dir.glob("*/episode.json")):
            episode = EpisodeDir(path.parent).load()
            print(f"{episode.id:30} {episode.state}")
        return 0
    if args.command == "new":
        ep = workflow.create_episode(settings.episodes_dir, args.episode, args.idea)
        print(f"created {ep.root}")
        return print_status(ep)

    ep = EpisodeDir(settings.episodes_dir / args.episode)
    if args.command == "status":
        return print_status(ep)
    with ep.lock():
        if args.command == "submit":
            workflow.submit(ep, args.document, args.note)
        elif args.command == "approve":
            workflow.approve(ep, args.note)
        elif args.command == "changes":
            workflow.request_changes(ep, args.note)
        elif args.command in ("finalize", "reopen"):
            workflow.transition(ep, args.command)
        elif args.command == "voice":
            from .voice import ingest

            workflow.require_approval(ep, "plan")
            workflow.require_state(ep, "provide_voice")
            ingest(args.file, ep.voice_dir, settings.voice.silence_threshold_db)
            workflow.transition(ep, "provide_voice")
        elif args.command in ("analyze", "generate"):
            from . import pipeline
            from .voice import FasterWhisperTranscriber

            transcriber = FasterWhisperTranscriber(settings.voice)
            if args.command == "analyze":
                timeline = pipeline.analyze(ep, settings, transcriber)
                for s in timeline.scenes:
                    print(f"{s.id:24} {s.start:7.2f}s  {s.duration:6.2f}s  cues={s.cues}")
            else:
                report = pipeline.generate(ep, settings, transcriber)
                for warning in report.warnings:
                    print(f"warning: {warning}")
                for error in report.errors:
                    print(f"error: {error}")
                if not report.ok:
                    return 1
                print(f"preview: {ep.output / 'final.mp4'}")
    return print_status(ep)


def print_status(ep: EpisodeDir) -> int:
    episode = ep.load()
    print(f"episode: {episode.id}\nstate:   {episode.state}")
    if episode.approvals:
        print(f"approved: {', '.join(sorted(episode.approvals))}")
    print(f"next:    {NEXT_STEPS[episode.state].format(id=episode.id)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if not args.verbose:
        logging.getLogger("video_automation.pipeline").setLevel(logging.INFO)
    try:
        return run(args)
    except KeyboardInterrupt:
        print(
            "interrupted; completed stages are kept, rerun the command to resume", file=sys.stderr
        )
        return 130
    except Exception as e:
        from pydantic import ValidationError

        known = (EngineError, ValidationError, json.JSONDecodeError, FileNotFoundError)
        if args.verbose or not isinstance(e, known):
            raise
        print(f"error: {e}", file=sys.stderr)
        return 1
