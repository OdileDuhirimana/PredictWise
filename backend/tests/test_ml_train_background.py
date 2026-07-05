"""Tests for the background-job path added to POST /ml/train.

Uses `fakeredis` (a pure-Python, in-process Redis implementation) instead
of a real Redis server — this environment has no Redis server available,
and fakeredis is the standard way to test RQ-dependent code without one.
`rq.SimpleWorker` executes jobs synchronously in the current process
(rather than forking, which the default `Worker` does and which fakeredis
connections don't survive across a fork), which is exactly what a
single-process test needs.

Scope note: `run_training_job()` creates its own Flask app pointed at
`DATABASE_URL`, which is a *different* database than the one this test's
`app`/`client` fixtures use (an isolated `sqlite:///:memory:` per test
function). Proving the job sees the *same* seeded data it would in a real
deployment would require a shared file-backed database wired through both
the test app and the job — these tests instead verify what they can
directly control: that a request enqueues a real job, that the job
actually executes when a worker picks it up, and that the status endpoint
correctly reports queued/finished state and surfaces the job's result
(including the "no assessment data" case, which is exactly what the job
sees against its own separate empty database). In production, the web
and worker processes are configured to point at the same real database
(Postgres, or a shared file) — a standard deployment assumption this
suite cannot exercise without a second live process.
"""
import fakeredis
import pytest
from rq import Queue, SimpleWorker

from backend.jobs import queue as queue_module

API = "/api/v1"


@pytest.fixture()
def fake_redis_connection(monkeypatch):
    """Points backend.jobs.queue.get_redis_connection() at an in-process
    fakeredis instance instead of a real Redis server."""
    connection = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(queue_module, "get_redis_connection", lambda: connection)
    return connection


class TestTrainEnqueuesWhenRedisConfigured:
    def test_train_returns_202_with_job_id(self, fake_redis_connection, make_authenticated_client):
        client, headers, _ = make_authenticated_client("bgtrain.enqueue@example.com", role="admin")

        resp = client.post(f"{API}/ml/train", headers=headers)

        assert resp.status_code == 202
        body = resp.get_json()
        assert body["status"] == "queued"
        assert "job_id" in body

    def test_teacher_still_gets_403_on_background_path(self, fake_redis_connection, make_authenticated_client):
        """The RBAC gate must apply identically regardless of whether
        training runs synchronously or as a background job."""
        client, headers, _ = make_authenticated_client("bgtrain.forbidden@example.com", role="teacher")

        resp = client.post(f"{API}/ml/train", headers=headers)

        assert resp.status_code == 403


class TestTrainStatusEndpoint:
    def test_status_reflects_finished_job_and_result(self, fake_redis_connection, make_authenticated_client):
        client, headers, _ = make_authenticated_client("bgtrain.status@example.com", role="admin")

        enqueue_resp = client.post(f"{API}/ml/train", headers=headers)
        job_id = enqueue_resp.get_json()["job_id"]

        # Execute the queued job synchronously in this process (no real
        # worker process needed for the test).
        work_queue = Queue(queue_module.TRAINING_QUEUE_NAME, connection=fake_redis_connection)
        worker = SimpleWorker([work_queue], connection=fake_redis_connection)
        worker.work(burst=True)

        status_resp = client.get(f"{API}/ml/train/status/{job_id}", headers=headers)

        assert status_resp.status_code == 200
        body = status_resp.get_json()
        assert body["job_id"] == job_id
        assert body["status"] == "finished"
        # The job's own isolated database has no seeded assessments (see
        # module docstring), so its result is the same "no assessment
        # data" dict the synchronous path returns in that situation —
        # proving the job actually ran the real training entry point
        # rather than a stub.
        assert body["result"] == {"error": "no assessment data"}

    def test_unknown_job_id_returns_404(self, fake_redis_connection, make_authenticated_client):
        client, headers, _ = make_authenticated_client("bgtrain.unknown@example.com", role="admin")

        resp = client.get(f"{API}/ml/train/status/does-not-exist", headers=headers)

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "not_found"

    def test_status_endpoint_requires_admin(self, fake_redis_connection, make_authenticated_client):
        client, headers, _ = make_authenticated_client("bgtrain.statusdenied@example.com", role="teacher")

        resp = client.get(f"{API}/ml/train/status/some-id", headers=headers)

        assert resp.status_code == 403


class TestTrainStatusWithoutRedisConfigured:
    def test_status_endpoint_404s_when_background_training_disabled(self, make_authenticated_client):
        """No fake_redis_connection fixture here: REDIS_URL is unset, so
        get_training_queue() returns None, matching the default/demo
        deployment with no Redis available."""
        client, headers, _ = make_authenticated_client("bgtrain.disabled@example.com", role="admin")

        resp = client.get(f"{API}/ml/train/status/some-id", headers=headers)

        assert resp.status_code == 404
