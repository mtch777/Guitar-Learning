import { defineConfig } from 'vite';
import { resolve } from 'node:path';

export default defineConfig({
  base: '/Guitar-Learning/',
  build: { rollupOptions: { input: {
    main: resolve(import.meta.dirname, 'index.html'),
    liveYinTest: resolve(import.meta.dirname, 'live-yin-test.html'),
    livePipelineTest: resolve(import.meta.dirname, 'live-pipeline-test.html'),
    compositionReview: resolve(import.meta.dirname, 'composition-review.html'),
    compositionAblationReview: resolve(import.meta.dirname, 'composition-ablation-review.html'),
    compositionPassageReview: resolve(import.meta.dirname, 'composition-passage-review.html')
  } } }
});
