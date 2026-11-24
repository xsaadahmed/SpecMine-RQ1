"""Classify pending work from current caches; no network or paid dispatch."""
import json
import pandas as pd
from common import KEY,CACHE
from storage import Store,metadata_request
from detector import eligible
from pipeline import static_prediction

def audit_pending(sample,results,groups,resolver):
    known={tuple(r[k] for k in KEY):r for r in results.to_dict('records')};store=Store();records=[]
    for row in sample.to_dict('records'):
        repo,num=row['repo_name'],int(row['pr_number']);key=(repo,num);old=known.get(key,{})
        outcome=old.get('test_added_content_verified');status=None;reasons=[];actionable=False
        if pd.notna(outcome):status='confirmed_positive' if outcome==1 else 'exhaustively_verified_negative'
        else:
            files,complete,requests,why=store.files(repo,num);meta=store.data(metadata_request(repo,num))
            if meta is None:
                status='not_yet_examined' if store.record(metadata_request(repo,num)) is None else 'missing_or_changed_github_data';actionable=bool(requests);reasons.append(why)
            elif not complete:status='waiting_github_content' if requests else 'missing_or_changed_github_data';actionable=bool(requests);reasons.append(why)
            else:
                expected=groups[key];aligned={(r.file_path,r.change_status) for r in expected.itertuples()}=={(f['filename'],f['status']) for f in files}
                if not aligned:status='missing_or_changed_github_data';reasons.append('net_diff_changed')
                else:
                    missing=0;need_model=0;blocked=0;positive=False
                    for f in files:
                        if f['status']!='added' or not eligible(f['filename']):continue
                        text,prov,request=store.content(repo,meta['head_sha'],f['filename'],f.get('sha'))
                        if text is None:
                            if request:missing+=1
                            else:blocked+=1
                            reasons.append({'path':f['filename'],'retrieval':prov.get('status')});continue
                        static=getattr(resolver,'static_classifier',static_prediction)(
                            text,f['filename'],prov['content_sha256'])
                        if static.get('has_executable_tests') is True and not static.get('needs_review'):positive=True;break
                        if static.get('needs_review'):
                            ai=resolver.resolve(text,f['filename'],static['language'],prov['content_sha256'])
                            if ai.get('status')=='validated' and not ai.get('needs_review'):
                                if ai.get('has_executable_tests') is True:positive=True;break
                                continue
                            if ai.get('status') in {'dry_run','missing_XAI_API_KEY'}:need_model+=1
                            else:blocked+=1
                            reasons.append({'path':f['filename'],'model_status':ai.get('status'),'diagnostic':ai.get('diagnostic',{}).get('validation_message')})
                    status='cache_ready_for_replay' if positive else 'waiting_github_content' if missing else 'waiting_grok_classification' if need_model else 'unresolved_classification' if blocked else 'cache_ready_for_replay'
                    actionable=bool(positive or missing or need_model or not blocked)
        records.append({'repo_name':repo,'pr_number':num,'verification_state':status,'resumable':status not in {'confirmed_positive','exhaustively_verified_negative'},'actionable_now':actionable,'checkpoint_record_exists':bool(old),'checkpoint_files_inspected':old.get('n_files_inspected',0),'details':json.dumps(reasons)})
    frame=pd.DataFrame(records)
    frame['requires_future_model_review']=frame.verification_state.isin(['waiting_grok_classification','unresolved_classification'])
    return frame
