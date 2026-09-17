import {Audio, type View2D} from '@revideo/2d';
import {ConceptBox, FlowStep, Headline, Tag} from '../components';
import {clearScene, fadeIn, slideIn} from '../motions';
import {safeArea} from '../lib/theme';
import {loadTimings, waitUntil} from '../lib/timing';
export default function* (view: View2D) {
  const {timings, startOf} = loadTimings('smoke_take1');
  const y = safeArea.centerY;
  yield view.add(<Audio src={'/audio/smoke_take1.mp3'} play />); // yielded: Revideo warns if the audio node is used before it is ready
  // Beat 1: Basically RAG mein model ko dobara train nahi kar rahe.
  yield* waitUntil(startOf('Basically RAG mein'));
  yield* fadeIn(<Headline text="RAG" y={y - 60} />);
  yield* waitUntil(startOf('dobara train'));
  yield* fadeIn(<Tag text="no retraining" y={y + 90} />);
  // Beat 2: Hum bas model ko notes de rahe hain.
  yield* clearScene(startOf('Hum bas model'));
  yield* fadeIn(<ConceptBox label="LLM" variant="accent" x={180} y={y} />);
  yield* waitUntil(startOf('notes'));
  yield* slideIn(<ConceptBox label="notes" x={-180} y={y} />, 'left');
  yield* fadeIn(<Tag text="extra context in the prompt" y={y + 180} />);
  // Beat 3: Retriever relevant documents dhoondta hai, aur LLM answer likhta hai.
  yield* clearScene(startOf('Retriever relevant documents'));
  const flow = FlowStep({labels: ['Retriever', 'relevant docs', 'LLM', 'answer']});
  yield* flow.reveal(2);
  yield* waitUntil(startOf('LLM'));
  yield* flow.reveal(1);
  yield* waitUntil(startOf('answer likhta'));
  yield* flow.reveal(1);
  yield* waitUntil(timings.duration);
}
