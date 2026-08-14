from __future__ import annotations

import re
from urllib.parse import urlsplit
from xml.etree import ElementTree
from crawler.prioritizer import priority_score
from utils.url_utils import is_allowed, normalize_url

def sitemap_urls(fetcher, seed_url, root_domain, tracking, limit=300):
    p=urlsplit(seed_url); origin=f"{p.scheme}://{p.netloc}"
    candidates=[origin+"/sitemap.xml"]
    try:
        robots=fetcher.session().get(origin+"/robots.txt",timeout=fetcher.config["timeout_seconds"])
        if robots.status_code==200:
            candidates.extend(re.findall(r"(?im)^\s*Sitemap:\s*(\S+)",robots.text))
    except Exception: pass
    found=[]; seen=set()
    while candidates and len(found)<limit:
        sm=normalize_url(candidates.pop(0),tracking=tracking)
        if not sm or sm in seen or not is_allowed(sm,root_domain): continue
        seen.add(sm)
        if not fetcher.allowed_by_robots(sm): continue
        got=fetcher.fetch(sm)
        if not got.response or got.response.status_code!=200: continue
        try: root=ElementTree.fromstring(got.response.content)
        except ElementTree.ParseError: continue
        locs=[(x.text or "").strip() for x in root.iter() if x.tag.rsplit("}",1)[-1]=="loc"]
        if root.tag.rsplit("}",1)[-1]=="sitemapindex": candidates.extend(locs[:20])
        else:
            for raw in locs:
                url=normalize_url(raw,tracking=tracking)
                if url and is_allowed(url,root_domain): found.append((url,priority_score(url)))
                if len(found)>=limit: break
    return found
