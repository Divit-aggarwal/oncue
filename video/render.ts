import {execFileSync, spawnSync} from 'node:child_process';
import {existsSync, renameSync} from 'node:fs';
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
const before = lufs();
if (before < -18) {
  // ponytail: single-pass loudnorm (dynamic); switch to two-pass if it audibly flattens delivery.
  const tmp = file.replace(/\.mp4$/, '.loud.mp4');
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', file, '-map', '0:v', '-map', '0:a', '-c:v', 'copy',
    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', tmp]);
  renameSync(tmp, file);
}

console.log(`output:   ${file}`);
console.log(`streams:  ${probe(['-show_entries', 'stream=codec_type']).split('\n').join(', ')}`);
console.log(`duration: ${Number(probe(['-show_entries', 'format=duration'])).toFixed(2)}s`);
console.log(`loudness: ${before} LUFS${before < -18 ? ` -> ${lufs()} LUFS (loudnorm I=-16)` : ''}`);
console.log(`size:     ${(Number(probe(['-show_entries', 'format=size'])) / 1e6).toFixed(2)} MB`);
