"""One-shot curl endpoint diagnosis. No campus data is sent."""
from __future__ import annotations
import concurrent.futures, json, os, subprocess, sys, tempfile, time, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'experiments/campus_md_to_sft_factory_v1/audit/chat_endpoint_diagnostic_matrix.json'
BASE='https://momoapi.cc/v1'

def curl_json(path, payload, stream=False):
    key=os.environ.get('MOMO_API_KEY')
    if not key: raise RuntimeError('MOMO_API_KEY_NOT_CONFIGURED')
    tag=uuid.uuid4().hex; root=Path(tempfile.gettempdir()); request=root/f'momo_diag_request_{tag}.json'; body=root/f'momo_diag_body_{tag}.txt'; headers=root/f'momo_diag_headers_{tag}.txt'
    try:
        request.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        args=['curl.exe','--silent','--show-error','--no-buffer','--connect-timeout','15','--max-time','90','-D',str(headers),'-o',str(body),'-w','%{http_code}\t%{time_starttransfer}\t%{time_total}\t%{content_type}','-H','Accept: text/event-stream' if stream else 'Accept: application/json','-H','Authorization: Bearer '+key]
        if payload is None: args.extend(['-X','GET'])
        else: args.extend(['-H','Content-Type: application/json','--data-binary','@'+str(request)])
        args.append(BASE+path)
        proc=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=100)
        parts=proc.stdout.strip().split('\t'); status=int(parts[0]) if parts and parts[0].isdigit() else 0
        first=float(parts[1]) if len(parts)>1 and parts[1] else None; total=float(parts[2]) if len(parts)>2 and parts[2] else None
        text=body.read_text(encoding='utf-8',errors='replace') if body.exists() else ''
        hdr=headers.read_text(encoding='utf-8',errors='replace') if headers.exists() else ''
        sse='data:' in text; done='[DONE]' in text; assistant=''
        if stream:
            for line in text.splitlines():
                if not line.startswith('data:') or line.strip()=='data: [DONE]': continue
                try:
                    obj=json.loads(line[5:].strip()); assistant+=obj.get('choices',[{}])[0].get('delta',{}).get('content','') or ''
                except (json.JSONDecodeError, IndexError): pass
        else:
            try: assistant=json.loads(text).get('choices',[{}])[0].get('message',{}).get('content','') or ''
            except (json.JSONDecodeError, IndexError): pass
        return {'status':status,'curl_exit_code':proc.returncode,'first_byte_seconds':first,'total_seconds':total,'content_type':parts[3] if len(parts)>3 else None,'response_headers':hdr,'response_body':text,'sse_detected':sse,'done_detected':done,'assistant_content_received':bool(assistant),'response_error':proc.stderr.strip() or None}
    except subprocess.TimeoutExpired:
        return {'status':0,'curl_exit_code':28,'first_byte_seconds':None,'total_seconds':90,'content_type':None,'response_headers':'','response_body':'','sse_detected':False,'done_detected':False,'assistant_content_received':False,'response_error':'curl subprocess timeout'}
    finally:
        for f in (request,body,headers):
            try: f.unlink()
            except FileNotFoundError: pass

def main():
    models=curl_json('/models',None,False)
    ids=[x.get('id') for x in json.loads(models['response_body']).get('data',[]) if x.get('id')]
    def test(model,stream):
        payload={'model':model,'messages':[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':'请返回 {"ok":true}'}],'stream':stream,'temperature':0,'max_tokens':16}
        return model,stream,curl_json('/chat/completions',payload,stream)
    rows={m:{'model_id':m} for m in ids}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures=[ex.submit(test,m,s) for m in ids for s in (False,True)]
        for f in concurrent.futures.as_completed(futures):
            model,stream,result=f.result(); prefix='chat_stream' if stream else 'chat_nonstream'; rows[model][prefix+'_status']=result['status']; rows[model][prefix+'_result']='SUCCESS' if result['assistant_content_received'] and (not stream or result['sse_detected'] and result['done_detected']) else 'FAIL'; rows[model][prefix]=result
    any_chat=any(r.get('chat_nonstream_result')=='SUCCESS' or r.get('chat_stream_result')=='SUCCESS' for r in rows.values())
    responses=[]
    if not any_chat:
        for model in ids[:2]:
            result=curl_json('/responses',{'model':model,'input':'请返回 {"ok":true}','max_output_tokens':16},False); rows[model]['responses_api_result']='SUCCESS' if result['status']==200 else 'FAIL'; rows[model]['responses_api']=result; responses.append(rows[model]['responses_api_result'])
    conclusion='CHAT_API_AVAILABLE_NONSTREAM' if any(r.get('chat_nonstream_result')=='SUCCESS' for r in rows.values()) else 'CHAT_API_AVAILABLE_STREAM_ONLY' if any(r.get('chat_stream_result')=='SUCCESS' for r in rows.values()) else 'RESPONSES_API_AVAILABLE' if 'SUCCESS' in responses else 'MOMOAPI_GENERATION_UNAVAILABLE'
    payload={'models':ids,'matrix':list(rows.values()),'conclusion':conclusion,'secret_recorded':False,'campus_markdown_sent':False}
    AUDIT.parent.mkdir(parents=True,exist_ok=True); AUDIT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); print(conclusion)
if __name__=='__main__': main()
