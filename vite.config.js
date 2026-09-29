import { defineConfig } from 'vite';
import { resolve } from 'node:path';

export default defineConfig({
  base: '/Guitar-Learning/',
  build: { rollupOptions: { input: {
    main: resolve(import.meta.dirname, 'index.html'),
    liveYinTest: resolve(import.meta.dirname, 'live-yin-test.html')
  } } }
});
