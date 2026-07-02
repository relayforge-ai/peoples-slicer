from forge.jobqueue import JobQueue


def test_enqueue_then_peek_returns_job(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    q.enqueue("ad5x", {"id": "abc", "name": "sandal.gcode"})
    assert q.peek("ad5x")["id"] == "abc"


def test_peek_empty_is_none(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    assert q.peek("ad5x") is None


def test_fifo_order_and_pending_list(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    q.enqueue("ad5x", {"id": "a"})
    q.enqueue("ad5x", {"id": "b"})
    assert q.peek("ad5x")["id"] == "a"
    assert [j["id"] for j in q.pending("ad5x")] == ["a", "b"]


def test_start_next_activates_and_removes_from_pending(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    q.enqueue("ad5x", {"id": "a"})
    q.enqueue("ad5x", {"id": "b"})
    started = q.start_next("ad5x")
    assert started["id"] == "a"
    assert q.active("ad5x")["id"] == "a"
    assert [j["id"] for j in q.pending("ad5x")] == ["b"]


def test_start_next_empty_returns_none(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    assert q.start_next("ad5x") is None


def test_complete_clears_active(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    q.enqueue("ad5x", {"id": "a"})
    q.start_next("ad5x")
    q.complete("ad5x", "a")
    assert q.active("ad5x") is None


def test_dedup_same_id_not_enqueued_twice(tmp_path):
    q = JobQueue(str(tmp_path / "state.json"))
    q.enqueue("ad5x", {"id": "a"})
    q.enqueue("ad5x", {"id": "a"})
    assert len(q.pending("ad5x")) == 1


def test_state_survives_reload(tmp_path):
    path = str(tmp_path / "state.json")
    q = JobQueue(path)
    q.enqueue("ad5x", {"id": "a"})
    q.enqueue("ad5x", {"id": "b"})
    q.start_next("ad5x")  # a -> active
    reloaded = JobQueue(path)
    assert reloaded.active("ad5x")["id"] == "a"
    assert [j["id"] for j in reloaded.pending("ad5x")] == ["b"]
