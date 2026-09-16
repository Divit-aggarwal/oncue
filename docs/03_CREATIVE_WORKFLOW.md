# Creative Workflow

> Status: draft assembled from `CLAUDE.md` and `09_APPROVAL_AND_GENERATION_PROTOCOL.md`. Awaiting creator review.

## Two Modes

Every request is either creative development or implementation. The assistant says which one it is working in and does not silently move from one to the other.

## Creative Development (before Gate A)

The creator gives a rough idea (`video-automation new <id> --idea "..."`). The assistant develops `proposal.json`:

* hook options and comedy direction
* analogy, with its technical limitations written in `analogy_limitations`
* technical explanation, which must be accurate
* narrative structure, ending, pacing, language
* visual and sound opportunities as suggestions, not decisions

Alternatives are offered where useful. The creator edits the file and approves it (`approve`) or sends it back (`changes --note`).

## Production Planning (before Gate B)

From the approved proposal, the assistant writes `plan.json`: scenes, the exact narration per scene, cues, animation events, visual component references, sound events and caption settings (see `04_VIDEO_SPECIFICATION.md`). Visual components are existing approved components or clearly temporary placeholders. The creator approves or requests changes.

## Production (after Gate B)

1. The creator records the full narration and runs `voice`.
2. `analyze` shows how the recording maps onto scenes.
3. `generate` renders, mixes, captions, composes and validates.
4. The creator reviews `output/final.mp4`, then runs `finalize` or requests a layer-specific revision.

## Revisions

Fix at the smallest layer (see the table in `README.md`). Script changes go back to the creative phase: `submit <id> proposal`.
