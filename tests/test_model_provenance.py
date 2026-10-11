import hashlib
from importlib.resources import files
import json
from pathlib import Path


def test_packaged_model_import_hashes_match_exact_bytes():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(files("quantum_models").joinpath("IMPORT_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["imports"]:
        assert hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"]
        assert item["source_bytes_preserved"] is True
    assert manifest["training_performed"] is False
