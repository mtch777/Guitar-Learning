# Playback and selection acceptance

- [x] Manual phrase selection preserves playback marker and horizontal scroll.
- [x] Review repeat closure is fetched from the existing backend plan; manual ids remain separate from gray auto-selected ids.
- [x] One-click regenerate uses existing default Both and posts only manual ids; no extra modal/confirmation.
- [x] Successful revision automatically renders full edited audio using chosen verified Kontakt preset; no autoplay.
- [x] Roll-body taps seek; checkbox selection remains separate; drag is ignored.
- [x] Play resumes from marker; sustained notes retrigger only their remaining duration.
- [x] Existing same-revision Kontakt audio element is retained on UI rerender.
- [x] Focused Node tests passed, including stale selection plan, rollback and no auto-render after failure.
- [ ] Integrated layout/step0 suites and visual browser QA owned by root.

Current defaults: Both regeneration; Modern Metal 1 when no explicit preset is chosen. Gray repeats can receive rhythm only according to backend closure; the manual selection is never expanded in the regeneration request.
