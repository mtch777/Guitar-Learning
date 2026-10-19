# Artist profiles — requirements and evidence

Current work uses existing source observations. Approved pedal detection and
continuation are unchanged. Private fitted tables retain source locations and
must not be published with this source-code ledger.

| Requirement | Evidence now | Remaining gate |
|---|---|---|
| Preserve observations and their scope | Separate development/held-out partitions; connected song families; global timing exclusions retained | Finish duplicate identity and sealed-pedal membership guards |
| Connect techniques to context | New relational layer: duration/register/open-string context, written simultaneous texture, accepted pedal role | These are notation associations, not explanations of musical purpose |
| Capture order | Successive written attack groups with exact IOIs and gap/overlap status; source-section boundaries respected | A next attack is not automatically an answer; complete sounding/voice-specific relationships remain broader work |
| Capture call/answer | Uses approved pedal cycle memberships; records answer intervals, durations, texture, techniques and changed answers to repeated calls | Does not infer general melodic phrase roles |
| Capture repetition/variation | Separate full-member written rhythm and relative pitch fingerprints; bar span/meter included where available | Not motif identity, thematic development or perceptual similarity |
| Capture relationships across tracks | Attack alignment and simultaneous texture/interval/technique combinations; instrument programs separate | Minimum written pitch interval is not a bass/harmony function label; sustained active textures are not reconstructed here |
| Capture technique execution in context | Joins existing bend/whammy details and directed HOPO observations | No new physical execution or audible-intent inference |
| Handle unknown information | Feature-specific eligibility, unknown pitch masks, separate missing pedal coverage | Missing annotations do not prove a technique was not performed |
| Avoid domination by duplicate versions | Equal eligible song within connected family; relation/feature denominators explicit | Family discovery is an existing operational grouping, not authoritative work identification |
| Test beyond fitted songs | Eight held-out scores/six families kept out of fit; vocabulary coverage separated from prediction | Previously examined split; not a pristine final test. Context richness must beat a marginal baseline, not just contain familiar labels |
| Support artist/song/local views | Private occurrence examples and aggregate song/family/section support counts | Aggregate counts alone do not yet supply all per-song/family variation views or note-attack percentages |
| Improve actual generation |36 isolated tuning-relative GP trials, independent native checks; baseline preserved | Candidate not promoted: better marginal rates coexist with worse bass relationships and harmony movement |

## Frozen relational snapshot v2

Invent Animate:70 development score entries,54 connected families,328 eligible
tracks,147103 regular attack groups,12247 accepted pedal cycles and126955
simultaneous track-pair observations. Counts are not independent musical examples.
The private source snapshot is `relationships-unblock-v1`; no automatic use of
locally recovered timing regions is implied.

Held-out exact vocabulary coverage illustrates why coverage is not accuracy:

| Relationship | Held-out opportunities | Fitted condition seen | Exact condition and outcome seen |
|---|---:|---:|---:|
| Accepted pedal answer |1241|97.82%|17.32%|
| Next written attack |14552|98.98%|83.25%|
| Simultaneous track relationship |9551|100%|63.44%|
| Mechanical curve in context |68|91.18%|4.41%|

Fine exact answer/curve outcomes are sparse. Neither unseen exact values nor
seen coarse labels measure musical correctness. Fixed, declared smoothing and
feature-only baselines are the next predictive comparison; do not optimize on
these held-out outcomes.

## Verification and delivery

Relational helper:15 focused tests pass after independent QABot3000 findings:
feature-specific weighting denominators; explicit known masks; all-member rhythm
durations/voice IDs and meter; distinct unknown harmony contexts. Input identity
and provenance review continues before declaring this component delivered.

Diagnostics helper:7 focused tests passed and independently reviewed; committed
`9ab5eba`. Explicit theme-return constraints: fresh eight-output batch and native
checks passed; committed `707a44e`. Main CI for `707a44e` succeeded in run
39226158459. Neither commit changes website files; no new Pages deployment claimed.

Current whole local regression:442 tests run,441 passed/one optional skip;
39 JS tests passed; Vite build passed. This includes isolated unfinished profile
and proposal tests and therefore is not identical to the earlier committed CI
suite. Listening and artist-feel acceptance remain unestablished.

## Repeatable private build

```powershell
.venv/Scripts/python.exe composition-lab/build_relationship_profile.py `
  composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-unblock-v1.json `
  composition-lab/local-artifacts/pedal-expansion-v1/evaluation-sealed.json `
  composition-lab/local-artifacts/artist-pipeline-v1/relationship-profiles-v3 `
  --artist 'Invent Animate' `
  --programs composition-lab/local-artifacts/artist-pipeline-v1/relationship-programs-v1.json
```

Use a fresh output directory each time. Products: fitted model, separately labelled
held-out description, exact vocabulary coverage, predictive diagnostic and a final
manifest sealing inputs/code/product hashes. Program metadata is optional and
explicitly unknown when omitted. The canonical private program record file is
itself hashed. A source hash proves which supplied input was used; it does not
independently authenticate the original score revision.

The predictive diagnostic compares a context model with a feature-only marginal,
using a fixed prior of one family-equivalent and fixed probability clipping.
Positive log-loss/Brier improvement means lower annotation-prediction error.
Cardinality-defined chord/dyad features share definition information with the
context: do not rank their improvement as a newly discovered artist behavior.
Neither a familiar context nor a low prediction error establishes artist feel.

## Sealed v3 results — current repaired-source snapshot

Build completed with unchanged input/code hashes. All products have manifest
hashes; models and source locations remain private. Per-scope output now includes
1462 song/feature summaries and32536 track/source-section/feature summaries.
Each reports eligible/positive regular attack groups. These are NOT percentages
of individual notes, general phrase labels or performed-technique estimates.

Input join audit passes:98 songs,495tracks,420119occurrences;310 accepted pedal
coverage records,1902phrases,15795cycles.6249 untagged context members remain
untagged. Duplicate/ambiguous IDs, missing or reused cycle references, invalid
bounds and alias program identities fail closed. Twenty profile tests pass.

Prediction sensitivity on the previously examined six held-out families:

| Feature given coarse context | Log-loss improvement | Families improved | Smallest family improvement |
|---|---:|---:|---:|
| Palm mute |.169615|6/6|.101127|
| Open-string pull-off |.007936|6/6|.004166|
| Open-string hammer-on |.031886|4/6|−.023944|
| Bend |.004766|5/6|−.000194|

Lower prediction error is useful engineering evidence; it does not establish
artist fidelity. Hammer-on results are uneven across families. Family ranges and
leave-one-family-out sensitivity are descriptive, not confidence intervals.
Seven evaluator tests and six sealed-runner tests pass. Independent final artifact
QA remains the delivery gate.

Current source-profile versus unchanged12-piece generation baseline still shows
palm mute−10.333pp, extended power chord−2.203pp, open hammer−1.779pp,
open pull−.986pp and close-interval texture+.941pp. These are eligible group-rate
gaps across different mixtures. The earlier frozen profile was stale; refitting
changes the numbers modestly and does not remove the generation problem.

Final independent QABot3000 artifact QA passed: all input/code/product hashes;
4125development/2006held-out conditional tables; exact family/song weights;
all song/local support reconciliation; saved prediction rerun; full accepted
membership audit. No blocking defect found in this bounded profile layer.
This closes its engineering gate, while the broader artist-fidelity goal remains
open. Current whole local regression:465 run,464 passed/one optional skip.
