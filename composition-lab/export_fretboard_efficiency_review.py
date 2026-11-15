"""Bundle the existing fingering review and its measured data into one offline HTML.

Run after npm ci and generation of public/data/fretboard-efficiency-fixtures.json.
The default output is the sibling deliverables/drop-e-efficiency-review.html.
Use --output to select another location, and --data for another validated bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BUILD_JS = r"""
const esbuild = require('esbuild');
esbuild.buildSync({
  stdin: {
    contents: "import {mountEfficiencyReview} from './src/fretboard-efficiency-view.js'; mountEfficiencyReview();",
    resolveDir: process.cwd(),
    sourcefile: 'fretboard-efficiency-offline-entry.js',
    loader: 'js'
  },
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: 'es2020',
  define: {'import.meta.env': JSON.stringify({BASE_URL: './'})},
  outfile: process.argv[1],
  minify: true,
  legalComments: 'none'
});
"""


def export_review(data_path: Path, output: Path) -> dict:
    data = json.loads(data_path.read_text(encoding='utf-8'))
    if data.get('schema') != 'drop-e-fretboard-efficiency/1' or not data.get('fixtures'):
        raise ValueError('Expected a nonempty drop-e-fretboard-efficiency/1 bundle.')
    if data.get('tuning_high_to_low') != [64, 59, 55, 50, 45, 40, 35, 28]:
        raise ValueError('The review must declare the exact eight-string Drop E tuning.')
    node = shutil.which('node')
    if node is None:
        raise RuntimeError('Node.js is required. Install project dependencies with npm ci first.')
    html = (ROOT / 'riff-builder.html').read_text(encoding='utf-8')
    style_tag = '<link rel="stylesheet" href="/src/riff-builder.css">'
    entry_tag = '<script type="module" src="/src/riff-builder.js"></script>'
    if html.count(style_tag) != 1 or html.count(entry_tag) != 1:
        raise ValueError('Riff Builder entry markup changed; update the exporter without duplicating the UI.')

    with tempfile.TemporaryDirectory(prefix='drop-e-review-') as temp:
        bundled_js = Path(temp) / 'review.js'
        subprocess.run([node, '-e', BUILD_JS, str(bundled_js)], cwd=ROOT, check=True)
        javascript = bundled_js.read_text(encoding='utf-8')
        css = (ROOT / 'src' / 'riff-builder.css').read_text(encoding='utf-8')
        css += '\n' + bundled_js.with_suffix('.css').read_text(encoding='utf-8')

    # Data stays inert JSON; escaping '<' prevents a source string ending its tag.
    inline_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('&', '\\u0026')
    javascript = re.sub(r'</script', r'<\\/script', javascript, flags=re.IGNORECASE)
    css = re.sub(r'</style', r'<\\/style', css, flags=re.IGNORECASE)
    html = html.replace(style_tag, '<style>\n' + css + '\n</style>')
    html = html.replace(entry_tag,
        '<script id="fretboard-efficiency-data" type="application/json">' + inline_data + '</script>\n'
        '<script>\n' + javascript + '\n</script>')
    if re.search(r'<script\b[^>]*\bsrc\s*=|<link\b[^>]*\brel=["\']stylesheet', html, flags=re.IGNORECASE):
        raise ValueError('Offline output still contains an external script or stylesheet.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    return {
        'output': str(output.resolve()),
        'bytes': output.stat().st_size,
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'data_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(),
        'fixtures': [{'id': f['id'], 'notes': len(f['notes']), 'versions': [v['id'] for v in f['versions']]} for f in data['fixtures']],
        'automatic_network_requests': False,
        'audio': False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'public/data/fretboard-efficiency-fixtures.json')
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'deliverables/drop-e-efficiency-review.html')
    args = parser.parse_args()
    print(json.dumps(export_review(args.data.resolve(), args.output.resolve()), indent=2))


if __name__ == '__main__':
    main()
