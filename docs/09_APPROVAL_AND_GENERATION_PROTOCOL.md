# Approval and Generation Protocol

## Objective

The production process must contain explicit human approval checkpoints.

The system should never jump directly from a vague idea to final production.

## Phase A — Creative Proposal

Input:

```text
Creator idea
```

Output:

```text
Creative Proposal
```

The proposal contains:

* concept
* hook
* comedy direction
* analogy
* technical explanation
* narrative structure
* ending
* language
* target duration
* visual opportunities
* sound opportunities

### Approval Gate A

Creator chooses:

* Approve
* Modify
* Reject

No implementation begins before approval.

---

## Phase B — Production Plan

Input:

```text
Approved Creative Proposal
```

Output:

```text
Production Plan
```

The production plan contains:

* scene list
* narration mapping
* animation events
* required visual components
* camera events
* transitions
* sound events
* caption requirements
* timing strategy
* implementation notes

### Approval Gate B

Creator chooses:

* Approve
* Modify
* Reject

No final generation begins before approval.

---

## Phase C — Voice

After Approval Gate B:

The system asks the creator to provide narration.

The creator records the complete narration.

The system processes the recording.

Output:

```text
transcript
timing
segments
pauses
```

---

## Phase D — Generation

The system generates:

1. animation
2. timing synchronization
3. sound effects
4. captions
5. final composition

The system should reuse existing approved components whenever available.

---

## Phase E — Review

Output:

```text
FINAL PREVIEW
```

The creator reviews:

* timing
* comedy
* technical correctness
* animation
* sound
* captions
* overall feel

## Revision

If the creator requests changes, the system should identify the smallest production layer that needs modification.

Example:

```text
Caption issue
→ regenerate captions only

Voice changed
→ regenerate timing + affected animation

SFX issue
→ modify sound layer

Visual issue
→ modify affected scene

Script issue
→ return to Creative Phase
```

The entire video should not be unnecessarily regenerated.

## State Machine

Conceptually:

```text
IDEA
 ↓
CREATIVE_PROPOSAL
 ↓
AWAITING_APPROVAL_A
 ↓
APPROVED_CREATIVE
 ↓
PRODUCTION_PLAN
 ↓
AWAITING_APPROVAL_B
 ↓
APPROVED_PLAN
 ↓
VOICE_INPUT
 ↓
VOICE_ANALYSIS
 ↓
GENERATION
 ↓
PREVIEW
 ↓
FINAL
```

Any stage may return to an earlier stage when required.

## Safety Principle

Approval is explicit.

Silence is not approval.
