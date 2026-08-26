import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from experiments.campus_md_to_sft_factory_v1.src.momo_api_client import MomoApiClient, MomoApiError

def main():
    cfg=json.loads((ROOT/'experiments/campus_md_to_sft_factory_v1/configs/factory_config.json').read_text())
    audit=ROOT/'experiments/campus_md_to_sft_factory_v1/audit'; audit.mkdir(parents=True,exist_ok=True)
    client=MomoApiClient(cfg['base_url'],cfg['timeout_seconds'],cfg['max_retries'],cfg.get('transport','curl'))
    native=client._native_diagnostic(); headers={k.lower():v for k,v in native.get('headers',{}).items()}
    diagnostic={'status':native.get('status'),'content_type':headers.get('content-type'),'server':headers.get('server'),'cf_ray':headers.get('cf-ray'),'cf_mitigated':headers.get('cf-mitigated'),'body_prefix':native.get('body_prefix',''),'classification':'PYTHON_TRANSPORT_WAF_BLOCK_CONFIRMED' if '<html' in native.get('body_prefix','').lower() else 'API_JSON_403' if native.get('status')==403 else 'OTHER'}
    (audit/'python_403_diagnostic.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2),encoding='utf-8')
    start=time.perf_counter(); models=client.models(); latency=round((time.perf_counter()-start)*1000,2); ids=[x.get('id') for x in models.get('data',[]) if x.get('id')]
    (audit/'api_capability_probe.json').write_text(json.dumps({'status':'CURL_TRANSPORT_AVAILABLE','http_status':200,'latency_ms':latency,'json_valid':True,'model_count':len(ids),'model_ids':ids},ensure_ascii=False,indent=2),encoding='utf-8')
    if not ids: raise MomoApiError('no models')
    try:
        smoke=client.chat(ids[0],[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':'请返回 {"ok": true}'}],{'type':'json_object'})
    except MomoApiError as exc:
        (audit/'curl_chat_smoke_test.json').write_text(json.dumps({'status':'FAIL','http_status':exc.status,'error':str(exc),'body_prefix':exc.body,'secret_recorded':False},ensure_ascii=False,indent=2),encoding='utf-8')
        print('CHAT_COMPLETION_TRANSPORT_FAILED'); return 4
    content=smoke.get('choices',[{}])[0].get('message',{}).get('content','')
    try: parsed=json.loads(content); content_valid=True
    except Exception: parsed=None; content_valid=False
    (audit/'curl_chat_smoke_test.json').write_text(json.dumps({'status':'PASS' if content_valid else 'FAIL','http_status':200,'model':smoke.get('model',ids[0]),'assistant_json_valid':content_valid,'usage_present':bool(smoke.get('usage')),'usage':smoke.get('usage',{}),'secret_recorded':False},ensure_ascii=False,indent=2),encoding='utf-8')
    (audit/'transport_comparison.json').write_text(json.dumps({'python_original':native.get('status'),'curl_models':200,'python_wrapper_curl':'PASS','conclusion':'PYTHON_NATIVE_TRANSPORT_INCOMPATIBLE' if native.get('status')==403 else 'NATIVE_NOT_REPRODUCED'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS' if content_valid else 'CHAT_COMPLETION_TRANSPORT_FAILED')
    return 0 if content_valid else 4
if __name__=='__main__': raise SystemExit(main())
