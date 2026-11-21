export const MAJOR_TRIADS = Object.freeze([
  {name:'C', notes:['C','E','G'], root:0},
  {name:'F', notes:['F','A','C'], root:5},
  {name:'G', notes:['G','B','D'], root:7},
  {name:'D', notes:['D','F♯','A'], root:2},
  {name:'E', notes:['E','G♯','B'], root:4},
  {name:'A', notes:['A','C♯','E'], root:9},
  {name:'B♭', notes:['B♭','D','F'], root:10},
  {name:'B', notes:['B','D♯','F♯'], root:11},
  {name:'D♭', notes:['D♭','F','A♭'], root:1},
  {name:'E♭', notes:['E♭','G','B♭'], root:3},
  {name:'A♭', notes:['A♭','C','E♭'], root:8},
  {name:'F♯', notes:['F♯','A♯','C♯'], root:6},
]);
export const BLACK_KEYS = new Set([1,3,6,8,10]);
export function triadPitchClasses(root) { return [root,root+4,root+7].map(midi=>midi%12); }
export function blackKeyCount(root) { return triadPitchClasses(root).filter(pitch=>BLACK_KEYS.has(pitch)).length; }
export function groupedTriads() { return [0,1,2,3].map(count=>({count, chords:MAJOR_TRIADS.filter(t=>blackKeyCount(t.root)===count)})); }
