var app = angular.module("myApp", []);

app.controller("MyRngCtrl", function ($scope, $timeout) {
  var VF = Vex.Flow;

  /*
   * Complete selectable range:
   *
   * C2 = MIDI 36
   * G5 = MIDI 79
   *
   * Clef division:
   *
   * Bass:   C2-B3
   * Treble: C4-G5
   */
  var ABSOLUTE_MIDI_MIN = 36;
  var ABSOLUTE_MIDI_MAX = 79;
  var TREBLE_START = 60; // C4

  var NATURAL_PITCH_CLASSES = [
    0,  // C
    2,  // D
    4,  // E
    5,  // F
    7,  // G
    9,  // A
    11  // B
  ];

  var ACCIDENTAL_PITCH_CLASSES = [
    1,  // C#
    3,  // D#
    6,  // F#
    8,  // G#
    10  // A#
  ];

  var currentMidiNote = null;
  var noteColor = "#111111";
  $scope.answerVisible = false;
  $scope.answerAvailable = false;
  $scope.answerLabel = "";

  $scope.toggleAnswer = function () {
    if (currentMidiNote === null) return;
    $scope.answerLabel = midiToDisplayName(currentMidiNote);
    $scope.answerVisible = !$scope.answerVisible;
  };

  var midiAccess = null;
  var connectedInputCount = 0;
  $scope.midiConnected = false;

  var feedbackLocked = false;
  var feedbackTimer = null;

  /*
   * Default filters.
   */
$scope.clefFilter = "treble";
$scope.noteFilter = "natural";

$scope.absoluteMidiMin = ABSOLUTE_MIDI_MIN;
$scope.absoluteMidiMax = ABSOLUTE_MIDI_MAX;

$scope.rangeMin = 60; // C4
$scope.rangeMax = 72; // C5

  $scope.absoluteMinLabel = midiToDisplayName(
    ABSOLUTE_MIDI_MIN
  );

  $scope.absoluteMaxLabel = midiToDisplayName(
    ABSOLUTE_MIDI_MAX
  );

  $scope.rangeMinLabel = "";
  $scope.rangeMaxLabel = "";

  $scope.rangeSelectionStyle = {
    left: "0%",
    width: "100%"
  };

  $scope.midiAccessGranted = false;
  $scope.status =
    "Enable MIDI, then play the displayed note.";

  $scope.statusType = "";

  /*
   * The lower slider cannot move above the upper slider.
   */
  $scope.onRangeMinChange = function () {
    $scope.rangeMin = Number($scope.rangeMin);
    $scope.rangeMax = Number($scope.rangeMax);

    if ($scope.rangeMin > $scope.rangeMax) {
      $scope.rangeMin = $scope.rangeMax;
    }

    updateRangeDisplay();
    $scope.applyFilters();
  };

  /*
   * The upper slider cannot move below the lower slider.
   */
  $scope.onRangeMaxChange = function () {
    $scope.rangeMin = Number($scope.rangeMin);
    $scope.rangeMax = Number($scope.rangeMax);

    if ($scope.rangeMax < $scope.rangeMin) {
      $scope.rangeMax = $scope.rangeMin;
    }

    updateRangeDisplay();
    $scope.applyFilters();
  };

  /*
   * Cancel current feedback and select a note using all
   * active filters.
   */
  $scope.applyFilters = function () {
    if (feedbackTimer) {
      $timeout.cancel(feedbackTimer);
      feedbackTimer = null;
    }

    feedbackLocked = false;
    noteColor = "#111111";

    var noteWasSelected = selectNewNote();

    if (!noteWasSelected) {
      $scope.status =
        "No notes match the current filters.";

      $scope.statusType = "error";
      return;
    }

    if (
      $scope.midiAccessGranted &&
      connectedInputCount > 0
    ) {
      $scope.status = "Play the new note.";
      $scope.statusType = "";
    } else if ($scope.midiAccessGranted) {
      $scope.status =
        "MIDI access enabled, but no MIDI input is connected.";

      $scope.statusType = "error";
    } else {
      $scope.status =
        "Enable MIDI, then play the displayed note.";

      $scope.statusType = "";
    }
  };

  /*
   * Update the text and highlighted portion of the
   * dual-handle range slider.
   */
  function updateRangeDisplay() {
    var totalRange =
      ABSOLUTE_MIDI_MAX - ABSOLUTE_MIDI_MIN;

    var minimumPercent =
      (($scope.rangeMin - ABSOLUTE_MIDI_MIN) /
        totalRange) *
      100;

    var maximumPercent =
      (($scope.rangeMax - ABSOLUTE_MIDI_MIN) /
        totalRange) *
      100;

    $scope.rangeMinLabel = midiToDisplayName(
      $scope.rangeMin
    );

    $scope.rangeMaxLabel = midiToDisplayName(
      $scope.rangeMax
    );

    $scope.rangeSelectionStyle = {
      left: minimumPercent + "%",
      width:
        maximumPercent - minimumPercent + "%"
    };
  }

  /*
   * Return every MIDI note allowed by all active filters.
   */
  function getFilteredMidiNotes() {
    var filteredNotes = [];

    var minimum = Number($scope.rangeMin);
    var maximum = Number($scope.rangeMax);

    for (
      var midiNote = minimum;
      midiNote <= maximum;
      midiNote++
    ) {
      if (
        noteMatchesClefFilter(midiNote) &&
        noteMatchesTypeFilter(midiNote)
      ) {
        filteredNotes.push(midiNote);
      }
    }

    return filteredNotes;
  }

  /*
   * Check whether the note belongs to the selected clef.
   */
  function noteMatchesClefFilter(midiNote) {
    if ($scope.clefFilter === "treble") {
      return midiNote >= TREBLE_START;
    }

    if ($scope.clefFilter === "bass") {
      return midiNote < TREBLE_START;
    }

    return true;
  }

  /*
   * Check whether the note is natural or accidental.
   */
  function noteMatchesTypeFilter(midiNote) {
    var pitchClass = midiNote % 12;

    if ($scope.noteFilter === "natural") {
      return (
        NATURAL_PITCH_CLASSES.indexOf(
          pitchClass
        ) !== -1
      );
    }

    if ($scope.noteFilter === "accidental") {
      return (
        ACCIDENTAL_PITCH_CLASSES.indexOf(
          pitchClass
        ) !== -1
      );
    }

    return true;
  }

  /*
   * Request browser access to connected MIDI devices.
   */
  $scope.enableMIDI = function () {
    if (!navigator.requestMIDIAccess) {
      $scope.status =
        "This browser does not support Web MIDI.";

      $scope.statusType = "error";
      return;
    }

    $scope.status = "Requesting MIDI access...";
    $scope.statusType = "";
    var midiStage = "access";

    navigator
      .requestMIDIAccess({
        sysex: false
      })
      .then(function (access) {
        midiStage = "setup";
        midiAccess = access;

        midiAccess.onstatechange =
          refreshMidiInputs;

        refreshMidiInputs();

        $scope.$evalAsync(function () {
          $scope.midiAccessGranted = true;
        });
      })
      .catch(function (error) {
        var failure = window.PracticeMIDI?.reportFailure?.(error, midiStage) ||
          "MIDI " + midiStage + " failed: " + (error?.message || error);
        $scope.$evalAsync(function () {
          $scope.midiConnected = false;
          $scope.midiAccessGranted = false;

          $scope.status = failure;

          $scope.statusType = "error";
        });
      });
  };

  /*
   * Attach a listener to every connected MIDI input.
   */
  function refreshMidiInputs() {
    if (!midiAccess) {
      return;
    }

    var inputs = Array.from(
      midiAccess.inputs.values()
    );


    connectedInputCount = 0;

    inputs.forEach(function (input) {
      input.onmidimessage = handleMidiMessage;

      if (input.state !== "disconnected") {
        connectedInputCount++;
      }
    });

    $scope.$evalAsync(function () {
      $scope.midiAccessGranted = true;
      $scope.midiConnected = connectedInputCount > 0;

      if (connectedInputCount > 0) {
        if (window.PracticeMIDI) {
          window.PracticeMIDI.setEnabled(true);
        }

        $scope.status =
          connectedInputCount === 1
            ? "MIDI input connected. Play the displayed note."
            : connectedInputCount +
              " MIDI inputs connected. Play the displayed note.";

        $scope.statusType = "";
      } else {
        $scope.status =
          "MIDI access enabled, but no MIDI input is connected.";

        $scope.statusType = "error";
      }
    });
  }

  /*
   * Receive messages from the MIDI keyboard.
   */
  function handleMidiMessage(event) {
    var statusByte = event.data[0];
    var playedMidiNote = event.data[1];
    var velocity = event.data[2];

    var command = statusByte & 0xf0;


    /*
     * Accept note-on messages only.
     *
     * A note-on event with velocity 0 is treated
     * as a note-off event.
     */
    if (command !== 0x90 || velocity === 0) {
      return;
    }

    if (
      feedbackLocked ||
      currentMidiNote === null
    ) {
      return;
    }

    $scope.$evalAsync(function () {
      gradeMidiNote(playedMidiNote);
    });
  }

  /*
   * Compare the played note with the displayed note.
   */
  function gradeMidiNote(playedMidiNote) {
    if (
      feedbackLocked ||
      currentMidiNote === null
    ) {
      return;
    }

    feedbackLocked = true;

    if (feedbackTimer) {
      $timeout.cancel(feedbackTimer);
    }

    if (playedMidiNote === currentMidiNote) {
      noteColor = "#16a34a";

      $scope.status = "Correct";
      $scope.statusType = "correct";

      renderCurrentNote();

      feedbackTimer = $timeout(function () {
        noteColor = "#111111";

        var noteWasSelected =
          selectNewNote();

        feedbackLocked = false;

        if (noteWasSelected) {
          $scope.status =
            "Play the new note.";

          $scope.statusType = "";
        } else {
          $scope.status =
            "No notes match the current filters.";

          $scope.statusType = "error";
        }
      }, 500);
    } else {
      noteColor = "#dc2626";

      $scope.status = "Wrong — try again.";
      $scope.statusType = "incorrect";

      renderCurrentNote();

      feedbackTimer = $timeout(function () {
        noteColor = "#111111";

        renderCurrentNote();

        feedbackLocked = false;

        $scope.status = "Try again.";
        $scope.statusType = "";
      }, 350);
    }
  }

  /*
   * Select a random note allowed by every filter.
   *
   * The previous note is excluded when more than
   * one valid choice exists.
   */
  function selectNewNote() {
    var validNotes = getFilteredMidiNotes();

    if (validNotes.length === 0) {
      currentMidiNote = null;
      $scope.answerVisible = false;
      $scope.answerAvailable = false;
      $scope.answerLabel = "";
      clearStaff();

      return false;
    }

    var choices = validNotes.filter(
      function (midiNote) {
        return midiNote !== currentMidiNote;
      }
    );

    if (choices.length === 0) {
      choices = validNotes;
    }

    var randomIndex = Math.floor(
      Math.random() * choices.length
    );

    currentMidiNote = choices[randomIndex];
    $scope.answerVisible = false;
    $scope.answerAvailable = true;
    $scope.answerLabel = midiToDisplayName(currentMidiNote);

    renderCurrentNote();

    return true;
  }

  /*
   * Convert a MIDI note number to a readable label.
   *
   * Examples:
   *
   * 36 -> C2
   * 61 -> C#4
   */
  function midiToDisplayName(midiNote) {
    var noteNames = [
      "C",
      "C♯",
      "D",
      "D♯",
      "E",
      "F",
      "F♯",
      "G",
      "G♯",
      "A",
      "A♯",
      "B"
    ];

    midiNote = Number(midiNote);

    var noteName =
      noteNames[midiNote % 12];

    var octave =
      Math.floor(midiNote / 12) - 1;

    return noteName + octave;
  }

  /*
   * Convert a MIDI note number to VexFlow notation.
   */
  function midiToVexFlowNote(midiNote) {
    var noteNames = [
      "C",
      "C#",
      "D",
      "D#",
      "E",
      "F",
      "F#",
      "G",
      "G#",
      "A",
      "A#",
      "B"
    ];

    var noteName =
      noteNames[midiNote % 12];

    var octave =
      Math.floor(midiNote / 12) - 1;

    return noteName + octave;
  }

  /*
   * Invisible whole-note voice used to align both staves.
   */
  function createGhostVoice() {
    var voice = new VF.Voice({
      num_beats: 4,
      beat_value: 4
    });

    voice.addTickables([
      new VF.GhostNote({
        duration: "w"
      })
    ]);

    return voice;
  }

  /*
   * Remove the existing rendered staff.
   */
  function clearStaff() {
    var staffElement =
      document.getElementById("staff");

    if (staffElement) {
      staffElement.innerHTML = "";
    }
  }

  /*
   * Draw the selected note on the appropriate staff.
   */
  function renderCurrentNote() {
    if (currentMidiNote === null) {
      clearStaff();
      return;
    }

    var staffElement =
      document.getElementById("staff");

    staffElement.innerHTML = "";

    var vf = new VF.Factory({
      renderer: {
        elementId: "staff",
        width: 500,
        height: 250
      }
    });

    var score = vf.EasyScore();
    var system = vf.System();

    var vexFlowNote =
      midiToVexFlowNote(currentMidiNote);

    var isTreble =
      currentMidiNote >= TREBLE_START;

    var trebleVoice;
    var bassVoice;
    var visibleNotes;

    if (isTreble) {
      visibleNotes = score.notes(
        vexFlowNote + "/w",
        {
          stem: "up"
        }
      );

      visibleNotes[0].setStyle({
        fillStyle: noteColor,
        strokeStyle: noteColor
      });

      trebleVoice =
        score.voice(visibleNotes);

      bassVoice =
        createGhostVoice();
    } else {
      visibleNotes = score.notes(
        vexFlowNote + "/w",
        {
          clef: "bass",
          stem: "up"
        }
      );

      visibleNotes[0].setStyle({
        fillStyle: noteColor,
        strokeStyle: noteColor
      });

      trebleVoice =
        createGhostVoice();

      bassVoice =
        score.voice(visibleNotes);
    }

    system
      .addStave({
        voices: [trebleVoice]
      })
      .addClef("treble")
      .addTimeSignature("4/4");

    system
      .addStave({
        voices: [bassVoice]
      })
      .addClef("bass")
      .addTimeSignature("4/4");

    system.addConnector();

    vf.draw();

    var svg =
      staffElement.querySelector("svg");

    if (svg) {
      svg.setAttribute(
        "viewBox",
        "0 0 500 250"
      );

      svg.setAttribute(
        "preserveAspectRatio",
        "xMidYMid meet"
      );
    }
  }

  updateRangeDisplay();
  selectNewNote();

  if (window.PracticeMIDI && window.PracticeMIDI.isEnabled()) {
    $timeout(function () {
      $scope.enableMIDI();
    }, 0);
  }
});
