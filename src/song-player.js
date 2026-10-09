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
    clearActiveNotes();

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

        onActiveNotes?.(
          notes
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

  stopButton.addEventListener(
    'click',
    () => {
      alphaTabApi?.stop();
      clearActiveNotes();
    }
  );

  updateTransport();
}
