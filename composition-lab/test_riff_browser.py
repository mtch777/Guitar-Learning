"""Regression tests for running existing riff recipes in the browser."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public/riff-builder"
RESEARCH = ROOT / "composition-lab/local-artifacts/drop-e-riffs-2026-11-04/generation-002"
FROZEN_SCORE_HASHES = {
    "conversation": (
        "fabf5fcf567cfbbbc16630d3db84561283a9bd933f8e26938b2cecbd1f28a341",
        "f048eb635e17709bb5f9d11f5a3af182f01a91f575b7c9e826a29267a736c1ae",
    ),
    "flow": (
        "22670bd9f112040082b18dad60d6ba1cd0400232c65d4813fcab0d0b5055d0ab",
        "42159ba503ec443fa4fa93aed120bceff5906df82a4cb0df9014fc6fa4a1a66e",
    ),
    "chords": (
        "c1ab3ee92524058fa08be868c58b4adabf0e23476f8997f7decae11ef26f5e50",
        "c2eeb3fffe76055e2a7e44faeb3fee1f9d968434f1b7bb5b850fb6d08377d5f2",
    ),
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


composer = load_module("riff_browser_composer", PUBLIC / "composer.py")
package = load_module("riff_browser_package", ROOT / "composition-lab/package_riff_browser.py")


class BrowserComposerTests(unittest.TestCase):
    def test_all_six_scores_equal_existing_examples(self):
        folders = {
            "conversation": "07-fracture-dialogue",
            "flow": "08-open-orbit-v2",
            "chords": "09-glass-counterweight",
        }
        for recipe, folder in folders.items():
            result = composer.generate(recipe)
            for version in ("baseline", "variation"):
                with self.subTest(recipe=recipe, version=version):
                    expected_path = RESEARCH / folder / f"{version}-score.json"
                    if expected_path.exists():
                        expected = json.loads(expected_path.read_text(encoding="utf8"))
                        self.assertEqual(result[version], expected)
                    # CI has no private research corpus. These fingerprints were
                    # computed from the independently saved earlier scores.
                    canonical = json.dumps(result[version], sort_keys=True, separators=(",", ":")).encode()
                    index = 0 if version == "baseline" else 1
                    self.assertEqual(hashlib.sha256(canonical).hexdigest(), FROZEN_SCORE_HASHES[recipe][index])

    def test_tempo_changes_clock_not_written_music(self):
        for recipe in composer.RECIPES:
            original = composer.generate(recipe)
            changed = composer.generate(recipe, 175)
            self.assertEqual(changed["tempo"], 175)
            for version in ("baseline", "variation"):
                old = original[version]
                new = changed[version]
                self.assertEqual(new["tempo"], 175)
                self.assertEqual({k: v for k, v in new.items() if k != "tempo"},
                                 {k: v for k, v in old.items() if k != "tempo"})

    def test_score_and_changes_invariants(self):
        for recipe in composer.RECIPES:
            result = composer.generate(recipe)
            self.assertTrue(result["changes"]["changed"]["pitch"])
            for version in ("baseline", "variation"):
                score = result[version]
                self.assertEqual(len(score["bars"]), 8)
                self.assertEqual(score["meter"], [4, 4])
                self.assertEqual(score["tuning_high_to_low"], [64, 59, 55, 50, 45, 40, 35, 28])
                for bar in score["bars"]:
                    self.assertEqual(sum((Fraction(*beat["duration"]) for beat in bar), Fraction()), 1)
                    for beat in bar:
                        self.assertEqual(len({n["string"] for n in beat["notes"]}), len(beat["notes"]))
                for note in score["notes"]:
                    self.assertEqual(note["pitch"], result["tuning"][note["string"]] + note["fret"])
                    self.assertGreaterEqual(note["fret"], 0)
                    self.assertLessEqual(note["fret"], 24)
                    self.assertGreater(Fraction(note["duration_q"]), 0)
            self.assertEqual(result["changes"], composer.final_differences(result["baseline"], result["variation"]))

    def test_json_is_deterministic_and_does_not_leak_mutations(self):
        first = composer.generate_json("flow", 132)
        second = composer.generate_json("flow", 132)
        self.assertEqual(first, second)
        modified = composer.generate("flow")
        modified["baseline"]["notes"][0]["fret"] = 99
        self.assertEqual(first, composer.generate_json("flow", 132))

    def test_input_validation(self):
        for tempo in (79, 201, 100.5, "140", True, {}, []):
            with self.subTest(tempo=tempo), self.assertRaises(ValueError):
                composer.generate("conversation", tempo)
        for recipe in ("other", "", None, [], {}):
            with self.subTest(recipe=recipe), self.assertRaises(ValueError):
                composer.generate(recipe)
        self.assertEqual(composer.generate("conversation", 80)["tempo"], 80)
        self.assertEqual(composer.generate("conversation", 200)["tempo"], 200)

    def test_minimal_materials_have_only_public_execution_fields(self):
        material = json.loads((PUBLIC / "materials.json").read_text(encoding="utf8"))
        self.assertEqual(set(material), {"hook", "broken_hook", "middle", "high", "flow", "open_chord", "shell"})
        for label, cell in material.items():
            self.assertEqual(set(cell), {"id", "source", "events"})
            self.assertEqual(cell["id"], label)
            self.assertEqual(cell["source"], {})
            self.assertLessEqual(len(cell["events"]), 8)
            for event in cell["events"]:
                self.assertEqual(set(event), {"relative_onset_q", "notes"})
                for note in event["notes"]:
                    self.assertEqual(set(note), {"string", "fret", "duration_q"})
        self.assertLess((PUBLIC / "materials.json").stat().st_size, 10000)

    @unittest.skipUnless((RESEARCH / "VOCABULARY.json").exists(), "Packaging audit requires private research inputs")
    def test_package_reproduces_delivered_files(self):
        for name, content in package.packaged_files().items():
            self.assertEqual((PUBLIC / name).read_text(encoding="utf8"), content)


if __name__ == "__main__":
    unittest.main()
