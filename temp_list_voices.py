from huggingface_hub import list_repo_tree

for speaker in ["carlfm", "davefx", "mls_10246", "mls_9972", "sharvard"]:
    print(f"\n=== es/es_ES/{speaker} ===")
    try:
        for item in list_repo_tree("rhasspy/piper-voices", path_in_repo=f"es/es_ES/{speaker}", recursive=False):
            path = getattr(item, "path", str(item))
            print("  " + path.split("/")[-1])
    except Exception as e:
        print(f"  Error: {e}")
