import os
from dataclasses import dataclass
from dotenv import load_dotenv
from utils.paths import PROJECT_ROOT

@dataclass
class ProviderConfig:
    api_key:str;api_base:str;model:str

def load_provider()->ProviderConfig:
    load_dotenv(PROJECT_ROOT/".env",override=True)
    return ProviderConfig(os.getenv("MOMO_API_KEY","").strip(),os.getenv("MOMO_API_BASE","").strip().rstrip("/"),os.getenv("MOMO_MODEL","").strip())

