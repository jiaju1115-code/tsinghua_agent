"""Read-only metadata probe for the frozen V2.1 recovery source revisions."""
from huggingface_hub import HfApi

SOURCES = {
    "nvidia/Nemotron-Instruction-Following-Chat-v1": "83dcd3a",
    "allenai/tulu-3-sft-personas-instruction-following": "fe0c7d3",
    "databricks/databricks-dolly-15k": "bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a",
    "rajpurkar/squad": "7b6d24c",
    "tasksource/ruletaker": "a3e0880",
    "facebook/babi_qa": "021d7ae",
    "nvidia/OpenCodeInstruct": "8f3ba5b",
    "google-research-datasets/mbpp": "4bb6404",
}

api = HfApi()
for dataset, revision in SOURCES.items():
    try:
        info = api.dataset_info(dataset, revision=revision, files_metadata=True)
        files = [{"path": x.rfilename, "size": x.size, "blob_id": x.blob_id} for x in info.siblings]
        print({"dataset": dataset, "requested_revision": revision, "resolved_sha": info.sha, "files": files})
    except Exception as exc:
        print({"dataset": dataset, "requested_revision": revision, "error": f"{type(exc).__name__}: {exc}"})
