"""Independent raw occurrence arithmetic for the published bounded DAG study.

Does not import the Tier2 core, extractor or its template scoring helper.
"""
from fractions import Fraction as F


def check(raw,evidence):
    request=evidence['request'];a,b=F(request['start_q']),F(request['end_q']);part=request['part_id']
    population=[(max(a,F(start)),min(b,F(start)+F(duration)),pitch) for pid,bar,pitch,start,duration in raw
                if (part is None or pid==part) and F(start)<b and F(start)+F(duration)>a and F(duration)>0]
    points=sorted({a,b}|{t for start,end,p in population if p is not None and F(p).denominator==1 for t in (start,end)})
    issues=[]
    if list(map(str,points))!=evidence['partition_points_q']:issues.append('Raw nominal partition boundaries differ')
    edges=len(points)*(len(points)-1)//2
    if edges>request['max_edges']:
        return dict(status='PASS' if evidence['status']=='NOT_RUN_RESOURCE_LIMIT' and not issues else 'FAIL',issues=issues,required_edges=edges,scope='Resource preflight only; no musical inference')
    forms=(('major',(0,4,7)),('dominant-seventh',(0,4,7,10)),('minor',(0,3,7)),('diminished-seventh',(0,3,6,9)),('half-diminished-seventh',(0,3,6,10)),('diminished',(0,3,6)))
    best=[0];pred=[[]];labels={};values={};comparisons=0
    for j in range(1,len(points)):
        choices=[]
        for i in range(j):
            weights=[0]*12
            for start,end,pitch in population:
                if pitch is None or F(pitch).denominator!=1:continue
                weight=sum(start<=t<end for t in points[i:j]);weights[int(F(pitch)%12)]+=weight
            rows=[]
            if any(weights):
                for kind,form in forms:
                    for root in range(12):
                        pcs={(root+d)%12 for d in form}
                        positive=sum(weights[pc] for pc in pcs);negative=sum(w for pc,w in enumerate(weights) if pc not in pcs);missing=sum(weights[pc]==0 for pc in pcs)
                        rows.append((positive-negative-missing,root,kind))
            score=max((v for v,_,_ in rows),default=0);labels[i,j]={(r,k) for v,r,k in rows if v==score};values[i,j]=(score,weights)
            choices.append((best[i]+score,i));comparisons+=len(rows)
        value=max(v for v,_ in choices);best.append(value);pred.append([i for v,i in choices if v==value])
    if best[-1]!=evidence['optimal_score'] or pred!=evidence['optimal_predecessors']:issues.append('Independent whole DAG optimum/predecessors differ')
    for edge in evidence['canonical_display_path']:
        key=(edge['start_index'],edge['end_index'])
        if values[key]!=(edge['score'],edge['pitch_class_note_cell_weights']):issues.append('Selected edge score/evidence differs')
        if labels[key]!={(r['root_pc'],r['kind']) for r in edge['candidates']}:issues.append('Selected edge tied label inventory differs')
    count=[1]
    for j in range(1,len(points)):count.append(sum(count[i] for i in pred[j]))
    if str(count[-1])!=evidence['optimal_boundary_path_count']:issues.append('Optimal boundary path multiplicity differs')
    remaining=[0]*len(points);remaining[-1]=1
    for j in reversed(range(1,len(points))):
        for i in pred[j]:remaining[i]+=remaining[j]
    mandatory=[i for i in range(len(points)) if count[i]*remaining[i]==count[-1]]
    if evidence['mandatory_boundary_indices']!=mandatory:issues.append('All-path mandatory boundary inventory differs')
    for cell,row in enumerate(evidence['all_optimal_path_cell_consensus']):
        union=set();empty=False
        for j in range(cell+1,len(points)):
            if not remaining[j]:continue
            for i in pred[j]:
                if i<=cell:
                    union|=labels[i,j]
                    if not labels[i,j]:empty=True
        if union!={(c['root_pc'],c['kind']) for c in row['candidate_labels']} or empty!=row['no_pitched_evidence_possibility']:issues.append('All-optimal-path label/unknown consensus differs')
    return dict(status='FAIL' if issues else 'PASS',issues=issues,independently_computed_template_scores=comparisons,source_partition_points=len(points),scope='Raw nominal intervals; compares whole DAG optimum/predecessors and canonical-edge scores/labels, not every producer template row or chord truth')
