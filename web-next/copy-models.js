import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const VAD_DIST = path.join(__dirname, 'node_modules', '@ricky0123', 'vad-web', 'dist');
const ORT_DIST = path.join(__dirname, 'node_modules', 'onnxruntime-web', 'dist');
const PUBLIC_DIR = path.join(__dirname, 'public');

if (!fs.existsSync(PUBLIC_DIR)) {
  fs.mkdirSync(PUBLIC_DIR, { recursive: true });
}

const copyFile = (src, dest) => {
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`Copied ${path.basename(src)} to public/`);
  } else {
    console.warn(`File not found: ${src}`);
  }
};

// Copy VAD files
copyFile(path.join(VAD_DIST, 'vad.worklet.bundle.min.js'), path.join(PUBLIC_DIR, 'vad.worklet.bundle.min.js'));
copyFile(path.join(VAD_DIST, 'silero_vad.onnx'), path.join(PUBLIC_DIR, 'silero_vad.onnx'));
copyFile(path.join(VAD_DIST, 'silero_vad_legacy.onnx'), path.join(PUBLIC_DIR, 'silero_vad_legacy.onnx'));
copyFile(path.join(VAD_DIST, 'silero_vad_v5.onnx'), path.join(PUBLIC_DIR, 'silero_vad_v5.onnx'));

// Copy ONNX files
const ortFiles = [
  'ort-wasm.wasm',
  'ort-wasm-simd.wasm',
  'ort-wasm-simd-threaded.wasm',
  'ort-wasm-simd-threaded.mjs',
  'ort-wasm-simd-threaded.jsep.wasm',
  'ort-wasm-simd-threaded.jsep.mjs'
];

ortFiles.forEach(file => {
  copyFile(path.join(ORT_DIST, file), path.join(PUBLIC_DIR, file));
});

console.log("VAD and ONNX files copied successfully!");
