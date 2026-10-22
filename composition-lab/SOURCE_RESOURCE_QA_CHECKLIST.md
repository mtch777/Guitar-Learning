# Source-resource QA acceptance checklist

Scope: existing actual capture/baseline/supplement bytes only. No engine, source
conversion, music interpretation, inferred alignment or model execution.

- [x] Reusable pure reporting function over caller-supplied existing paths; no
  network/global resource paths and no mutation of source/configuration.
- [x] Compute original file set and SHA256s against separately retained baseline;
  ignore asserted preservation/alignment booleans in inventory reports.
- [x] Strict type-sensitive source/supplement song/artist/title comparison;
  independent revision fields retained rather than compared for equality.
- [x] Missing supplementary resources explicitly UNAVAILABLE, not empty chords.
- [x] Alignment always UNKNOWN; availability/text/automatic-time-truth claims fail.
- [x] Baseline/source/supplement rehashed after check; errors retained in result.
- [x] Nine targeted tests pass: byte/filepopulation corruption, typed identity,
  independent revisions, changed/unsealed supplement, absence, invented timedtruth,
  malformed baseline and duplicate metadata keys.
- [x] Actual RoughBoy audit passes provenance only:8original files+2supplementfiles,
  score revision9620672/chord revision20985,645bytes; alignmentUNKNOWN.
- [x] Root independent adversarial review and installation/integration.
- [x] Existing Gate1 optional attachment test and full relevant regressions by root.

Commands executed in this authorized visualization directory:
`python -m unittest test_source_resource_qa -q` →8PASS.
Actual `source_resource_qa.audit(...)` on frozen RoughBoy capture plus prior
preservation-verification.json and separate metadata/text →roughboy-resource-qa-result.json.
No raw chord sequence/lyrics copied into source/test/report. Baseline authenticity
is an explicit external obligation; this guard does not prove baseline history.
Root will attach result to existing Gate1 without expanding its musical scope.

Root review found identical metadata/text arguments collapsed the hash dictionary.
Fixed by requiring distinct resolved paths AND distinct basename identities under
the current baseline format. Identical-path and same-basename regressions pass;
symlink alias branch runs only where platform creation is available. Actual
RoughBoy audit rerun: PASS_PROVENANCE_ONLY, alignmentUNKNOWN. Final review pending.

Root installed-repo run seals extractor/checker/source semantics/analyzer, resource
guard, original source and separate baseline/supplement files. All5012original
occurrences still match. Resource result remains provenance-only/UNKNOWN alignment;
active inverse NOT RUN and musical-tier FAIL remain visible.40targeted tests pass;
full Python suite785tests:784PASS/1optionalSKIP. Planner independently reviewed
integration and actual resource bytes before installation. No musical acceptance.
