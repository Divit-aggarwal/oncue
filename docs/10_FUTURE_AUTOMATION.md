# Future Automation

## Purpose

Define how the system may become increasingly automated without sacrificing creative control.

## Level 1 — Assisted Development

Current target.

The creator interacts with an AI coding/reasoning assistant.

The assistant:

* reads project documentation
* modifies implementation
* runs rendering tools
* diagnoses errors
* improves implementation

The creator remains actively involved.

## Level 2 — Production Orchestration

The creator provides:

```text
concept
```

The system coordinates:

```text
creative proposal
→ approval
→ production plan
→ approval
→ voice
→ generation
→ final
```

## Level 3 — Structured Agent

An AI agent can operate the production pipeline through structured tools.

Possible tools:

```text
create_scene
modify_scene
render_scene
inspect_render
transcribe_voice
analyze_timing
add_sound_event
generate_captions
compose_video
validate_output
```

The agent should operate through explicit interfaces rather than directly modifying arbitrary files.

## Level 4 — Visual Universe Integration

Once the creator has developed the visual universe, the agent can use:

* canonical characters
* canonical locations
* canonical objects
* canonical animation behaviors
* canonical sound identities

The agent becomes a composer of an established visual language.

## Level 5 — Automated Quality Control

The system may automatically check:

### Technical

* render success
* missing assets
* invalid references
* scene failures

### Visual

* text overflow
* objects outside frame
* accidental overlaps
* inconsistent components

### Audio

* missing audio
* clipping
* voice intelligibility
* SFX timing

### Content

* narration/animation mismatch
* missing scene
* caption mismatch

## Level 6 — Alternative AI Backends

The system should eventually support multiple reasoning backends.

Possible options:

* Claude
* local LLM
* cloud LLM
* hybrid

The production engine should not depend on one provider.

## Local-First Principle

Local processing is preferred when practical.

Reasons:

* zero per-video API cost
* privacy
* reproducibility
* offline capability
* control
* easier experimentation

Cloud AI may be used where it provides substantial value.

## Important Constraint

Automation should eliminate repetitive work.

It should not automate away creative decisions that define the creator's brand.
