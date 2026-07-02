import json
from forge.store import JsonlStore, NullStore

def test_jsonl_store_appends(tmp_path):
    s = JsonlStore(str(tmp_path / "jobs.jsonl"))
    s.record({"state": "printing", "printer": "bambu"})
    s.record({"state": "queued", "printer": "ender"})
    lines = (tmp_path / "jobs.jsonl").read_text().splitlines()
    assert [json.loads(x)["state"] for x in lines] == ["printing", "queued"]

def test_null_store_is_noop():
    NullStore().record({"anything": 1})  # must not raise
