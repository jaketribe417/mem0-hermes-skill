#!/usr/bin/env python3
"""
Build-time patcher for mem0 v2.0.4
Applies all runtime patches at build time instead of startup.

Patches applied:
1. main.py — Inject OLLAMA config, 1536 dims, disable HNSW/diskann
2. mem0/memory/main.py — Fix cosine distance → similarity inversion in _search_vector_store
3. main.py — Inject /__build__ health endpoint
"""

import os
import sys
import re

PATCHES = {
    "main.py": {
        "target": r"OPENAI_API_KEY = os\.environ\.get\(\"OPENAI_API_KEY\"\)",
        "replacement": r'''OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OLLAMA_API_KEY = os.environ.get("OLLAMA_CLOUD_API_KEY", "")''',
        "description": "Inject OLLAMA_API_KEY alongside OPENAI_API_KEY"
    },
    "main.py_config": {
        "target": r'"collection_name": POSTGRES_COLLECTION_NAME,',
        "replacement": r'''"collection_name": POSTGRES_COLLECTION_NAME,
            "embedding_model_dims": 1536,
            "hnsw": False,
            "diskann": False,''',
        "description": "Set 1536 embedding dims, disable HNSW/diskann for pgvector"
    },
    "main.py_llm": {
        "target": r'"llm": \{\s*"provider": "openai",\s*"config": \{"api_key": OPENAI_API_KEY, "temperature": 0\.2, "model": DEFAULT_LLM_MODEL\},',
        "replacement": r'''"llm": {
        "provider": "openai",
        "config": {"api_key": OLLAMA_API_KEY or OPENAI_API_KEY, "openai_base_url": "https://ollama.com/v1" if OLLAMA_API_KEY else None, "temperature": 0.2, "model": DEFAULT_LLM_MODEL},''',
        "description": "Route LLM through Ollama when OLLAMA_API_KEY is set"
    },
    "mem0/memory/main.py_score": {
        "target": r'"score": mem\.score,',
        "replacement": r'''"score": (1.0 - mem.score) if mem.score > 0.5 else mem.score,''',
        "description": "Invert cosine distance to similarity for pgvector results"
    },
    "main.py_build_endpoint": {
        "target": r'@app\.get\("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False\)',
        "replacement": r'''@app.get("/__build__", summary="Build info", include_in_schema=False)
def __build__():
    from server_state import get_current_config as gcc
    cfg = gcc()
    e = cfg.get("embedder", {})
    vs = cfg.get("vector_store", {})
    return {
        "build": "BUILD-20260606-HARDENED",
        "version": "v2.0.4",
        "embedder": e.get("provider"),
        "embed_model": e.get("config", {}).get("model"),
        "vs_dims": vs.get("config", {}).get("embedding_model_dims"),
        "llm_model": cfg.get("llm", {}).get("config", {}).get("model"),
        "search_fix": True,
        "patched_at": "build"
    }

@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)''',
        "description": "Inject /__build__ health endpoint"
    },
}

def find_file(base_dir, filename):
    """Find file in site-packages or source tree."""
    for root, dirs, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

def apply_patch(filepath, patch_name, target_pattern, replacement, description):
    """Apply a single regex-based patch."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    if not re.search(target_pattern, content):
        print(f"  WARNING: Patch '{patch_name}' target not found — may already be patched or upstream changed")
        return False
    
    new_content = re.sub(target_pattern, replacement, content, count=1)
    
    if new_content == content:
        print(f"  WARNING: Patch '{patch_name}' did not modify content")
        return False
    
    with open(filepath, 'w') as f:
        f.write(new_content)
    
    print(f"  OK: {description}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: mem0_apply_patches.py <site-packages-dir>")
        sys.exit(1)
    
    base_dir = sys.argv[1]
    print(f"Patching mem0 in: {base_dir}")
    
    # Find files
    main_py = find_file(base_dir, "main.py")
    memory_main_py = find_file(base_dir, "main.py")
    
    # memory/main.py is in mem0/memory/ subdirectory
    memory_main = None
    for root, dirs, files in os.walk(base_dir):
        if "mem0" in root and "memory" in root and "main.py" in files:
            memory_main = os.path.join(root, "main.py")
            break
    
    results = {"applied": 0, "failed": 0, "skipped": 0}
    
    # Patch main.py
    if main_py:
        print(f"\nPatching: {main_py}")
        for key in ["main.py", "main.py_config", "main.py_llm", "main.py_build_endpoint"]:
            patch = PATCHES[key]
            if apply_patch(main_py, key, patch["target"], patch["replacement"], patch["description"]):
                results["applied"] += 1
            else:
                results["failed"] += 1
    else:
        print("ERROR: main.py not found")
        results["failed"] += 4
    
    # Patch mem0/memory/main.py
    if memory_main:
        print(f"\nPatching: {memory_main}")
        patch = PATCHES["mem0/memory/main.py_score"]
        if apply_patch(memory_main, "mem0/memory/main.py_score", patch["target"], patch["replacement"], patch["description"]):
            results["applied"] += 1
        else:
            results["failed"] += 1
    else:
        print("ERROR: mem0/memory/main.py not found")
        results["failed"] += 1
    
    print(f"\n{'='*50}")
    print(f"Patches applied: {results['applied']}")
    print(f"Patches failed: {results['failed']}")
    print(f"{'='*50}")
    
    if results["failed"] > 0:
        print("ERROR: Some patches failed. Do not deploy.")
        sys.exit(1)
    
    print("SUCCESS: All patches applied. Ready for deployment.")

if __name__ == "__main__":
    main()
