import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

for(const [file,port] of [['pedal-diff.html',5191],['pedal-evidence.html',5195]]) test(`${file}: file opening redirects before module loading`,()=>{
 const html=fs.readFileSync(new URL('../composition-lab/'+file,import.meta.url),'utf8');
 const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
 const element=()=>({children:[],append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;}});
 const main=element(),body=element();let destination;
 const document={body,querySelector:()=>main,getElementById:()=>null,createElement:element};
 vm.runInNewContext(source,{document,location:{protocol:'file:',search:'?case=gained-00001',hash:'#roll',replace(url){destination=url;}},
  addEventListener(){assert.fail('File opening must exit before HTTP module setup');}});
 assert.equal(destination,`http://127.0.0.1:${port}/?case=gained-00001#roll`);
 assert.equal(main.hidden,true);
 assert.equal(body.children.length,1);
 assert.equal(body.children[0].children[2].href,destination);
 assert.match(body.children[0].children[1].textContent,/source HTML does not contain/);
});
