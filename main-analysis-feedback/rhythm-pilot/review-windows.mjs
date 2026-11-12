import {Q,qnum} from '../playback/timing.mjs?v=audio-fix-1';
export const reviewWindows={
  "rhythm-pilot-001-01": {
    "range_q": [
      "364",
      "380"
    ],
    "original_range_q": [
      "332",
      "396"
    ],
    "revision": "76c92e120de41489f104acfe8b819d416a6c625f87af400fa027d16155a104a6",
    "reason": "One complete repeated cycle containing the original target; the distinct opening stays available in full context."
  },
  "rhythm-pilot-001-02": {
    "range_q": [
      "724",
      "748"
    ],
    "original_range_q": [
      "684",
      "748"
    ],
    "revision": "753e1fc09f72556ceecb08b961ea2831874d1bb0ca8afa364edd6512ce8d3500",
    "reason": "One complete repeated 24-quarter sequence containing the target and continuation."
  },
  "rhythm-pilot-001-03": {
    "range_q": [
      "0",
      "16"
    ],
    "original_range_q": [
      "0",
      "64"
    ],
    "revision": "0a6a5e8cee2bce18205208ab87d571defeea3198b18d9e3da332e1981e94681e",
    "reason": "First of four identical 16-quarter cycles."
  },
  "rhythm-pilot-001-04": {
    "range_q": [
      "192",
      "224"
    ],
    "original_range_q": [
      "172",
      "236"
    ],
    "revision": "d77134d38317571f36f652910536d4830966b2437838fac387c42bc64845c9e9",
    "reason": "Focused grouping window retaining surrounding phrases and the target; repeated attacks needed for grouping remain."
  },
  "rhythm-pilot-001-05": {
    "range_q": [
      "80",
      "96"
    ],
    "original_range_q": [
      "32",
      "96"
    ],
    "revision": "61fe61d1266195664b7220c54150f9c5f592a029e99030799df3be845ea8717a",
    "reason": "Final complete cycle retained because its ending differs from earlier repetitions."
  },
  "rhythm-pilot-001-06": {
    "range_q": [
      "4",
      "20"
    ],
    "original_range_q": [
      "4",
      "40"
    ],
    "revision": "f7c95a86adf1af26466e40b3c1c0bd1d890c7f10c8504c21f3645160ae19b1c1",
    "reason": "One of two identical full cycles, retaining both coherent gestures."
  },
  "rhythm-pilot-001-07": {
    "range_q": [
      "137",
      "153"
    ],
    "original_range_q": [
      "121",
      "153"
    ],
    "revision": "a4bb94aab50ed21919d74ffffc2f744e9539800934ed2f91f2b63741cf20bb95",
    "reason": "Original A and changed B retained; earlier duplicate cycles removed."
  },
  "rhythm-pilot-001-08": {
    "range_q": [
      "261",
      "277"
    ],
    "original_range_q": [
      "261",
      "301"
    ],
    "revision": "798b055ec196c205798f1b4a2499bcb608aed8c608f8af5e7675d2c7cbfe80b7",
    "reason": "Focused original A/B pair. Later development is different and remains available in full context."
  },
  "rhythm-pilot-001-09": {
    "range_q": [
      "368",
      "380"
    ],
    "original_range_q": [
      "348",
      "388"
    ],
    "revision": "57dc3510ec027ff407a80e672c55e50c5f8dd02a04105e1668d50a0c88b8ea7d",
    "reason": "Original A/B plus the returning A retained because all three are needed for the dialogue judgment."
  },
  "rhythm-pilot-001-10": {
    "range_q": [
      "640",
      "672"
    ],
    "original_range_q": [
      "640",
      "704"
    ],
    "revision": "98ede2584635057f8e4572ea90611800bfc1b1626997ffb689c121df9ab44a4e",
    "reason": "First of two identical complete cycles; both comparison gestures retained."
  },
  "rhythm-pilot-001-11": {
    "range_q": [
      "390",
      "401"
    ],
    "original_range_q": [
      "378",
      "442"
    ],
    "revision": "d85f32b2655d5101264bde29dbda6758b7b838cac18d346592d5e7720c672bcc",
    "reason": "Focused pause/hold context with the target and continuation. Source-wide partial-coverage limits still apply."
  },
  "rhythm-pilot-001-12": {
    "range_q": [
      "25/2",
      "36"
    ],
    "original_range_q": [
      "0",
      "36"
    ],
    "revision": "6cd821e1a060f22c2ff309fca3d6773a600e5082905fbbd0e3c80614a6c56dc3",
    "reason": "Conservative focused window retaining overlapping holds and the final target. The apparent cycles are not identical."
  }
};
export function reviewRange(c,full=false){
 const w=reviewWindows[c.id];if(!w||w.revision!==c.revision||JSON.stringify(w.original_range_q)!==JSON.stringify(c.context_range_q))throw Error('Short review window is not bound to this source version.');
 return (full?c.context_range_q:w.range_q).map(String);
}
export function cropStream(s,range){
 const [start,end]=range.map(v=>new Q(v)),inside=q=>new Q(q).cmp(start)>=0&&new Q(q).cmp(end)<0;
 const member=m=>({...m,offset_q:String(new Q(m.onset_q).sub(start)),written_end_offset_q:m.written_end_q?String(new Q(m.written_end_q).sub(start)):m.written_end_offset_q,tied_end_offset_q:m.tied_end_q?String(new Q(m.tied_end_q).sub(start)):m.tied_end_offset_q});
 const attacks=(s.attacks??[]).filter(a=>inside(a.onset_q)).map(a=>({...a,offset_q:String(new Q(a.onset_q).sub(start)),members:(a.members??[]).map(member)}));
 const carry_in=[...(s.carry_in??[]),...(s.attacks??[]).flatMap(a=>a.members??[])].filter(m=>m.onset_q&&new Q(m.onset_q).cmp(start)<0&&new Q(m.tied_end_q??m.end_q??m.written_end_q).cmp(start)>0).map(member);
 const uncovered_intervals_q=(s.uncovered_intervals_q??[]).map(g=>Array.isArray(g)?g:[g.start_q,g.end_q]).filter(([a,b])=>new Q(b).cmp(start)>0&&new Q(a).cmp(end)<0).map(([a,b])=>[String(new Q(a).cmp(start)<0?start:a),String(new Q(b).cmp(end)>0?end:b)]);
 const labels={};for(const a of attacks)for(const n of a.members){const label=n.notation?.label??n.written_duration_q+'q';labels[label]=(labels[label]??0)+1;}
 return {...s,id:s.id+':review',start_q:String(start),end_q:String(end),duration_q:String(end.sub(start)),attacks,carry_in,summary:{...s.summary,attack_groups:attacks.length,notation_label_counts:labels},meter:(s.meter??[]).filter(b=>new Q(b.end_q).cmp(start)>0&&new Q(b.start_q).cmp(end)<0),written_rests:(s.written_rests??[]).filter(r=>inside(r.onset_q??r.start_q)),uncovered_intervals_q,uncovered_intervals_offset_q:uncovered_intervals_q.map(([a,b])=>[String(new Q(a).sub(start)),String(new Q(b).sub(start))])};
}
