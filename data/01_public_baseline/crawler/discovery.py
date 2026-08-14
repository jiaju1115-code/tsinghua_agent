from utils.url_utils import ATTACHMENT_EXTENSIONS, SKIP_EXTENSIONS, extension, is_allowed, normalize_url
from crawler.prioritizer import priority_score

def discover(links, root_domain, depth, max_depth, tracking):
    if depth >= max_depth: return []
    result=[]
    for item in links:
        raw,text=item if isinstance(item,(tuple,list)) else (item,"")
        url=normalize_url(raw, tracking=tracking)
        if not url or not is_allowed(url, root_domain): continue
        if extension(url) in ATTACHMENT_EXTENSIONS | SKIP_EXTENSIONS: continue
        result.append((url,priority_score(url,text)))
    return list(dict.fromkeys(result))
