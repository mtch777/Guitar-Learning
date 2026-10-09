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

const BUILT_IN_TIME_FILE =
  'songs/time-solo-track.gp';

const TIME_SOLO_START_MS =
  3 * 60 * 1000 +
  2 * 1000;

const TIME_SOLO_END_MS =
  4 * 60 * 1000 +
  28 * 1000;

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
  let builtInLoadStarted = false;
  let sectionResolving = false;
  let sectionStartTick = null;
  let sectionEndTick = null;
  let currentTick = 0;
  let currentTimeMs = 0;
  let activeBeatNotes = [];
  let visualFrame = null;
  let pendingSeekCapture = null;

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
      currentTime.textContent =
        formatTime(
          TIME_SOLO_START_MS
        );
      duration.textContent =
        formatTime(
          TIME_SOLO_END_MS
        );
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
      const initial =
        Number(
          note?.initialBendValue ||
          0
        );

      return initial / 2;
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

    const relative =
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

    const offset =
      relative * 60;

    const sorted =
      [...points].sort(
        (a, b) =>
          Number(a.offset) -
          Number(b.offset)
      );

    if (
      offset <=
      Number(
        sorted[0].offset
      )
    ) {
      return (
        Number(
          sorted[0].value
        ) /
        2
      );
    }

    for (
      let index = 1;
      index <
        sorted.length;
      index++
    ) {
      const left =
        sorted[index - 1];

      const right =
        sorted[index];

      const rightOffset =
        Number(
          right.offset
        );

      if (
        offset <=
        rightOffset
      ) {
        const leftOffset =
          Number(
            left.offset
          );

        const span =
          Math.max(
            0.0001,
            rightOffset -
            leftOffset
          );

        const amount =
          (
            offset -
            leftOffset
          ) /
          span;

        const value =
          Number(
            left.value
          ) +
          (
            Number(
              right.value
            ) -
            Number(
              left.value
            )
          ) *
          amount;

        return value / 2;
      }
    }

    return (
      Number(
        sorted[
          sorted.length - 1
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
      activeBeatNotes.map(
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

  function stopVisualLoop() {
    if (
      visualFrame !==
        null
    ) {
      cancelAnimationFrame(
        visualFrame
      );
    }

    visualFrame = null;
  }

  function startVisualLoop() {
    stopVisualLoop();

    const draw =
      () => {
        if (
          !playing ||
          !alphaTabApi
        ) {
          visualFrame =
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

        visualFrame =
          requestAnimationFrame(
            draw
          );
      };

    visualFrame =
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
        !sectionResolving &&
        Number.isFinite(
          sectionStartTick
        ) &&
        Number.isFinite(
          sectionEndTick
        ) &&
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
    stopVisualLoop();
    activeBeatNotes = [];
    clearActiveNotes();
    resetProgress();
    sectionStartTick = null;
    sectionEndTick = null;

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
        sectionStartTick = null;
        sectionEndTick = null;
        activeBeatNotes = [];

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
      async () => {
        playerReady =
          true;

        const track =
          getSelectedTrack();

        if (track) {
          setStatus(
            'Preparing 3:02–4:28…'
          );

          try {
            await resolveSoloSectionTicks();

            setStatus(
              track.name +
              ' · 3:02–4:28'
            );
          } catch (error) {
            console.error(
              'Could not resolve solo section:',
              error
            );

            setStatus(
              'Could not prepare 3:02–4:28'
            );
          }
        }

        updateTransport();
      }
    );

    alphaTabApi.playerStateChanged.on(
      args => {
        playing =
          args.state === 1;

        if (playing) {
          startVisualLoop();
        } else {
          stopVisualLoop();
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
            0
          );

        currentTimeMs =
          Math.max(
            0,
            Number(
              args.currentTime ||
              0
            )
          );

        if (
          pendingSeekCapture &&
          args.isSeek
        ) {
          const capture =
            pendingSeekCapture;

          pendingSeekCapture =
            null;

          capture.resolve({
            tick:
              currentTick,
            time:
              currentTimeMs
          });
        }

        if (
          Number.isFinite(
            sectionStartTick
          ) &&
          Number.isFinite(
            sectionEndTick
          )
        ) {
          if (
            playing &&
            currentTick >=
              sectionEndTick
          ) {
            alphaTabApi.pause();
            alphaTabApi.tickPosition =
              sectionStartTick;

            currentTick =
              sectionStartTick;

            activeBeatNotes = [];
            clearActiveNotes();
          }

          if (!scrubbing) {
            const sectionSpan =
              Math.max(
                1,
                sectionEndTick -
                sectionStartTick
              );

            progress.value =
              String(
                Math.max(
                  0,
                  Math.min(
                    1000,
                    Math.round(
                      (
                        currentTick -
                        sectionStartTick
                      ) /
                      sectionSpan *
                      1000
                    )
                  )
                )
              );
          }
        }

        currentTime.textContent =
          formatTime(
            Math.max(
              TIME_SOLO_START_MS,
              Math.min(
                TIME_SOLO_END_MS,
                currentTimeMs
              )
            )
          );

        duration.textContent =
          formatTime(
            TIME_SOLO_END_MS
          );

        emitActiveNotes(
          currentTick
        );

        updateTransport();
      }
    );

    alphaTabApi.playerFinished.on(
      () => {
        playing =
          false;

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

        activeBeatNotes =
          notes;

        emitActiveNotes(
          currentTick
        );
      }
    );

    return alphaTabApi;
  }

  function captureTickAtTime(
    milliseconds
  ) {
    return new Promise(
      (
        resolve,
        reject
      ) => {
        if (!alphaTabApi) {
          reject(
            new Error(
              'alphaTab is not ready.'
            )
          );
          return;
        }

        const timeout =
          setTimeout(
            () => {
              if (
                pendingSeekCapture
              ) {
                pendingSeekCapture =
                  null;
              }

              reject(
                new Error(
                  'Seek did not resolve.'
                )
              );
            },
            3000
          );

        pendingSeekCapture = {
          resolve:
            value => {
              clearTimeout(
                timeout
              );

              resolve(
                value
              );
            }
        };

        alphaTabApi.timePosition =
          milliseconds;
      }
    );
  }

  async function resolveSoloSectionTicks() {
    if (
      sectionResolving ||
      !alphaTabApi ||
      !score
    ) {
      return;
    }

    sectionResolving =
      true;

    updateTransport();

    try {
      alphaTabApi.pause();

      const start =
        await captureTickAtTime(
          TIME_SOLO_START_MS
        );

      const end =
        await captureTickAtTime(
          TIME_SOLO_END_MS
        );

      sectionStartTick =
        Math.min(
          start.tick,
          end.tick
        );

      sectionEndTick =
        Math.max(
          start.tick,
          end.tick
        );

      alphaTabApi.tickPosition =
        sectionStartTick;

      currentTick =
        sectionStartTick;

      progress.value =
        '0';

      currentTime.textContent =
        formatTime(
          TIME_SOLO_START_MS
        );

      duration.textContent =
        formatTime(
          TIME_SOLO_END_MS
        );
    } finally {
      sectionResolving =
        false;

      updateTransport();
    }
  }

  async function loadBuffer(
    buffer,
    filename
  ) {
    const api =
      await ensureApi();

    setStatus(
      'Loading ' +
      filename +
      '…'
    );

    activeBeatNotes = [];
    clearActiveNotes();

    api.settings
      .importer
      .encoding =
        /\.(gp3|gp4|gp5)$/i
          .test(filename)
          ? 'windows-1252'
          : 'utf-8';

    api.updateSettings();
    api.load(
      buffer
    );
  }

  async function loadBuiltInTime() {
    if (
      builtInLoadStarted ||
      score
    ) {
      return;
    }

    builtInLoadStarted =
      true;

    try {
      setStatus(
        'Loading saved Time GP…'
      );

      const baseUrl =
        import.meta.env.BASE_URL;

      const response =
        await fetch(
          baseUrl +
          BUILT_IN_TIME_FILE
        );

      if (!response.ok) {
        throw new Error(
          'Saved Time GP was not found.'
        );
      }

      const buffer =
        await response.arrayBuffer();

      await loadBuffer(
        buffer,
        'time-solo-track.gp'
      );
    } catch (error) {
      builtInLoadStarted =
        false;

      console.error(
        'Saved Time GP load error:',
        error
      );

      setStatus(
        'Saved Time GP failed to load'
      );
    }
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
        const buffer =
          await file.arrayBuffer();

        await loadBuffer(
          buffer,
          file.name
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

        if (
          Number.isFinite(
            sectionStartTick
          ) &&
          Number.isFinite(
            sectionEndTick
          )
        ) {
          const tick =
            Number(
              api.tickPosition ||
              0
            );

          if (
            tick <
              sectionStartTick ||
            tick >=
              sectionEndTick
          ) {
            api.tickPosition =
              sectionStartTick;
          }
        }

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

  stopButton.addEventListener(
    'click',
    () => {
      if (!alphaTabApi) {
        return;
      }

      alphaTabApi.pause();
      stopVisualLoop();

      if (
        Number.isFinite(
          sectionStartTick
        )
      ) {
        alphaTabApi.tickPosition =
          sectionStartTick;

        currentTick =
          sectionStartTick;
      }

      activeBeatNotes = [];
      clearActiveNotes();

      progress.value =
        '0';

      currentTime.textContent =
        formatTime(
          TIME_SOLO_START_MS
        );
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

      if (
        !Number.isFinite(
          sectionStartTick
        ) ||
        !Number.isFinite(
          sectionEndTick
        )
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

      const targetTick =
        sectionStartTick +
        (
          sectionEndTick -
          sectionStartTick
        ) *
        fraction;

      alphaTabApi.tickPosition =
        targetTick;

      currentTick =
        targetTick;
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

  const lessonSelect =
    document.getElementById(
      'lessonTypeSelect'
    );

  lessonSelect?.addEventListener(
    'change',
    () => {
      if (
        lessonSelect.value ===
          'songPlayer'
      ) {
        loadBuiltInTime();
      }
    }
  );

  if (
    lessonSelect?.value ===
      'songPlayer'
  ) {
    loadBuiltInTime();
  }

  resetProgress();
  updateTransport();
}
