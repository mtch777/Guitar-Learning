# Browser ↔ librosa feature parity test

This isolates DSP parity from live capture and XGBoost.

1. Pick any original ringing training WAV, for example `s3_f0_normal_ringing.wav`.
2. Export the Python/librosa reference:

```bash
python training/export_feature_reference.py path/to/s3_f0_normal_ringing.wav --out training/results/parity/reference.json
```

3. In the browser, decode **that exact WAV** with Web Audio and call:

```js
import { compareFeatureParity } from "./training/browser_feature_parity.js";

const audioBuffer = await audioContext.decodeAudioData(await file.arrayBuffer());
const report = compareFeatureParity(
  audioBuffer.getChannelData(0),
  audioBuffer.sampleRate,
  referenceJson
);
console.table(report.worst);
```

The report compares all 107 values by exact feature name and sorts the largest relative mismatches first.

Do not use live microphone audio for this test. The same WAV must feed both extractors.
