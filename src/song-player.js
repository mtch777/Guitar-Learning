import { isTimeFile, applySongPitch, timeNotePosition } from './song-profile.js';
import { TIME_SOLO_DROP_E_TUNING } from './data/time-solo.js';

const ALPHATAB_VERSION =
  '1.8.4';

const ALPHATAB_ROOT =
  'https://cdn.jsdelivr.net/npm/' +
  '@coderline/alphatab@' +
  ALPHATAB_VERSION +
  '/dist/';

const ALPHATAB_SCRIPT =
  ALPHATAB_ROOT +
  'alphaTab.min.js';

const ALPHATAB_SOUNDFONT =
  ALPHATAB_ROOT +
  'soundfont/sonivox.sf2';

const ALPHATAB_FONT_DIRECTORY =
  ALPHATAB_ROOT +
  'font/';

let alphaTabLoadPromise = null;

function loadAlphaTab() {
  if (window.alphaTab) {
    return Promise.resolve(
      window.alphaTab
    );
  }

  if (alphaTabLoadPromise) {
    return alphaTabLoadPromise;
  }

  alphaTabLoadPromise =
    new Promise(
      (
        resolve,
        reject
      ) => {
        const script =
          document.createElement(
            'script'
          );

        script.src =
          ALPHATAB_SCRIPT;

        script.async =
          true;

        script.addEventListener(
          'load',
          () => {
            if (
              window.alphaTab
            ) {
              resolve(
                window.alphaTab
              );
            } else {
              reject(
                new Error(
                  'alphaTab loaded without exposing its API.'
                )
              );
            }
          }
        );

        script.addEventListener(
          'error',
          () =>
            reject(
              new Error(
                'Could not load alphaTab.'
              )
            )
        );

        document.head
          .appendChild(
            script
          );
      }
    );

  return alphaTabLoadPromise;
}

function getTrackStringTuning(
  track
) {
  const values =
    track
      ?.staves?.[0]
      ?.stringTuning
      ?.tunings;

  return values
    ? Array.from(values)
    : [];
}

export function setupSongPlayer({
  onActiveNotes,
  onPositionChanged,
  onTrackChanged,
  onScoreLoaded
} = {}) {
  const fileInput =
    document.getElementById(
      'songPlayerFile'
    );

  const trackSelect =
    document.getElementById(
      'songPlayerTrack'
    );

  const playPauseButton =
    document.getElementById(
      'songPlayerPlayPause'
    );

  const stopButton =
    document.getElementById(
      'songPlayerStop'
    );

  const speedSelect =
    document.getElementById(
      'songPlayerSpeed'
    );

  const progress =
    document.getElementById(
      'songPlayerProgress'
    );

  const currentTime =
    document.getElementById(
      'songPlayerCurrentTime'
    );

  const duration =
    document.getElementById(
      'songPlayerDuration'
    );

  const status =
    document.getElementById(
      'songPlayerStatus'
    );

  const surface =
    document.getElementById(
      'alphaTabSurface'
    );

  if (
    !fileInput ||
    !trackSelect ||
    !playPauseButton ||
    !stopButton ||
    !speedSelect ||
    !progress ||
    !currentTime ||
    !duration ||
    !status ||
    !surface
  ) {
    return;
  }

  let alphaTabApi = null;
  let score = null;
  let timeProfile = false;
  let selectedTrackIndex = null;
  let playerReady = false;
  let playing = false;
  let endTimeMs = 0;
  let scrubbing = false;
  let currentTick = 0;
  let activeNotes = [];
  let bendAnimationFrame = null;

  function applyPlaybackSpeed() {
    if (!alphaTabApi) return;
    const speed = Number(speedSelect.value);
    if (!Number.isFinite(speed) || speed <= 0) return;
    alphaTabApi.playbackSpeed = speed;
  }

  const formatTime =
    milliseconds => {
      const totalSeconds =
        Math.max(
          0,
          Math.round(
            Number(milliseconds || 0) /
            1000
          )
        );

      const minutes =
        Math.floor(
          totalSeconds /
          60
        );

      const seconds =
        String(
          totalSeconds %
          60
        ).padStart(
          2,
          '0'
        );

      return (
        minutes +
        ':' +
        seconds
      );
    };

  const resetProgress =
    () => {
      endTimeMs = 0;
      progress.value = '0';
      progress.disabled = true;
      currentTime.textContent = '0:00';
      duration.textContent = '0:00';
    };

  function getBendSemitones(
    note,
    tick
  ) {
    const points =
      Array.from(
        note?.bendPoints ||
        []
      );

    if (
      points.length === 0
    ) {
      return 0;
    }

    const beat =
      note.beat;

    const startTick =
      Number(
        beat?.absolutePlaybackStart ??
        0
      );

    const durationTick =
      Math.max(
        1,
        Number(
          beat?.playbackDuration ??
          1
        )
      );

    const relativePosition =
      Math.max(
        0,
        Math.min(
          1,
          (
            Number(tick) -
            startTick
          ) /
          durationTick
        )
      );

    /*
      alphaTab BendPoint.offset runs from 0..60 across the
      note duration. BendPoint.value is measured in quarter-tones,
      so divide by 2 to convert to semitones.
    */
    const bendOffset =
      relativePosition *
      60;

    const sortedPoints =
      points
        .slice()
        .sort(
          (a, b) =>
            Number(a.offset) -
            Number(b.offset)
        );

    if (
      bendOffset <=
      Number(
        sortedPoints[0].offset
      )
    ) {
      return (
        Number(
          sortedPoints[0].value
        ) /
        2
      );
    }

    for (
      let index = 1;
      index <
        sortedPoints.length;
      index++
    ) {
      const previous =
        sortedPoints[
          index - 1
        ];

      const next =
        sortedPoints[index];

      const nextOffset =
        Number(
          next.offset
        );

      if (
        bendOffset <=
          nextOffset
      ) {
        const previousOffset =
          Number(
            previous.offset
          );

        const span =
          Math.max(
            0.0001,
            nextOffset -
              previousOffset
          );

        const amount =
          (
            bendOffset -
              previousOffset
          ) /
          span;

        const quarterTones =
          Number(
            previous.value
          ) +
          (
            Number(
              next.value
            ) -
            Number(
              previous.value
            )
          ) *
          amount;

        return (
          quarterTones /
          2
        );
      }
    }

    return (
      Number(
        sortedPoints[
          sortedPoints.length -
          1
        ].value
      ) /
      2
    );
  }

  function emitActiveNotes(
    tick =
      currentTick
  ) {
    onActiveNotes?.(
      activeNotes.map(
        item => ({
          ...item,
          bendSemitones:
            getBendSemitones(
              item.note,
              tick
            )
        })
      )
    );
  }

  function stopBendAnimation() {
    if (
      bendAnimationFrame !==
        null
    ) {
      cancelAnimationFrame(
        bendAnimationFrame
      );
    }

    bendAnimationFrame =
      null;
  }

  function startBendAnimation() {
    stopBendAnimation();

    const draw =
      () => {
        if (
          !playing ||
          !alphaTabApi
        ) {
          bendAnimationFrame =
            null;
          return;
        }

        currentTick =
          Number(
            alphaTabApi
              .tickPosition ||
            currentTick
          );

        emitActiveNotes(
          currentTick
        );

        bendAnimationFrame =
          requestAnimationFrame(
            draw
          );
      };

    bendAnimationFrame =
      requestAnimationFrame(
        draw
      );
  }

  const setStatus =
    text => {
      status.textContent =
        text;
    };

  const clearActiveNotes =
    () => {
      onActiveNotes?.([]);
    };

  function updateTransport() {
    const canPlay =
      Boolean(
        score &&
        playerReady &&
        selectedTrackIndex !==
          null
      );

    playPauseButton.disabled =
      !canPlay;

    stopButton.disabled =
      !canPlay;

    progress.disabled =
      !canPlay ||
      endTimeMs <= 0;

    playPauseButton.textContent =
      playing
        ? '⏸ Pause'
        : '▶ Play';
  }

  function getSelectedTrack() {
    if (
      !score ||
      selectedTrackIndex ===
        null
    ) {
      return null;
    }

    return (
      score.tracks[
        selectedTrackIndex
      ] ||
      null
    );
  }

  // The placeholder set must be computed from the same alphaTab notes and
  // transposition mapping that activeBeatsChanged uses during playback.
  function collectTrackPositions(track) {
    // Only the selected guitar-solo track, restricted to the solo note range.
    // bendPoints are not separate fretted notes.
    const events=[];
    for(const staff of track.staves||[])
      for(const [barIndex, bar] of (staff.bars||[]).entries())
        // The Time F#m score's guitar solo is measures 94–143 inclusive.
        // Exclude all notes from that track before and after this passage.
        if (!timeProfile || (barIndex >= 93 && barIndex <= 142))
        for(const voice of bar.voices||[])
          for(const beat of voice.beats||[]) {
            const start=Number(beat.absolutePlaybackStart);
            if(!Number.isFinite(start))continue;
            for(const note of beat.notes||[]) {
              if(!Number.isFinite(note.string)||!Number.isFinite(note.fret)||note.string<1||note.fret<0)continue;
              const position=timeProfile?timeNotePosition(note):{string:note.string,fret:note.fret};
              if(position)events.push({start,position});
            }
          }
    if(!events.length)return [];
    const seen=new Set();
    return events.map(e=>e.position).filter(p=>{
        const key=p.string+':'+p.fret;
        if(seen.has(key))return false;
        seen.add(key);return true;
      });
  }

  // Chords are derived from timed bass and accompaniment events in the
  // loaded score, never inferred from the melody's interval annotations.
  function collectTimedHarmony(selectedTrack) {
    if (!score) return [];
    // Fixed solo passage for the original Time score: measures 94–143.
    // Analyze actual sounding harmony; no individual bass attack creates a change.
    const firstBar = timeProfile ? 93 : 0;
    const lastBar = timeProfile ? 142 : Infinity;
    const measures = new Map();
    const ensure = (i, start) => {
      if (!measures.has(i)) measures.set(i, {start, end:start, bass:[], harmony:[], melody:[]});
      const m = measures.get(i);
      m.start = Math.min(m.start, start);
      return m;
    };
    for (const track of score.tracks) {
      const name = (track.name || '').toLowerCase();
      const isBass = /bass/.test(name) && !/synthesizer|bass drum/.test(name);
      const isHarmony = /rhythm guitar|organ|piano|keyboard|electric piano/.test(name);
      const isSolo = track.index === selectedTrack.index;
      if (!isBass && !isHarmony && !isSolo) continue;
      for (const staff of track.staves || [])
        for (const [i, bar] of (staff.bars || []).entries()) {
          if (i < firstBar || i > lastBar) continue;
          for (const voice of bar.voices || [])
            for (const beat of voice.beats || []) {
              const start = Number(beat.absolutePlaybackStart);
              const dur = Number(beat.playbackDuration);
              if (!Number.isFinite(start) || !Number.isFinite(dur) || dur <= 0) continue;
              const m = ensure(i, start);
              m.end = Math.max(m.end, start + dur);
              for (const note of beat.notes || []) {
                const midi = Number(note.realValue);
                if (!Number.isFinite(midi)) continue;
                const event = {pitch:midi-(timeProfile?2:0),start,end:start+dur};
                if (isBass) m.bass.push(event);
                if (isHarmony) m.harmony.push(event);
                if (isSolo) {
                  const position = timeProfile ? timeNotePosition(note) : {string:note.string,fret:note.fret};
                  if (position) m.melody.push({...event, position});
                }
              }
            }
        }
    }
    const bars = [...measures].sort((a,b)=>a[0]-b[0]).map(x=>x[1]);
    if (!bars.length) return [];
    // Two-measure harmonic windows suppress transient bass fills and passing tones.
    // Dynamic programming favors an unchanged chord unless the combined tracks
    // provide sustained evidence for a different triad.
    const windows = [];
    for (let i=0;i<bars.length;i+=2) {
      const subset=bars.slice(i,i+2);
      windows.push({
        start:subset[0].start,
        end:subset[subset.length-1].end,
        bass:subset.flatMap(b=>b.bass),
        harmony:subset.flatMap(b=>b.harmony),
        melody:subset.flatMap(b=>b.melody)
      });
    }
    const pc=p=>((p%12)+12)%12;
    const candidates = [ // E Aeolian, after the player's F#m -> Em transposition.
      {root:4,quality:'minor'}, {root:6,quality:'diminished'},
      {root:7,quality:'major'}, {root:9,quality:'minor'},
      {root:11,quality:'minor'}, {root:0,quality:'major'},
      {root:2,quality:'major'}
    ];
    function evaluate(win,chord) {
      const r=chord.root;
      const third=pc(r+(chord.quality==='major'?4:3));
      const fifth=pc(r+(chord.quality==='diminished'?6:7));
      const tones=new Set([r,third,fifth]);
      const scoreEvents=(events,weight) => {
        let total=0,good=0;
        for (const e of events) {
          const duration=Math.max(0,Math.min(win.end,e.end)-Math.max(win.start,e.start));
          if(!duration)continue;
          const w=weight*duration;
          total+=w;
          if (tones.has(pc(e.pitch))) good+=w;
          else if (pc(e.pitch)===pc(r+2)||pc(e.pitch)===pc(r+5)) good+=0.12*w;
        }
        return total?good/total:0;
      };
      const harmonic=scoreEvents(win.harmony,1);
      const bass=scoreEvents(win.bass,1);
      const melody=scoreEvents(win.melody,1);
      // Harmonic backing dominates; bass and solo are supporting context.
      return 7*harmonic+1.5*bass+0.6*melody;
    }
    const transitionPenalty=1.55;
    const dp=[], back=[];
    for(let i=0;i<windows.length;i++) {
      dp[i]=[];back[i]=[];
      for(let c=0;c<candidates.length;c++) {
        const evidence=evaluate(windows[i],candidates[c]);
        if(i===0){dp[i][c]=evidence;back[i][c]=-1;continue;}
        let best=-Infinity,previous=0;
        for(let p=0;p<candidates.length;p++) {
          const value=dp[i-1][p]-(p===c?0:transitionPenalty);
          if(value>best){best=value;previous=p;}
        }
        dp[i][c]=best+evidence;
        back[i][c]=previous;
      }
    }
    let state=dp.at(-1).indexOf(Math.max(...dp.at(-1)));
    const sequence=Array(windows.length);
    for(let i=windows.length-1;i>=0;i--){sequence[i]=state;state=back[i][state];}
    const sections=[];
    windows.forEach((win,i)=>{
      const chord=candidates[sequence[i]];
      const prev=sections.at(-1);
      const positions=win.melody.map(e=>e.position);
      if(prev&&prev.root===chord.root&&prev.quality===chord.quality){
        prev.end=win.end;prev.positions.push(...positions);
      } else sections.push({start:win.start,end:win.end,...chord,positions:[...positions]});
    });
    return sections;
  }

  function applySelectedTrack() {
    const track =
      getSelectedTrack();

    if (
      !track ||
      !alphaTabApi
    ) {
      return;
    }

    alphaTabApi.stop();
    stopBendAnimation();
    activeNotes = [];
    clearActiveNotes();
    resetProgress();

    /*
      Rendering only this track also makes it the playback focus.
    */
    alphaTabApi.renderTracks(
      [track]
    );
    applySongPitch(alphaTabApi, score, timeProfile);
    applyPlaybackSpeed();

    onTrackChanged?.({
      timeProfile,
      index:
        track.index,
      name:
        track.name,
      placeholderPositions: collectTrackPositions(track),
      chordSections: collectTimedHarmony(track),
      tuningHighToLow:
        timeProfile ? [...TIME_SOLO_DROP_E_TUNING].reverse() : getTrackStringTuning(track)
    });

    setStatus(
      track.name
    );
  }

  async function ensureApi() {
    if (alphaTabApi) {
      return alphaTabApi;
    }

    setStatus(
      'Loading alphaTab…'
    );

    const alphaTab =
      await loadAlphaTab();

    alphaTabApi =
      new alphaTab.AlphaTabApi(
        surface,
        {
          core: {
            scriptFile:
              ALPHATAB_SCRIPT,
            fontDirectory:
              ALPHATAB_FONT_DIRECTORY
          },

          player: {
            playerMode:
              'enabledSynthesizer',
            outputMode:
              'webAudioScriptProcessor',
            soundFont:
              ALPHATAB_SOUNDFONT,
            enableCursor:
              false,
            enableAnimatedBeatCursor:
              false,
            enableElementHighlighting:
              false,
            enableUserInteraction:
              false,
            scrollMode:
              'off'
          }
        }
      );

    applyPlaybackSpeed();

    alphaTabApi.error.on(
      error => {
        console.error(
          'alphaTab error:',
          error
        );

        setStatus(
          'alphaTab error: ' +
          (
            error?.message ||
            String(error)
          )
        );
      }
    );

    alphaTabApi.scoreLoaded.on(
      loadedScore => {
        score =
          loadedScore;

        playing =
          false;

        resetProgress();

        trackSelect.innerHTML =
          '';

        loadedScore.tracks
          .forEach(
            track => {
              const option =
                document.createElement(
                  'option'
                );

              option.value =
                String(
                  track.index
                );

              option.textContent =
                track.name ||
                (
                  'Track ' +
                  (
                    track.index +
                    1
                  )
                );

              trackSelect.appendChild(
                option
              );
            }
          );

        trackSelect.disabled =
          loadedScore
            .tracks
            .length === 0;

        const preferred =
          loadedScore
            .tracks
            .find(
              track =>
                /guitar\s+solo/i
                  .test(
                    track.name ||
                    ''
                  )
            ) ||
          loadedScore
            .tracks
            .find(
              track =>
                getTrackStringTuning(
                  track
                ).length > 0
            ) ||
          loadedScore
            .tracks[0];

        selectedTrackIndex =
          preferred
            ? preferred.index
            : null;

        if (
          selectedTrackIndex !==
            null
        ) {
          trackSelect.value =
            String(
              selectedTrackIndex
            );

          applySelectedTrack();
        }

        onScoreLoaded?.({
          title:
            loadedScore.title ||
            '',
          artist:
            loadedScore.artist ||
            '',
          trackCount:
            loadedScore
              .tracks
              .length
        });

        applyPlaybackSpeed();
        updateTransport();
      }
    );

    alphaTabApi.playerReady.on(
      () => {
        playerReady =
          true;
        if (score) applySongPitch(alphaTabApi, score, timeProfile);
        applyPlaybackSpeed();
        updateTransport();

        const track =
          getSelectedTrack();

        if (track) {
          setStatus(
            track.name
          );
        }
      }
    );

    alphaTabApi.playerStateChanged.on(
      args => {
        playing =
          args.state === 1;

        if (playing) {
          startBendAnimation();
        } else {
          stopBendAnimation();
        }

        updateTransport();
      }
    );

    alphaTabApi.playerPositionChanged.on(
      args => {
        endTimeMs =
          Math.max(
            0,
            Number(
              args.endTime ||
              0
            )
          );

        currentTick =
          Number(
            args.currentTick ||
            currentTick
          );

        onPositionChanged?.({fraction: endTimeMs > 0 ? Number(args.currentTime || 0) / endTimeMs : 0, tick: currentTick});

        const nowMs =
          Math.max(
            0,
            Number(
              args.currentTime ||
              0
            )
          );

        emitActiveNotes(
          currentTick
        );

        currentTime.textContent =
          formatTime(
            nowMs
          );

        duration.textContent =
          formatTime(
            endTimeMs
          );

        if (
          !scrubbing &&
          endTimeMs > 0
        ) {
          progress.value =
            String(
              Math.max(
                0,
                Math.min(
                  1000,
                  Math.round(
                    nowMs /
                    endTimeMs *
                    1000
                  )
                )
              )
            );
        }

        updateTransport();
      }
    );

    alphaTabApi.playerFinished.on(
      () => {
        playing =
          false;

        stopBendAnimation();
        activeNotes = [];
        clearActiveNotes();
        updateTransport();
      }
    );

    alphaTabApi.activeBeatsChanged.on(
      args => {
        if (
          selectedTrackIndex ===
            null
        ) {
          clearActiveNotes();
          return;
        }

        const notes =
          [];

        for (
          const beat of
            args.activeBeats ||
            []
        ) {
          const trackIndex =
            beat
              ?.voice
              ?.bar
              ?.staff
              ?.track
              ?.index;

          if (
            trackIndex !==
              selectedTrackIndex
          ) {
            continue;
          }

          for (
            const note of
              beat.notes ||
              []
          ) {
            if (
              Number.isFinite(
                note.string
              ) &&
              Number.isFinite(
                note.fret
              ) &&
              note.string > 0
            ) {
              const position = timeProfile ? timeNotePosition(note) : { string: note.string, fret: note.fret };
              if (position) notes.push({ ...position, note });
            }
          }
        }

        activeNotes =
          notes;

        emitActiveNotes(
          currentTick
        );
      }
    );

    return alphaTabApi;
  }

  fileInput.addEventListener(
    'change',
    async () => {
      const file =
        fileInput.files?.[0];

      if (!file) {
        return;
      }

      try {
        const api =
          await ensureApi();

        setStatus(
          'Loading ' +
          file.name +
          '…'
        );

        stopBendAnimation();
        activeNotes = [];
        clearActiveNotes();

        const buffer =
          await file.arrayBuffer();

        api.settings
          .importer
          .encoding =
            /\.(gp3|gp4|gp5)$/i
              .test(file.name)
              ? 'windows-1252'
              : 'utf-8';

        api.updateSettings();
        timeProfile = isTimeFile(file.name);
        api.load(
          buffer
        );
      } catch (error) {
        console.error(
          'Song Player load error:',
          error
        );

        setStatus(
          'Load failed: ' +
          (
            error?.message ||
            String(error)
          )
        );
      }
    }
  );

  trackSelect.addEventListener(
    'change',
    () => {
      const value =
        Number(
          trackSelect.value
        );

      if (
        !Number.isInteger(
          value
        )
      ) {
        return;
      }

      selectedTrackIndex =
        value;

      applySelectedTrack();
      updateTransport();
    }
  );

  playPauseButton.addEventListener(
    'click',
    async () => {
      try {
        const api =
          await ensureApi();

        applyPlaybackSpeed();
        api.playPause();
      } catch (error) {
        setStatus(
          'Playback failed: ' +
          (
            error?.message ||
            String(error)
          )
        );
      }
    }
  );

  speedSelect.addEventListener('change', applyPlaybackSpeed);
  speedSelect.addEventListener('input', applyPlaybackSpeed);

  stopButton.addEventListener(
    'click',
    () => {
      alphaTabApi?.stop();
      stopBendAnimation();
      activeNotes = [];
      clearActiveNotes();
    }
  );

  const seekFromProgress =
    () => {
      if (
        !alphaTabApi ||
        endTimeMs <= 0
      ) {
        return;
      }

      const fraction =
        Math.max(
          0,
          Math.min(
            1,
            Number(
              progress.value
            ) /
            1000
          )
        );

      const targetMs =
        fraction *
        endTimeMs;

      currentTime.textContent =
        formatTime(
          targetMs
        );

      alphaTabApi.timePosition =
        targetMs;
    };

  progress.addEventListener(
    'pointerdown',
    () => {
      scrubbing =
        true;
    }
  );

  progress.addEventListener(
    'input',
    seekFromProgress
  );

  progress.addEventListener(
    'change',
    () => {
      seekFromProgress();
      scrubbing =
        false;
    }
  );

  window.addEventListener(
    'pointerup',
    () => {
      scrubbing =
        false;
    }
  );

  resetProgress();
  updateTransport();
}
