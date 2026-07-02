from forge.watch import collect_new_files, is_watchable, watch_once


def test_is_watchable_extensions():
    assert is_watchable("/tmp/job.gcode")
    assert is_watchable("/tmp/job.gcode.3mf")
    assert is_watchable("/tmp/job.3mf")
    assert not is_watchable("/tmp/readme.txt")


def test_collect_new_files_finds_nested_gcode(tmp_path):
    sub = tmp_path / "inbox" / "ender"
    sub.mkdir(parents=True)
    gcode = sub / "cube.gcode"
    gcode.write_text("; test\n")
    seen: set[str] = set()
    found = collect_new_files(str(tmp_path / "inbox"), seen)
    assert len(found) == 1
    assert found[0].endswith("cube.gcode")
    # second pass — deduped
    assert collect_new_files(str(tmp_path / "inbox"), seen) == []


class _FakeDispatcher:
    def __init__(self):
        self.submitted: list[str] = []

    def submit(self, path, **extra):
        self.submitted.append(path)
        return {"state": "queued", "path": path, **extra}

    def drain(self):
        return []


def test_watch_once_submits_new_files(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    job = drop / "part.gcode"
    job.write_text("; HEADER\n")
    disp = _FakeDispatcher()
    results = watch_once(str(drop), disp, bed_confirmed=True)
    assert len(results) == 1
    assert disp.submitted == [str(job.resolve())]