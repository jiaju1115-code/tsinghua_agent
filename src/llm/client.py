from __future__ import annotations
import time
import requests
from utils.security import assert_external_allowed,redact

class AuthenticationError(RuntimeError):pass
class APIError(RuntimeError):pass

class MomoClient:
    def __init__(self,provider,timeout=90,max_retries=2,retry_delay=2,session=None):
        self.p=provider;self.timeout=timeout;self.max_retries=max_retries;self.retry_delay=retry_delay;self.session=session or requests.Session()
    def _headers(self):return {"Authorization":f"Bearer {self.p.api_key}","Content-Type":"application/json"}
    def _request(self,method,path,**kwargs):
        url=self.p.api_base+path
        for attempt in range(self.max_retries+1):
            try:r=self.session.request(method,url,headers=self._headers(),timeout=self.timeout,**kwargs)
            except requests.RequestException as exc:
                if attempt>=self.max_retries:raise APIError(redact(exc)) from exc
                time.sleep(self.retry_delay*(2**attempt));continue
            if r.status_code in (401,403):raise AuthenticationError("API Key可能已经失效，请更换.env中的MOMO_API_KEY。")
            if r.status_code==429 or 500<=r.status_code<600:
                if attempt>=self.max_retries:raise APIError(f"HTTP {r.status_code}: {redact(r.text[:500])}")
                time.sleep(self.retry_delay*(2**attempt));continue
            if not r.ok:raise APIError(f"HTTP {r.status_code}: {redact(r.text[:500])}")
            return r.json()
        raise APIError("unreachable")
    def models(self):return self._request("GET","/models")
    def chat(self,candidate,messages,max_tokens=900,temperature=.1,json_mode=True):
        assert_external_allowed(candidate,False)
        payload={"model":self.p.model,"messages":messages,"max_tokens":max_tokens,"temperature":temperature}
        if json_mode:payload["response_format"]={"type":"json_object"}
        return self._request("POST","/chat/completions",json=payload)

