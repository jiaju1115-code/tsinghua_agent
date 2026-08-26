from __future__ import annotations
import json, os, subprocess, tempfile, time, urllib.error, urllib.request, uuid
from pathlib import Path

class MomoApiError(RuntimeError):
    def __init__(self, message, status=None, body=""):
        super().__init__(message); self.status=status; self.body=body

class MomoApiClient:
    """OpenAI-compatible client; curl is default after native urllib WAF rejection."""
    def __init__(self, base_url="https://momoapi.cc", timeout=60, max_retries=3, transport="curl"):
        self.base_url=base_url.rstrip("/"); self.timeout=timeout; self.max_retries=max_retries; self.transport=transport
        self.api_key=os.environ.get("MOMO_API_KEY")
        if not self.api_key: raise MomoApiError("MOMO_API_KEY_NOT_CONFIGURED")
        self.stats={"api_calls":0,"retry_calls":0,"input_tokens":0,"output_tokens":0,"total_tokens":0,"latencies_ms":[]}

    def _native_diagnostic(self, path="/v1/models"):
        req=urllib.request.Request(self.base_url+path,headers={"Authorization":"Bearer "+self.api_key,"Accept":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r: body=r.read(500).decode("utf-8","replace"); return {"status":r.status,"headers":dict(r.headers),"body_prefix":body}
        except urllib.error.HTTPError as e:
            return {"status":e.code,"headers":dict(e.headers),"body_prefix":e.read(500).decode("utf-8","replace")}

    def _curl_request(self, path, payload=None, method="GET"):
        request_file=None; response_file=Path(tempfile.gettempdir())/("momo_response_"+uuid.uuid4().hex+".json")
        try:
            curl_timeout=min(self.timeout,20)
            args=["curl.exe","--silent","--show-error","--fail-with-body","--connect-timeout","10","--max-time",str(curl_timeout),"-X",method,"-H","Accept: application/json","-H","Authorization: Bearer "+self.api_key,"-o",str(response_file),"-w","%{http_code}"]
            if payload is not None:
                request_file=Path(tempfile.gettempdir())/("momo_request_"+uuid.uuid4().hex+".json")
                request_file.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
                args.extend(["-H","Content-Type: application/json","--data-binary","@"+str(request_file)])
            started=time.perf_counter(); proc=subprocess.run(args+[self.base_url+path],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=curl_timeout+5); latency=round((time.perf_counter()-started)*1000,2)
            body=response_file.read_text(encoding="utf-8",errors="replace") if response_file.exists() else ""
            try: status=int(proc.stdout.strip().splitlines()[-1])
            except (ValueError,IndexError): status=None
            if proc.returncode or not status or status >= 400: raise MomoApiError("curl transport failure",status,body[:500])
            try: data=json.loads(body)
            except json.JSONDecodeError as exc: raise MomoApiError("invalid JSON",status,body[:500]) from exc
            return data,latency,status
        finally:
            for f in (request_file,response_file):
                if f and f.exists(): f.unlink()

    def _request(self,path,payload=None,method="GET"):
        last=None
        for attempt in range(self.max_retries+1):
            self.stats["api_calls"]+=1
            try:
                data,latency,_=self._curl_request(path,payload,method); self.stats["latencies_ms"].append(latency)
                usage=data.get("usage",{}) if isinstance(data,dict) else {}
                ins=usage.get("prompt_tokens",usage.get("input_tokens",0)) or 0; outs=usage.get("completion_tokens",usage.get("output_tokens",0)) or 0
                self.stats["input_tokens"]+=ins; self.stats["output_tokens"]+=outs; self.stats["total_tokens"]+=usage.get("total_tokens",ins+outs) or 0
                return data,latency
            except MomoApiError as exc:
                last=exc
                if exc.status not in (429,500,502,503,504) or attempt>=self.max_retries: raise
                self.stats["retry_calls"]+=1; time.sleep(min(8,2**attempt))
        raise last
    def models(self): return self._request("/v1/models")[0]
    def chat(self,model,messages,response_format=None):
        payload={"model":model,"messages":messages,"temperature":0,"max_tokens":600}
        if response_format: payload["response_format"]=response_format
        return self._request("/v1/chat/completions",payload,"POST")[0]
