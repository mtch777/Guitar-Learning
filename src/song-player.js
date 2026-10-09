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
  let selectedTrackIndex = null;
  let playerReady = false;
  let playing = false;
  let endTimeMs = 0;
  let scrubbing = false;
  let currentTick = 0;
  let activeNotes = [];
  let bendAnimationFrame = null;

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

    onTrackChanged?.({
      index:
        track.index,
      name:
        track.name,
      tuningHighToLow:
        getTrackStringTuning(
          track
        )
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

    alphaTabApi.playbackSpeed = Number(speedSelect.value);

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

        updateTransport();
      }
    );

    alphaTabApi.playerReady.on(
      () => {
        playerReady =
          true;

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
              notes.push({
                string:
                  note.string,
                fret:
                  note.fret,
                note
              });
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

  speedSelect.addEventListener(
    'change',
    () => {
      if (alphaTabApi) {
        alphaTabApi.playbackSpeed = Number(speedSelect.value);
      }
    }
  );

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
