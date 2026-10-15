"""Inspect/download the official public default artifact without credentials.

Download occurs only with --download-to. No license inference: a repository
code license alone does not settle weight redistribution permissions.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error

QUERY='''query($entity:String!,$project:String!,$name:String!){
 project(name:$project,entityName:$entity){
 artifact(name:$name){id metadata description}
 artifactCollection(name:"model-uvj2ddun"){
 artifactMembership(aliasName:"v1"){
 files(first:50){edges{node{displayName directUrl sizeBytes md5}}}
 }}
 }}'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path)
    p.add_argument('--download-to',type=Path);args=p.parse_args()
    payload=dict(query=QUERY,variables=dict(entity='melkisedeath',project='AnalysisGNN',name='model-uvj2ddun:v1'))
    request=urllib.request.Request('https://api.wandb.ai/graphql',data=json.dumps(payload).encode(),
                                   headers={'Content-Type':'application/json','User-Agent':'Composition-Lab-public-metadata-check'})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            report=dict(status=response.status,response=json.load(response),credentials_sent=False)
    except urllib.error.HTTPError as exc:
        report=dict(status=exc.code,error=exc.read().decode()[:3000],credentials_sent=False)
    if args.download_to:
        entries=report['response']['data']['project']['artifactCollection']['artifactMembership']['files']['edges']
        files=[x['node'] for x in entries if x['node']['displayName']=='model.ckpt']
        if len(files)!=1:raise ValueError('Official artifact did not contain exactly one model.ckpt')
        file=files[0]; destination=args.download_to
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists():
            with urllib.request.urlopen(file['directUrl'],timeout=60) as response,destination.open('xb') as handle:
                while chunk:=response.read(8*1024*1024):handle.write(chunk)
        data=destination.read_bytes()
        if len(data)!=int(file['sizeBytes']):raise ValueError('Checkpoint size mismatch')
        md5=hashlib.md5(data).hexdigest()
        if file.get('md5') and file['md5'] not in (md5,base64.b64encode(hashlib.md5(data).digest()).decode()):
            raise ValueError('Checkpoint MD5 mismatch; existing file was preserved')
        report['download']=dict(path=str(destination),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            md5=md5,source='official AnalysisGNN default artifact model-uvj2ddun:v1',
            code_license='MIT',weight_specific_license='not stated in artifact metadata or file list; redistribution not established')
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    public=json.loads(json.dumps(report))
    # Signed storage URLs stay in the ignored local metadata report.
    try:
        for edge in public['response']['data']['project']['artifactCollection']['artifactMembership']['files']['edges']:
            edge['node'].pop('directUrl',None)
    except (KeyError,TypeError):pass
    print(json.dumps(public,indent=2))


if __name__=='__main__':main()
