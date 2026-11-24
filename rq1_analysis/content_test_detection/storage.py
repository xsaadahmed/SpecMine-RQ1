"""Read-only reuse of historical caches, pinned content verification, new caches."""
import base64
import json
import re
from pathlib import Path

from common import CACHE,HIST,OUT,ROOT,sha256,write_json


def request(kind,args):
    ident=sha256(json.dumps({'kind':kind,'args':args},sort_keys=True).encode())[:24]
    return {'id':ident,'kind':kind,'args':args}


def metadata_request(repo,num):return request('metadata',{'repository_full_name':repo,'pr_number':int(num)})


def files_request(repo,num,page):return request('files',{'url':f'https://api.github.com/repos/{repo}/pulls/{int(num)}/files?per_page=100&page={page}'})


def content_request(repo,sha,path):
    if not re.fullmatch('[0-9a-f]{40}',str(sha)):raise ValueError('Unpinned content request')
    return request('content',{'repository_full_name':repo,'ref':sha,'path':path,'encoding':'base64'})


def git_blob_sha(raw):
    import hashlib
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


class Store:
    def __init__(self):
        self.old=HIST/'cache/responses'
        self.new=CACHE/'github'
        self.memory={}
    def record(self,req):
        ident=req['id']
        if ident in self.memory:return self.memory[ident]
        for directory in [self.new,self.old]:
            path=directory/(ident+'.json')
            if path.exists():
                value=json.loads(path.read_text(encoding='utf-8'))
                assert value['request']['kind']==req['kind'] and value['request']['args']==req['args']
                self.memory[ident]=value;return value
        return None
    def data(self,req):
        r=self.record(req);return r.get('data') if r and r.get('ok') else None
    def files(self,repo,num):
        req=metadata_request(repo,num);meta=self.data(req)
        if meta is None:return None,False,[req] if self.record(req) is None else [],'metadata_missing_or_failed'
        count=meta.get('changed_files')
        if count is None or count>=3000:return None,False,[],'incomplete_or_capped_file_list'
        rows=[];pending=[]
        for page in range(1,(count+99)//100+1):
            req=files_request(repo,num,page);data=self.data(req)
            if data is None:
                if self.record(req) is None:pending.append(req)
            else:rows.extend(data)
        complete=len(rows)==count and not pending and len({r['filename'] for r in rows})==len(rows)
        return rows,complete,pending,'complete' if complete else 'file_pages_missing_or_failed'
    def content(self,repo,sha,path,expected_blob=None):
        req=content_request(repo,sha,path);r=self.record(req)
        if r is None:return None,{'status':'not_cached','request_id':req['id']},req
        if not r.get('ok'):return None,{'status':'retrieval_failed','request_id':req['id']},None
        d=r['data']
        if d.get('unavailable_reason')=='blob_fallback_required':
            if expected_blob and d.get('sha')!=expected_blob:return None,{'status':'blob_metadata_hash_mismatch','integrity_error':True},None
            blob_req=request('blob',{'repository_full_name':repo,'sha':d['sha'],'ref':sha})
            blob_record=self.record(blob_req)
            if blob_record is None:return None,{'status':'waiting_pinned_blob','request_id':blob_req['id']},blob_req
            if not blob_record.get('ok'):return None,{'status':'blob_retrieval_failed','request_id':blob_req['id']},None
            d=blob_record['data']
            if not d.get('unavailable_reason') and d.get('sha')!=blob_req['args']['sha']:return None,{'status':'blob_response_hash_mismatch','integrity_error':True},None
        if d.get('unavailable_reason'):return None,{'status':d['unavailable_reason'],'request_id':req['id']},None
        try:
            if d.get('encoding')=='base64':raw=base64.b64decode(''.join(d['content'].split()),validate=True)
            elif d.get('encoding')=='utf-8':raw=d['content'].encode()
            else:raise ValueError('Unsupported encoding')
            blob=git_blob_sha(raw)
            if blob!=d.get('sha') or expected_blob and expected_blob!=blob:
                # Only a specifically investigated, hash-proven path-reference
                # anomaly may be quarantined without ending unrelated PR work.
                # This NEVER returns source text or supplies a negative label.
                proof_path=CACHE/'quarantined_path_references'/(req['id']+'.json')
                if proof_path.exists():
                    proof=json.loads(proof_path.read_text())
                    assert proof['request']==req
                    assert expected_blob==d.get('sha')==proof['expected_blob_sha']
                    assert git_blob_sha(proof['expected_reference_text'].encode())==expected_blob
                    assert blob==proof['computed_response_blob_sha'] and sha256(raw)==proof['response_sha256']
                    return None,{'status':'quarantined_path_reference_contents_response','request_id':req['id'],'expected_blob_sha':expected_blob,'actual_blob_sha':blob,'proof_reference':str(proof_path)},None
                raise ValueError('Blob hash mismatch')
            if b'\0' in raw:return None,{'status':'binary_data','request_id':req['id']},None
            text=raw.decode('utf-8-sig')
        except (ValueError,UnicodeError,KeyError,TypeError) as error:return None,{'status':'invalid_hash_encoding_or_binary','request_id':req['id'],'integrity_error':isinstance(error,ValueError) and str(error)=='Blob hash mismatch','expected_blob_sha':expected_blob,'returned_metadata_sha':d.get('sha'),'actual_blob_sha':locals().get('blob')},None
        digest=sha256(raw);ref=OUT/'content'/(digest+'.txt')
        if not ref.exists():ref.write_bytes(raw)
        else:assert sha256(ref.read_bytes())==digest
        return text,{'status':'verified','repo_name':repo,'commit_sha':sha,'file_path':path,'blob_sha':blob,'content_sha256':digest,'content_reference':ref.relative_to(ROOT).as_posix(),'request_id':req['id'],'pinned_url':d.get('display_url')},None


def cached_review_text(row):
    ref=(HIST/row['content_reference']).resolve()
    assert ref.is_relative_to(HIST.resolve()),'Unsafe historical content reference'
    raw=ref.read_bytes()
    assert sha256(raw)==row['content_sha256'] and git_blob_sha(raw)==row['blob_sha']
    assert str(row['commit_sha']) in row['pinned_url']
    return raw.decode('utf-8-sig')
