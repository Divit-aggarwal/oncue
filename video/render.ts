import {execFileSync, spawnSync} from 'node:child_process';
import {existsSync, readFileSync, renameSync} from 'node:fs';
import {renderVideo} from '@revideo/renderer';

const slug = process.argv[2];
if (!slug) {
  console.error('usage: npm run render -- <slug>');
  process.exit(1);
}
const audio = `./public/audio/${slug}.mp3`;
if (!existsSync(audio)) throw new Error(`missing ${audio}`);

const file = await renderVideo({
  projectFile: './src/project.tsx',
  variables: {slug},
  settings: {outFile: `${slug}.mp4`, outDir: './output', logProgress: true},
});

const probe = (args: string[]) =>
  execFileSync('ffprobe', ['-v', 'error', ...args, '-of', 'csv=p=0', file], {encoding: 'utf8'}).trim();

if (!probe(['-select_streams', 'a', '-show_entries', 'stream=codec_name'])) {
  console.warn(`WARNING: Revideo produced ${file} without audio; muxing ${audio} with ffmpeg.`);
  const tmp = file.replace(/\.mp4$/, '.mux.mp4');
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', file, '-i', audio,
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-shortest', tmp]);
  renameSync(tmp, file);
}

// Integrated loudness (LUFS) from ffmpeg's ebur128 summary, which is printed on stderr.
const lufs = () => {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', file, '-af', 'ebur128', '-f', 'null', '-'], {encoding: 'utf8'});
  return Number(r.stderr.match(/Summary:[\s\S]*?I:\s+(-?[\d.]+) LUFS/)![1]);
};
// loudnorm prints its JSON report as the last {...} block on stderr.
const loudnorm = (filter: string, out: string[]) => {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', file, '-af', `${filter}:print_format=json`, ...out], {encoding: 'utf8'});
  if (r.status !== 0) throw new Error(`loudnorm failed:\n${r.stderr.slice(-1000)}`);
  return JSON.parse(r.stderr.slice(r.stderr.lastIndexOf('{'), r.stderr.lastIndexOf('}') + 1));
};
const target = 'loudnorm=I=-16:TP=-1.5:LRA=11';
const before = lufs();
let normalization = '';
if (before < -18) {
  // Two-pass: measure, then apply with the measured values so the gain is linear where possible.
  const m = loudnorm(target, ['-f', 'null', '-']);
  const tmp = file.replace(/\.mp4$/, '.loud.mp4');
  const applied = loudnorm(
    `${target}:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}` +
      `:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`,
    ['-map', '0:v', '-map', '0:a', '-c:v', 'copy', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-y', tmp],
  );
  renameSync(tmp, file);
  // ffmpeg silently falls back to dynamic when linear gain would break the true-peak limit.
  normalization = applied.normalization_type;
}

console.log(`output:   ${file}`);
console.log(`streams:  ${probe(['-show_entries', 'stream=codec_type']).split('\n').join(', ')}`);
console.log(`duration: ${Number(probe(['-show_entries', 'format=duration'])).toFixed(2)}s`);
console.log(`loudness: ${before} LUFS${normalization ? ` -> ${lufs()} LUFS (two-pass loudnorm, ${normalization})` : ''}`);
console.log(`size:     ${(Number(probe(['-show_entries', 'format=size'])) / 1e6).toFixed(2)} MB`);

// Step 4 checks: flag a duration outside 30–60s and any beat whose visual starts >0.3s after its first word.
// A beat's visual start is the first frame at or after its word where the picture gets brighter
// (everything is light on a dark background); this reads ~1 frame late because a fade starts at opacity 0.
const FPS = 30;
const seconds = Number(probe(['-show_entries', 'format=duration']));
if (seconds < 30 || seconds > 60) console.warn(`FLAG: duration ${seconds.toFixed(2)}s is outside 30–60s`);

const storyboard = `../storyboards/${slug}.md`;
if (existsSync(storyboard)) {
  const tokens = (s: string) =>
    s.toLowerCase().split(/\s+/).map(t => t.replace(/^[\p{P}\p{S}।॥]+|[\p{P}\p{S}।॥]+$/gu, '')).filter(Boolean);
  const words: {text: string; start: number}[] = JSON.parse(readFileSync(`./timings/${slug}.json`, 'utf8')).words;
  const spoken = words.flatMap(w => tokens(w.text).map(t => ({t, start: w.start})));
  const says = [...readFileSync(storyboard, 'utf8').matchAll(/\*\*Say:\*\*\s*(.+)/g)].map(m => m[1]);
  const stats = spawnSync('ffmpeg', ['-v', 'error', '-i', file, '-vf', 'signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-', '-f', 'null', '-'],
    {encoding: 'utf8', maxBuffer: 256 * 1024 * 1024}).stdout;
  const brightness = [...stats.matchAll(/YAVG=([\d.]+)/g)].map(m => Number(m[1]));
  let cursor = 0;
  says.forEach((say, i) => {
    const needle = tokens(say).slice(0, 3);
    let k = cursor;
    while (k + needle.length <= spoken.length && !needle.every((t, j) => spoken[k + j].t === t)) k++;
    if (k + needle.length > spoken.length) return console.warn(`FLAG: beat ${i + 1} "${needle.join(' ')}" not found in timings`);
    cursor = k + needle.length;
    const word = spoken[k].start;
    let f = Math.max(1, Math.floor(word * FPS) - 1);
    while (f < brightness.length && !(brightness[f] > brightness[f - 1] + 0.001)) f++;
    const lag = f / FPS - word;
    console.log(`beat ${i + 1}:   word ${word.toFixed(2)}s, visual ${(f / FPS).toFixed(2)}s, lag ${lag >= 0 ? '+' : ''}${lag.toFixed(3)}s${lag > 0.3 ? '  FLAG: more than 0.3s late' : ''}`);
  });
} else {
  console.warn(`no ${storyboard}; skipped the beat sync check`);
}
