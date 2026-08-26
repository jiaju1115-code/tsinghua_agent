from factory import discover
if __name__=='__main__':
    d,r,t=discover(); print({'canonical_md_total':t,'eligible':len(d),'exclusions':r})
