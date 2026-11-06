/** alphaTab 1.8.4 keys an intermediate legato slide's pitch curve to a note
 * which was never reattacked. Rebase that curve to the still-sounding note.
 * Registration is limited to scores created by this builder. Notation and
 * events remain untouched; ordinary slides use alphaTab's original path. */
const registered = new WeakMap();

export function registerRiffPlayback(at, score) {
  const Generator = at.midi.MidiFileGenerator;
  let scores = registered.get(Generator);
  if (!scores) {
    const original = Generator.prototype._generateSlide;
    if (typeof original !== 'function' || typeof Generator.getPitchWheel !== 'function') {
      throw new Error('The guitar player does not provide the verified slide playback API.');
    }
    scores = new WeakSet(); registered.set(Generator, scores);
    Generator.prototype._generateSlide = function(note, start, duration, key, channel, tempo) {
      if (!scores.has(note.beat.voice.bar.staff.track.score)) return original.call(this,note,start,duration,key,channel,tempo);
      let origin = note, linked = false; const visited = new Set();
      while (true) {
        if (visited.has(origin)) throw new Error('Cyclic slide playback connection.');
        visited.add(origin);
        if (origin.isTieDestination && origin.tieOrigin) origin = origin.tieOrigin;
        else if (origin.slideOrigin?.slideOutType === at.model.SlideOutType.Legato) {
          linked = true; origin = origin.slideOrigin;
        } else break;
      }
      if (!linked) return original.call(this,note,start,duration,key,channel,tempo);
      const rootKey = origin.calculateRealValue(this.applyTranspositionPitches,true);
      // Native bend values are half-semitones. Derive the wheel offset using
      // the same native conversion rather than assuming its configured range.
      const offset = Generator.getPitchWheel(2*(key-rootKey))-Generator.getPitchWheel(0);
      const handler = this._handler, rootChannel = this._determineChannel(origin.beat.voice.bar.staff.track,origin);
      this._handler = new Proxy(handler,{get(target,property) {
        if (property === 'addNoteBend') return (track,tick,_channel,_key,value) => target.addNoteBend(track,tick,rootChannel,rootKey,value+offset);
        const value=Reflect.get(target,property);return typeof value==='function'?value.bind(target):value;
      }});
      try {return original.call(this,note,start,duration,key,channel,tempo);}
      finally {this._handler=handler;}
    };
  }
  scores.add(score);
  return score;
}
