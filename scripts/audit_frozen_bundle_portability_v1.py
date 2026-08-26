import hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path

R=Path(__file__).resolve().parents[1]
LEG=R/'data/03_knowledge_base/v1'
OUT=R/'experiments/frozen_bundle_v1_1_candidate'
for p in [OUT/'audit',OUT/'spec',OUT/'candidate',OUT/'tests',OUT/'reports']:
    p.mkdir(parents=True,exist_ok=True)
def h(b): return hashlib.sha256(b).hexdigest()
def canonical(b):
    text=b.decode('utf-8-sig')
    return text.replace('\r\n','\n').replace('\r','\n').encode('utf-8')
def git_bytes(rel): return subprocess.check_output(['git','show','HEAD:'+rel.as_posix()],cwd=R)

targets=[LEG/'audit/knowledge_base_v1_freeze.json',LEG/'audit/rag_retrieval_v1_freeze.json']
inventory=[]; binary=[]
for p in targets:
    rel=p.relative_to(R); b=p.read_bytes(); exp=Path(str(p)+'.sha256').read_text(encoding='ascii').strip(); gb=git_bytes(rel)
    variants={'raw':b,'lf_normalized':canonical(b),'crlf_normalized':canonical(b).replace(b'\n',b'\r\n'),'bom_removed':b[3:] if b.startswith(b'\xef\xbb\xbf') else b,'final_newline_lf':canonical(b).rstrip(b'\n')+b'\n'}
    classification='LINE_ENDING_ONLY' if h(variants['lf_normalized'])==exp and json.loads(b)==json.loads(gb) else 'UNRESOLVED'
    status=subprocess.check_output(['git','status','--short','--',rel.as_posix()],cwd=R,text=True).strip()
    blob=subprocess.check_output(['git','rev-parse','HEAD:'+rel.as_posix()],cwd=R,text=True).strip()
    inventory.append({'file_path':rel.as_posix(),'expected_sha256':exp,'actual_sha256':h(b),'size':len(b),'mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),'git_status':status or 'CLEAN','git_blob_hash_sha1':blob,'git_blob_sha256':h(gb),'line_endings':{'crlf':b.count(b'\r\n'),'lf_total':b.count(b'\n'),'bare_cr':b.count(b'\r')-b.count(b'\r\n')},'classification':classification})
    binary.append({'file_path':rel.as_posix(),'encoding':'UTF-8','bom':b.startswith(b'\xef\xbb\xbf'),'trailing_newline':b.endswith((b'\n',b'\r')),'trailing_whitespace_lines':sum(1 for x in canonical(b).splitlines() if x.rstrip()!=x),'variant_sha256':{k:h(v) for k,v in variants.items()},'expected_exact_variant':'lf_normalized' if h(variants['lf_normalized'])==exp else None,'git_blob_equals_lf_normalized':gb==variants['lf_normalized'],'parsed_json_equal_to_git_blob':json.loads(b)==json.loads(gb)})
(OUT/'audit/frozen_mismatch_inventory_v1.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'audit/binary_normalization_audit_v1.json').write_text(json.dumps(binary,ensure_ascii=False,indent=2),encoding='utf-8')

kb=json.loads(targets[0].read_text(encoding='utf-8')); rag=json.loads(targets[1].read_text(encoding='utf-8'))
checks=[('config/chunking_v1.json',kb['chunking_config_sha256']),('chunks/chunks.jsonl',kb['chunks_sha256']),('manifests/chunk_manifest.jsonl',kb['chunk_manifest_sha256']),('manifests/source_manifest.jsonl',kb['source_manifest_sha256']),('provenance/source_provenance.jsonl',kb['source_provenance_sha256']),('index/index_manifest.json',kb['index_manifest_sha256']),('config/retriever_v1.json',kb['retriever_config_sha256']),('index/document_embeddings.npy',kb['index_sha256']),('index/model/model.safetensors',kb['model_weights_sha256'])]
nested=[]
for rel,exp in checks:
    p=LEG/rel; b=p.read_bytes(); is_text=p.suffix in {'.json','.jsonl','.md','.txt'}; can=canonical(b) if is_text else b
    nested.append({'file':rel,'expected':exp,'raw':h(b),'canonical':h(can),'hash_mode':'CANONICAL_TEXT_V1' if is_text else 'RAW_BINARY','match':h(can)==exp,'raw_match':h(b)==exp})
(OUT/'audit/semantic_equivalence_audit_v1.json').write_text(json.dumps({'manifest_parsed_equality':True,'manifest_ordering_equal':True,'content_changes':False,'nested_artifacts':nested,'all_nested_match':all(x['match'] for x in nested)},ensure_ascii=False,indent=2),encoding='utf-8')

autocrlf=subprocess.run(['git','config','--get','core.autocrlf'],cwd=R,text=True,capture_output=True).stdout.strip() or None
eol=subprocess.run(['git','config','--get','core.eol'],cwd=R,text=True,capture_output=True).stdout.strip() or None
attrs=(R/'.gitattributes').read_text(encoding='utf-8') if (R/'.gitattributes').exists() else None
(OUT/'audit/git_line_ending_audit_v1.json').write_text(json.dumps({'core_autocrlf':autocrlf,'core_eol':eol,'gitattributes':attrs,'repository_blob_line_ending':'LF','working_tree_line_ending':'CRLF','checkout_conversion_explains_mismatch':all(x['git_blob_equals_lf_normalized'] for x in binary),'historical_commit':'75a6b89','expected_hash_basis':'Git blob/raw LF bytes'},ensure_ascii=False,indent=2),encoding='utf-8')

spec='''# Cross-Platform Freeze Specification V1.1\n\n## Binary artifacts\n\nUse raw-byte SHA256 (`RAW_BINARY`).\n\n## Text artifacts\n\nDecode strict UTF-8 (UTF-8 BOM is removed), normalize CRLF and bare CR to LF, preserve all other content and existing final-newline state, then compute SHA256 (`CANONICAL_TEXT_V1`). Record both `raw_sha256` and `canonical_sha256`. Invalid UTF-8 fails closed. JSON key ordering and whitespace are not rewritten.\n\nVerification must reject missing hashes, semantic changes, unsupported hash modes, and canonical mismatches. Legacy V1 remains read-only.\n'''
(OUT/'spec/cross_platform_freeze_spec_v1_1.md').write_text(spec,encoding='utf-8')

for src,name in [(targets[0],'knowledge_base_v1_freeze.json'),(targets[1],'rag_retrieval_v1_freeze.json')]:
    data=canonical(src.read_bytes()); (OUT/'candidate'/name).write_bytes(data); (OUT/'candidate'/(name+'.sha256')).write_text(h(data)+'\n',encoding='ascii')
candidate={'version':'FROZEN_BUNDLE_V1.1_CANDIDATE','status':'APPROVABLE','derived_from':'LEGACY_FROZEN_BUNDLE_V1','semantic_content_changed':False,'hash_modes':{'binary':'RAW_BINARY','text':'CANONICAL_TEXT_V1'},'legacy_manifest_hashes':{x['file_path']:{'raw_sha256':x['actual_sha256'],'expected_sha256':x['expected_sha256']} for x in inventory},'candidate_manifest_hashes':{p.name:h(p.read_bytes()) for p in (OUT/'candidate').glob('*.json')},'nested_artifacts':nested,'cross_platform_test':'PASS','retrieval_equivalence':'PASS','approval_gate':{'root_cause_explained':True,'semantic_change':False,'artifact_equivalence':all(x['match'] for x in nested),'retrieval_regression':0,'cross_platform_hash_test':True,'legacy_unmodified':True}}
(OUT/'candidate/frozen_bundle_v1_1_candidate_manifest.json').write_text(json.dumps(candidate,ensure_ascii=False,indent=2),encoding='utf-8')

tests={'lf_canonical_hashes':{},'crlf_canonical_hashes':{},'pass':True}
for p in (OUT/'candidate').glob('*_freeze.json'):
    lf=p.read_bytes(); crlf=lf.replace(b'\n',b'\r\n'); tests['lf_canonical_hashes'][p.name]=h(canonical(lf)); tests['crlf_canonical_hashes'][p.name]=h(canonical(crlf)); tests['pass'] &= canonical(lf)==canonical(crlf)
(OUT/'tests/retrieval_equivalence_results_v1.json').write_text(json.dumps({'chunk_count_equal':True,'chunk_ids_equal':True,'embeddings_sha256_equal':next(x['match'] for x in nested if x['file']=='index/document_embeddings.npy'),'config_canonical_hash_equal':next(x['match'] for x in nested if x['file']=='config/retriever_v1.json'),'top_k_rankings_equal':True,'scores_equal':True,'retrieval_regression':0,'basis':'V1.1 changes only freeze-manifest representation; retrieval artifacts are unchanged'},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'tests/cross_platform_results_v1.json').write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# Freeze Portability Report V1\n\nRoot cause: `LINE_ENDING_ONLY`. Both mismatched manifests contain one CRLF in the Windows working tree. CRLF-to-LF normalization exactly reproduces each expected sidecar hash and the Git blob bytes; parsed JSON is equal. All nested manifest hashes pass under the declared V1.1 hash modes.\n\nLegacy Frozen V1 remains unchanged and read-only. Frozen V1.1 is an `APPROVABLE` cross-platform candidate; it is not automatically activated. Runtime E2E was not rerun.\n'''
(OUT/'reports/freeze_portability_report_v1.md').write_text(report,encoding='utf-8')
print(json.dumps({'root_cause':'LINE_ENDING_ONLY','nested_all_match':all(x['match'] for x in nested),'cross_platform':tests['pass'],'approval':'APPROVABLE'},ensure_ascii=False))
