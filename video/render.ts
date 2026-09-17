import {execFileSync} from 'node:child_process';
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

console.log(`output:   ${file}`);
console.log(`streams:  ${probe(['-show_entries', 'stream=codec_type']).split('\n').join(', ')}`);
console.log(`duration: ${Number(probe(['-show_entries', 'format=duration'])).toFixed(2)}s`);
console.log(`size:     ${(Number(probe(['-show_entries', 'format=size'])) / 1e6).toFixed(2)} MB`);
