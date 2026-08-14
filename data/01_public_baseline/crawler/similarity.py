import hashlib
import re

def simhash(text: str, bits=64) -> str:
    tokens=re.findall(r"[\u4e00-\u9fff]|[a-z0-9]+",text.lower())
    features=("".join(tokens[i:i+3]) for i in range(max(1,len(tokens)-2)))
    vector=[0]*bits
    for feature in features:
        value=int.from_bytes(hashlib.blake2b(feature.encode(),digest_size=8).digest(),"big")
        for i in range(bits): vector[i]+=1 if value&(1<<i) else -1
    value=sum(1<<i for i,v in enumerate(vector) if v>=0)
    return f"{value:016x}"

def similarity(a: str,b: str,bits=64) -> float:
    return 1-((int(a,16)^int(b,16)).bit_count()/bits)
