import {Audio, type View2D} from '@revideo/2d';
import {ConceptBox, FlowStep, Headline, Tag} from '../components';
import {clearScene, fadeIn, slideIn} from '../motions';
import {safeArea} from '../lib/theme';
import {loadTimings, waitUntil} from '../lib/timing';
export default function* (view: View2D) {
  const {timings, startOf} = loadTimings('smoke_take1');
  const y = safeArea.centerY;
  yield view.add(<Audio src={'/audio/smoke_take1.mp3'} play />); // start the voiceover once it is ready
  // Beat 1: Basically RAG mein model ko dobara train nahi kar rahe.
  yield* waitUntil(startOf('Basically RAG mein'));
  // Show the "RAG" headline.
  yield* fadeIn(<Headline text="RAG" y={y - 60} />);
  yield* waitUntil(startOf('dobara train'));
  // Show the "no retraining" tag under it.
  yield* fadeIn(<Tag text="no retraining" y={y + 90} />);
  // Beat 2: Hum bas model ko notes de rahe hain. Clear beat 1 so the screen is empty on its first word.
  yield* clearScene(startOf('Hum bas model'));
  // Show the LLM box.
  yield* fadeIn(<ConceptBox label="LLM" variant="accent" x={180} y={y} />);
  yield* waitUntil(startOf('notes'));
  // Slide the notes box in from the left to sit beside the LLM box.
  yield* slideIn(<ConceptBox label="notes" x={-180} y={y} />, 'left');
  // Show what the notes are.
  yield* fadeIn(<Tag text="extra context in the prompt" y={y + 180} />);
  // Beat 3: Retriever relevant documents dhoondta hai, aur LLM answer likhta hai. Clear beat 2 first.
  yield* clearScene(startOf('Retriever relevant documents'));
  const flow = FlowStep({labels: ['Retriever', 'relevant docs', 'LLM', 'answer']});
  // Reveal Retriever, then an arrow down to relevant docs.
  yield* flow.reveal(2);
  yield* waitUntil(startOf('LLM'));
  // Reveal the arrow down to the LLM box.
  yield* flow.reveal(1);
  yield* waitUntil(startOf('answer likhta'));
  // Reveal the arrow down to the answer box.
  yield* flow.reveal(1);
  // Hold the finished flow until the voiceover ends.
  yield* waitUntil(timings.duration);
}
