# Vendored browser dependencies

The lesson loads these pinned browser bundles from this directory. Its runtime does not fetch either library from a CDN. Both JavaScript files are unchanged copies of the indicated npm package files, renamed to include their versions.

| Dependency | Local file | Package file | Purpose | License |
| --- | --- | --- | --- | --- |
| OpenSheetMusicDisplay **2.3.1** | [opensheetmusicdisplay-2.3.1.min.js](./opensheetmusicdisplay-2.3.1.min.js) | `build/opensheetmusicdisplay.min.js` | Render MusicXML notation and supply graphical note/cursor mapping | BSD-3-Clause; [retained license](./OpenSheetMusicDisplay-LICENSE.txt) |
| fflate **0.8.3** | [fflate-0.8.3.min.js](./fflate-0.8.3.min.js) | `umd/index.js` | Extract uploaded compressed MusicXML archives locally | MIT; [retained license](./fflate-LICENSE.txt) |

## Sources

- OpenSheetMusicDisplay: [upstream repository](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay), [exact npm package](https://www.npmjs.com/package/opensheetmusicdisplay/v/2.3.1), [2.3.1 package archive](https://registry.npmjs.org/opensheetmusicdisplay/-/opensheetmusicdisplay-2.3.1.tgz).
- fflate: [upstream repository](https://github.com/101arrowz/fflate), [exact npm package](https://www.npmjs.com/package/fflate/v/0.8.3), [0.8.3 package archive](https://registry.npmjs.org/fflate/-/fflate-0.8.3.tgz).

## File integrity

These SHA-256 values identify the JavaScript bytes currently included in the repository:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `opensheetmusicdisplay-2.3.1.min.js` | 1,475,333 | `caa3052d01f4e1b91fd22e12d6561269d157edced929ef88c95ecb5f9d387812` |
| `fflate-0.8.3.min.js` | 33,044 | `462ef8041fc970e3615a20a9dd2b2e3047a073b2da729ef4f02b634bba8b7b83` |

When updating a dependency, copy its actual browser bundle and required license notices, update the versioned reference in `../index.html`, and rerun the focused tests plus renderer/app integration helpers documented in [the lesson README](../README.md). Recheck notehead mapping, independent chord colors, ties and written-order cursor behavior against the new renderer before changing these recorded hashes.

These software licenses do not grant rights to uploaded sheet music. The bundled conversion fixture's separate provenance and Public Domain statement are documented in [the lesson README](../README.md#fixture-provenance).
