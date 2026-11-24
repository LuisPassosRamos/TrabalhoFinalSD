from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src.cloud.cloud_server import create_app


class CloudReplicaTests(TestCase):
    def setUp(self):
        temporary_dir = TemporaryDirectory()
        self.addCleanup(temporary_dir.cleanup)
        self.path = Path(temporary_dir.name) / "replica.json"
        self.app = create_app(self.path)
        self.client = self.app.test_client()

    def test_round_trip_persists_across_app_instances(self):
        self.assertEqual(self.client.get("/replica").json, [])
        entry = {"sensor_id": 2, "mensagem": "Medição registrada"}
        self.assertEqual(self.client.post("/replica", json=entry).status_code, 200)
        self.assertEqual(create_app(self.path).test_client().get("/replica").json, [entry])

    def test_invalid_input_leaves_replica_empty(self):
        self.assertEqual(self.client.post("/replica", json=["registro"]).status_code, 400)
        self.assertEqual(self.client.get("/replica").json, [])

    def test_concurrent_requests_keep_all_records(self):
        def replicate(index):
            client = self.app.test_client()
            self.assertEqual(client.post("/replica", json={"sequence": index}).status_code, 200)
            self.assertEqual(client.get("/replica").status_code, 200)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(replicate, range(20)))
        self.assertEqual(sorted(row["sequence"] for row in self.client.get("/replica").json), list(range(20)))

    def test_failed_replacement_preserves_previous_data(self):
        self.client.post("/replica", json={"sequence": 1})
        with patch("src.cloud.cloud_server.os.replace", side_effect=OSError), self.assertLogs():
            self.assertEqual(self.client.post("/replica", json={"sequence": 2}).status_code, 500)
        self.assertEqual(self.client.get("/replica").json, [{"sequence": 1}])
