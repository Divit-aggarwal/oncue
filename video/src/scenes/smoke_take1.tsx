import {Audio, Line, Rect, Txt, type View2D} from '@revideo/2d';
import {all, createRef} from '@revideo/core';
import {colors, fonts, safeArea, text} from '../lib/theme';
import {loadTimings, waitUntil} from '../lib/timing';

// TEMPORARY visuals: plain text, boxes and lines for the pipeline test.
const FADE = 0.3;
const label = {fill: colors.text, fontFamily: fonts.body, fontSize: text.body};
const box = {stroke: colors.text, lineWidth: 4, radius: 24, height: 150, opacity: 0};
const arrow = {stroke: colors.text, lineWidth: 4, endArrow: true, arrowSize: 16, end: 0};

export default function* (view: View2D) {
  const {timings, startOf} = loadTimings('smoke_take1');
  const y = safeArea.centerY;

  // Add the voiceover and wait until the audio node is ready.
  yield view.add(<Audio src={'/audio/smoke_take1.mp3'} play />);

  // Beat 1: Basically RAG mein model ko dobara train nahi kar rahe.
  const title = createRef<Txt>();
  const noRetrain = createRef<Txt>();
  view.add(
    <>
      <Txt ref={title} {...label} text="RAG" fontSize={160} fontWeight={700} y={y - 60} opacity={0} />
      <Txt ref={noRetrain} {...label} text="no retraining" fill={colors.muted} y={y + 90} opacity={0} />
    </>,
  );
  yield* waitUntil(startOf('Basically RAG mein'));
  // Fade in the "RAG" headline.
  yield* title().opacity(1, FADE);
  yield* waitUntil(startOf('dobara train'));
  // Fade in "no retraining" under the headline.
  yield* noRetrain().opacity(1, FADE);

  // Beat 2: Hum bas model ko notes de rahe hain.
  const beat2 = startOf('Hum bas model');
  yield* waitUntil(beat2 - FADE);
  // Fade out beat 1 so the screen is clear exactly when beat 2 starts.
  yield* all(title().opacity(0, FADE), noRetrain().opacity(0, FADE));
  title().remove();
  noRetrain().remove();

  const llm = createRef<Rect>();
  const notes = createRef<Rect>();
  const context = createRef<Txt>();
  view.add(
    <>
      <Rect ref={llm} {...box} width={360} x={200} y={y}>
        <Txt {...label} text="LLM" />
      </Rect>
      <Rect ref={notes} {...box} width={300} x={-700} y={y} opacity={1}>
        <Txt {...label} text="notes" />
      </Rect>
      <Txt ref={context} {...label} text="extra context in the prompt" fill={colors.muted} y={y + 180} opacity={0} />
    </>,
  );
  // Fade in the LLM box.
  yield* llm().opacity(1, FADE);
  yield* waitUntil(startOf('notes'));
  // Slide the notes box in from off-screen left until it sits beside the LLM box.
  yield* notes().x(-200, 0.5);
  // Fade in the "extra context in the prompt" caption.
  yield* context().opacity(1, FADE);

  // Beat 3: Retriever relevant documents dhoondta hai, aur LLM answer likhta hai.
  const beat3 = startOf('Retriever relevant documents');
  yield* waitUntil(beat3 - FADE);
  // Fade out beat 2 so the screen is clear exactly when beat 3 starts.
  yield* all(llm().opacity(0, FADE), notes().opacity(0, FADE), context().opacity(0, FADE));
  llm().remove();
  notes().remove();
  context().remove();

  const step = 270;
  const rowY = (i: number) => y + (i - 1.5) * step;
  const names = ['Retriever', 'relevant docs', 'LLM', 'answer'];
  const boxes = names.map(() => createRef<Rect>());
  const lines = [0, 1, 2].map(() => createRef<Line>());
  view.add(
    <>
      {names.map((name, i) => (
        <Rect ref={boxes[i]} {...box} width={520} y={rowY(i)}>
          <Txt {...label} text={name} />
        </Rect>
      ))}
      {lines.map((ref, i) => (
        <Line ref={ref} {...arrow} points={[[0, rowY(i) + 85], [0, rowY(i + 1) - 85]]} />
      ))}
    </>,
  );
  // Fade in the Retriever box.
  yield* boxes[0]().opacity(1, FADE);
  // Draw the arrow down from Retriever.
  yield* lines[0]().end(1, FADE);
  // Fade in the relevant docs box.
  yield* boxes[1]().opacity(1, FADE);

  yield* waitUntil(startOf('LLM'));
  // Draw the arrow down from relevant docs.
  yield* lines[1]().end(1, 0.2);
  // Fade in the LLM box.
  yield* boxes[2]().opacity(1, FADE);

  yield* waitUntil(startOf('answer likhta'));
  // Draw the arrow down from LLM.
  yield* lines[2]().end(1, 0.2);
  // Fade in the answer box.
  yield* boxes[3]().opacity(1, FADE);

  // Hold the final flow until the voiceover ends.
  yield* waitUntil(timings.duration);
}
