export const SUPPORTED_EXTENSIONS = ['musicxml', 'xml', 'mxl'];
const MAX_BYTES = 20 * 1024 * 1024;

function decode(bytes) {
  if (bytes[0] === 0xff && bytes[1] === 0xfe) return new TextDecoder('utf-16le').decode(bytes);
  if (bytes[0] === 0xfe && bytes[1] === 0xff) return new TextDecoder('utf-16be').decode(bytes);
  if (bytes[0] === 0x3c && bytes[1] === 0) return new TextDecoder('utf-16le', {fatal:true}).decode(bytes);
  if (bytes[0] === 0 && bytes[1] === 0x3c) return new TextDecoder('utf-16be', {fatal:true}).decode(bytes);
  const declaration = new TextDecoder('ascii').decode(bytes.slice(0, 300));
  const encoding = declaration.match(/<\?xml\s[^?]*encoding\s*=\s*["']([^"']+)["']/i)?.[1] || 'utf-8';
  try { return new TextDecoder(encoding, {fatal:true}).decode(bytes); }
  catch (_) { throw new Error(`This score has an unsupported or invalid ${encoding} text encoding. Export a UTF-8 MusicXML copy.`); }
}

/** Read note data locally. ZIP contents are never executed or sent to a server. */
export async function readScoreFile(file, {unzip = globalThis.fflate?.unzipSync} = {}) {
  const extension = file.name.split('.').pop().toLowerCase();
  if (!SUPPORTED_EXTENSIONS.includes(extension)) {
    throw new Error('Choose a .musicxml, .xml or .mxl score. Export other formats to MusicXML first.');
  }
  if (!file.size || file.size > MAX_BYTES) throw new Error('Choose a nonempty score smaller than 20 MB.');
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (extension !== 'mxl') return decode(bytes);
  if (!unzip) throw new Error('The compressed-score reader did not load. Refresh and try again.');
  if (bytes[0] !== 0x50 || bytes[1] !== 0x4b) throw new Error('This .mxl file is not a compressed MusicXML archive.');
  let declaredTotal = 0;
  const entries = unzip(bytes, {filter(entry) {
    if (!/\.(xml|musicxml)$/i.test(entry.name)) return false;
    declaredTotal += entry.originalSize;
    if (entry.originalSize > MAX_BYTES || declaredTotal > MAX_BYTES) {
      throw new Error('The expanded score exceeds the 20 MB limit.');
    }
    return true;
  }});
  let actualTotal = 0;
  for (const entry of Object.values(entries)) {
    actualTotal += entry.length;
    if (actualTotal > MAX_BYTES) throw new Error('The expanded score exceeds the 20 MB limit.');
  }
  let path;
  const container = entries['META-INF/container.xml'];
  if (container) {
    const document = new DOMParser().parseFromString(decode(container), 'application/xml');
    const roots = Array.from(document.getElementsByTagNameNS('*', 'rootfile'));
    path = (roots.find(root => root.getAttribute('media-type') === 'application/vnd.recordare.musicxml+xml') || roots[0])?.getAttribute('full-path');
    if (path && !entries[path]) throw new Error('The MusicXML archive is missing its declared score file.');
  }
  if (!path) path = Object.keys(entries).find(name => !name.startsWith('META-INF/') && /\.(musicxml|xml)$/i.test(name));
  if (!path) throw new Error('No MusicXML score was found inside this archive.');
  return decode(entries[path]);
}
