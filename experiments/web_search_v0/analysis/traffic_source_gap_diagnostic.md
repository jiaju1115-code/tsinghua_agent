# Traffic Source Gap diagnostic

Query: `清华校车什么时候发车？` (A02)

## Result

`RESOLVED_BY_PUBLIC_WEB_OFFICIAL_SOURCE`.

Three extracted sources passed the quality gate and were all `OFFICIAL_THSINGHUA`, including the public campus traffic page:

- https://www.tsinghua.edu.cn/zjqh/syxx/xyjt.htm
- https://www.tsinghua.edu.cn/info/1177/97354.htm
- https://www.tsinghua.edu.cn/info/1182/104384.htm

No non-official source was needed for the retained evidence. This demonstrates recovery of the specified public transport source gap, but does not replace the existing Local RAG corpus or establish a general guarantee for every transport query.
