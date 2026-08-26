# Dynamic Retriever V0.1 Validation & Mixed Regression

{
  "staging_correction": {
    "canonical_count": 920,
    "cross_dedup_counts": {
      "UNIQUE_DYNAMIC": 920
    },
    "final_dynamic_sources": 920,
    "final_dynamic_chunks": 2429,
    "excluded_exact_core_duplicate_ids": [],
    "conclusion": "The 920/916 discrepancy was not reproduced: current deterministic cross-dedup has 0 EXACT_CORE_DUPLICATE; the 4 groups in canonicalization are internal duplicate groups, not Core matches."
  },
  "temporal": {
    "counts": {
      "UNKNOWN": 643,
      "ACTIVE": 41,
      "EXPIRED": 149,
      "NOT_APPLICABLE": 19,
      "ONGOING": 71,
      "UPCOMING": 1
    },
    "deadline": 188,
    "event_interval": 0,
    "valid_until": 2,
    "ambiguous": 588,
    "parse_failure": 93
  },
  "retrieval": {
    "Lexical": {
      "n": 70,
      "Hit@1": 0.8571428571428571,
      "Hit@5": 1.0,
      "Hit@10": 1.0,
      "Hit@20": 1.0,
      "MRR": 0.919047619047619
    },
    "Dense": {
      "status": "LOCAL_MODEL_MISSING"
    },
    "Hybrid": {
      "status": "NOT_AVAILABLE_DENSE_MISSING",
      "lexical_fallback": {
        "n": 70,
        "Hit@1": 0.8571428571428571,
        "Hit@5": 1.0,
        "Hit@10": 1.0,
        "Hit@20": 1.0,
        "MRR": 0.919047619047619
      }
    }
  },
  "core_regression": {
    "status": "NO_RETRIEVAL_GOLD_FOR_FROZEN_CASES",
    "Core Only": "NOT_RUN",
    "Core + Dynamic": "NOT_RUN"
  },
  "mixed_evaluation": {
    "dynamic_positive": 70,
    "core_cases": "NO_RETRIEVAL_GOLD",
    "cross_layer": 20,
    "negative": 10
  },
  "leakage": {
    "negative_cases": 10,
    "dynamic_top1_intrusion_rate": 1.0,
    "dynamic_top5_intrusion_rate": 1.0,
    "core_top1_retention": "NOT_COMPUTABLE_NO_CORE_GOLD",
    "core_top5_retention": "NOT_COMPUTABLE_NO_CORE_GOLD"
  },
  "fusion": {
    "Equal-weight RRF": {
      "status": "NOT_RUN_DENSE_MISSING"
    },
    "Core-priority RRF": {
      "status": "NOT_RUN_DENSE_MISSING"
    },
    "Dynamic-priority RRF": {
      "status": "NOT_RUN_DENSE_MISSING"
    }
  },
  "recovery_queue": {
    "status": "PENDING_AUTH_RECOVERY",
    "count": 22,
    "international_internship": 19
  },
  "readiness": "NEEDS_RETRIEVAL_TUNING",
  "readiness_reason": "Staging is internally consistent, but Dense/Hybrid validation is unavailable because the frozen local embedding model was not loaded."
}