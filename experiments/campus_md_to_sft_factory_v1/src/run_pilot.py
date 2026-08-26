import os, sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if __name__=='__main__':
    if not os.environ.get('MOMO_API_KEY'):
        print('MOMO_API_KEY_NOT_CONFIGURED'); raise SystemExit(2)
    sys.path.insert(0, str(ROOT))
    from experiments.campus_md_to_sft_factory_v1.src.momo_api_client import MomoApiClient
    from experiments.campus_md_to_sft_factory_v1.src.md_eligibility import discover
    from experiments.campus_md_to_sft_factory_v1.src.generate_candidates import prompt, parse_response
    from experiments.campus_md_to_sft_factory_v1.src.validate_candidates import validate
    cfg=json.loads((ROOT/'experiments/campus_md_to_sft_factory_v1/configs/factory_config.json').read_text())
    client=MomoApiClient(cfg['base_url'], cfg['timeout_seconds'], cfg['max_retries'])
    started=__import__('time').perf_counter(); models=client.models()
    ids=[x.get('id') for x in models.get('data',[]) if x.get('id')]
    audit=ROOT/'experiments/campus_md_to_sft_factory_v1/audit'; audit.mkdir(parents=True,exist_ok=True)
    (audit/'api_capability_probe.json').write_text(json.dumps({'status':'PASS','model_ids':ids,'latency_ms':round((__import__('time').perf_counter()-started)*1000,2),'secret_recorded':False},ensure_ascii=False,indent=2),encoding='utf-8')
    if not ids: print('API_INTEGRATION_BLOCKED'); raise SystemExit(3)
    docs=discover(cfg, cfg['pilot_size']); metrics={'processed':0,'success':0,'valid_json':0,'validator_pass':0,'validator_reject':0,'generated_candidates':0,'no_training_value':0,'api_errors':0,'restricted_or_portal_documents_sent_to_api':0}
    out=ROOT/'data/fine_tuning_v1/campus_md_api_candidates'; out.mkdir(parents=True,exist_ok=True)
    names={'SUPPORTED':'supported_candidates.jsonl','PARTIAL':'partial_candidates.jsonl','PARAPHRASE':'paraphrase_candidates.jsonl','GROUNDED_ANSWER':'grounded_answer_candidates.jsonl','NEGATIVE_PROPOSAL':'negative_proposals.jsonl'}
    for doc in docs:
        metrics['processed']+=1
        try: result=parse_response(client.chat(ids[0], prompt(doc), {'type':'json_object'})); metrics['success']+=1; metrics['valid_json']+=1
        except Exception as exc: metrics['api_errors']+=1; continue
        if result.get('document_decision')=='NONE': metrics['no_training_value']+=1
        for c in result.get('candidates',[]):
            metrics['generated_candidates']+=1; ok,reasons=validate(doc,result)
            if not ok: metrics['validator_reject']+=1; continue
            c.update({'source_id':doc['source_id'],'source_url':doc['url'],'quality_level':'HIGH_CONFIDENCE_API','provenance':{'source_sha256':doc['content_sha256'],'source_type':'public'}})
            with (out/names.get(c.get('sample_type'),'rejected_candidates.jsonl')).open('a',encoding='utf-8') as f: f.write(json.dumps(c,ensure_ascii=False)+'\n')
            metrics['validator_pass']+=1
    metrics.update(client.stats); results=ROOT/'experiments/campus_md_to_sft_factory_v1/results'; results.mkdir(parents=True,exist_ok=True)
    (results/'pilot_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(metrics,ensure_ascii=False))
