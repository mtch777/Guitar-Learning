import test from 'node:test';
import assert from 'node:assert/strict';
import {deleteSongFromGitHub} from '../public/piano/learning-songs/github-song-delete.js';

const parent='a'.repeat(40), baseTree='b'.repeat(40), blob='c'.repeat(40), newTree='d'.repeat(40), next='e'.repeat(40);
const seed={version:1,defaultSongId:'default',songs:[
  {id:'default',scorePath:'scores/default.musicxml',sourcePath:'scores/default.mid'},
  {id:'second',scorePath:'scores/second.musicxml',sourcePath:'scores/second.mid'},
]};
function mock() {
  const calls=[];
  const fetchImpl=async (url,init) => {
    calls.push({url,init});
    let result;
    if (url.endsWith('/git/ref/heads/main')) result={object:{sha:parent}};
    else if (url.endsWith(`/git/commits/${parent}`)) result={tree:{sha:baseTree}};
    else if (url.includes('/contents/')) result={encoding:'base64',content:Buffer.from(JSON.stringify(seed)).toString('base64')};
    else if (url.endsWith('/git/blobs')) result={sha:blob};
    else if (url.endsWith('/git/trees')) result={sha:newTree};
    else if (url.endsWith('/git/commits')) result={sha:next};
    else if (url.endsWith('/git/refs/heads/main')) result={object:{sha:next}};
    else throw new Error(`Unexpected request: ${url}`);
    return {ok:true,json:async()=>result};
  };
  return {calls,fetchImpl};
}

test('delete uploaded song removes only its original in one atomic Git commit', async () => {
  const m=mock();
  const song={id:'upload-test',sourcePath:'uploads/My score--digest.musicxml'};
  const result=await deleteSongFromGitHub(song,'temporary-token',{fetchImpl:m.fetchImpl});
  assert.equal(result.commit,next);
  assert.equal(m.calls.length,5);
  const tree=JSON.parse(m.calls.find(x=>x.url.endsWith('/git/trees')).init.body);
  assert.equal(tree.base_tree,baseTree);
  assert.deepEqual(tree.tree,[{path:'public/piano/learning-songs/uploads/My score--digest.musicxml',mode:'100644',type:'blob',sha:null}]);
  assert.equal(m.calls.at(-1).init.method,'PATCH');
  assert.equal(JSON.parse(m.calls.at(-1).init.body).force,false);
  assert.ok(m.calls.every(x=>x.init.headers.Authorization==='Bearer temporary-token' && x.init.credentials==='omit'));
  assert.doesNotMatch(JSON.stringify(result),/temporary-token/);
});

test('delete default song updates seed and removes original score files together', async () => {
  const m=mock();
  await deleteSongFromGitHub({id:'default',sourcePath:'scores/default.mid',scorePath:'scores/default.musicxml'},'temporary-token',{fetchImpl:m.fetchImpl});
  const changed=JSON.parse(m.calls.find(x=>x.url.endsWith('/git/blobs')).init.body);
  const updated=JSON.parse(changed.content);
  assert.equal(updated.defaultSongId,'second');
  assert.deepEqual(updated.songs.map(x=>x.id),['second']);
  const tree=JSON.parse(m.calls.find(x=>x.url.endsWith('/git/trees')).init.body);
  assert.deepEqual(tree.tree.map(x=>x.path).sort(),[
    'public/piano/learning-songs/scores/default.mid',
    'public/piano/learning-songs/scores/default.musicxml',
    'public/piano/learning-songs/song-library.seed.json',
  ].sort());
});

test('last seeded song may be removed; token and unsafe paths are rejected before mutation', async () => {
  const m=mock();
  const singleton={...seed,songs:[seed.songs[0]]};
  const fetchImpl=async (url,init) => url.includes('/contents/')
    ? {ok:true,json:async()=>({encoding:'base64',content:Buffer.from(JSON.stringify(singleton)).toString('base64')})}
    : m.fetchImpl(url,init);
  await deleteSongFromGitHub({id:'default',scorePath:'scores/default.musicxml',sourcePath:'scores/default.mid'},'token',{fetchImpl});
  const changed=JSON.parse(m.calls.find(x=>x.url.endsWith('/git/blobs')).init.body);
  assert.equal(JSON.parse(changed.content).defaultSongId,null);
  await assert.rejects(deleteSongFromGitHub({id:'unsafe',sourcePath:'../other'},'token',{fetchImpl:m.fetchImpl}),/deletable/);
  await assert.rejects(deleteSongFromGitHub({id:'safe',sourcePath:'uploads/safe.xml'},'',{fetchImpl:m.fetchImpl}),/token/);
});
