import {groupedTriads} from './triads.js';
import {buildTriadMusicXML} from './notation.js';

const container = document.getElementById('triad-groups');
const scores=[];

function createGroups() {
  for (const {count,chords} of groupedTriads()) {
    const group=document.createElement('section');
    group.className='notation-group';
    group.dataset.blackKeys=String(count);
    const title=document.createElement('h2');
    title.textContent=count+(count===1?' black key':' black keys');
    title.className='lesson-section-title';
    group.append(title);
    const paper=document.createElement('div');
    paper.className='score-paper';
    const score=document.createElement('div');
    score.className='triad-score';
    score.setAttribute('aria-label',chords.map(chord=>chord.name+' major: '+chord.notes.join(' ')).join('; '));
    paper.append(score);
    group.append(paper);
    const status=document.createElement('p');
    status.className='render-status';
    status.textContent='Loading notation…';
    group.append(status);
    container.append(group);
    scores.push({group,score,status,chords});
  }
}

async function drawScores() {
  const Runtime=window.opensheetmusicdisplay?.OpenSheetMusicDisplay;
  for (const item of scores) {
    try {
      if (!Runtime) throw new Error('Sheet music library unavailable.');
      const osmd=new Runtime(item.score,{
        backend:'svg',autoResize:false,followCursor:false,
        drawTitle:false,drawSubtitle:false,drawComposer:false,drawLyricist:false,
        drawPartNames:false,drawPartAbbreviations:false,
        newPageFromXML:false,newSystemFromXML:false,
      });
      await osmd.load(buildTriadMusicXML(item.chords));
      const mobile=item.score.clientWidth < 500;
      osmd.Zoom=mobile ? 0.74 : 0.92;
      osmd.render();
      item.group.dataset.ready='true';
      item.status.hidden=true;
      item.osmd=osmd;
    } catch(error) {
      item.group.dataset.ready='false';
      item.status.textContent='Sheet music error: '+(error?.message||error);
      console.error('Major Triads engraving error:',error);
    }
  }
  window.PracticeTracker?.recordOpen('sheet-reading-major-triads-reference');
}

createGroups();
window.addEventListener('load',drawScores,{once:true});