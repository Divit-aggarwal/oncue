#!/bin/sh
# Creates the files for a new reel: storyboards/<slug>.md, video/src/scenes/<slug>.tsx, video/public/audio/.
# usage: scripts/new-reel.sh <slug>     (slug: lowercase letters, digits, - and _)
set -eu

SLUG="${1:-}"
if ! printf '%s' "$SLUG" | grep -Eq '^[a-z0-9][a-z0-9_-]*$'; then
  echo "usage: scripts/new-reel.sh <slug>  (lowercase letters, digits, - and _)" >&2
  exit 1
fi

VIDEO="$(cd "$(dirname "$0")/.." && pwd)"
STORYBOARD="$(cd "$VIDEO/.." && pwd)/storyboards/$SLUG.md"
SCENE="$VIDEO/src/scenes/$SLUG.tsx"
for f in "$STORYBOARD" "$SCENE"; do
  if [ -e "$f" ]; then echo "already exists: $f" >&2; exit 1; fi
done
mkdir -p "$(dirname "$STORYBOARD")" "$VIDEO/public/audio"

cat > "$STORYBOARD" <<EOF
# TODO title

Status: DRAFT, awaiting creator approval.
Target: 30–60s, 90–120 words, 4–6 beats.

**Hook (first 3s):** TODO

## Beat 1

**Say:** TODO exact sentence as it will be spoken.

**Screen:** TODO what appears.

## Beat 2

**Say:** TODO

**Screen:** TODO

## Beat 3

**Say:** TODO

**Screen:** TODO

## Beat 4

**Say:** TODO

**Screen:** TODO

## Technical check

TODO: what the analogy simplifies and where it stops being true.
EOF

cat > "$SCENE" <<EOF
import {Audio, type View2D} from '@revideo/2d';
import {ConceptBox, FlowStep, Headline, Tag} from '../components';
import {clearScene, draw, fadeIn, highlight, slideIn} from '../motions';
import {safeArea} from '../lib/theme';
import {loadTimings, waitUntil} from '../lib/timing';
export default function* (view: View2D) {
  const {timings, startOf} = loadTimings('$SLUG');
  const y = safeArea.centerY;
  yield view.add(<Audio src={'/audio/$SLUG.mp3'} play />); // start the voiceover once it is ready
  // Beat 1: TODO sentence. Clear the screen on its first word.
  yield* clearScene(startOf('TODO first words'));
  // TODO animate beat 1 (one comment per animation call)
  // Beat 2: TODO sentence. Clear beat 1 so the screen is empty on its first word.
  yield* clearScene(startOf('TODO first words'));
  // TODO animate beat 2
  // Beat 3: TODO sentence. Clear beat 2 first.
  yield* clearScene(startOf('TODO first words'));
  // TODO animate beat 3
  // Beat 4: TODO sentence. Clear beat 3 first.
  yield* clearScene(startOf('TODO first words'));
  // TODO animate beat 4
  // Hold the last beat until the voiceover ends.
  yield* waitUntil(timings.duration);
}
EOF

echo "created $STORYBOARD"
echo "created $SCENE"
echo "voiceover: record it, then from video/: uv run python scripts/transcribe.py $SLUG <recording>"
echo "           (writes public/audio/$SLUG.mp3 and timings/$SLUG.json; storyboard must be approved first)"
