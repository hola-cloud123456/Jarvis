import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as jarvis


class JarvisApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = jarvis.DATABASE_PATH
        self.original_access_token = jarvis.ACCESS_TOKEN
        jarvis.DATABASE_PATH = Path(self.temp_dir.name) / "memory.sqlite3"
        jarvis.ACCESS_TOKEN = ""
        jarvis._requests_by_ip.clear()
        self.client = jarvis.app.test_client()

    def tearDown(self):
        jarvis.DATABASE_PATH = self.original_database_path
        jarvis.ACCESS_TOKEN = self.original_access_token
        self.temp_dir.cleanup()

    def test_root_serves_interface(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"JARVIS", response.data)

    def test_health_never_exposes_secret(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"gsk" + b"_", response.data)

    def test_chat_validates_input(self):
        self.assertEqual(self.client.post("/chat", data="not-json").status_code, 400)
        self.assertEqual(self.client.post("/chat", json={}).status_code, 400)
        self.assertEqual(
            self.client.post("/chat", json={"message": "hola", "session_id": "!"}).status_code,
            400,
        )

    def test_private_access_token(self):
        jarvis.ACCESS_TOKEN = "private-test-token"
        self.assertEqual(self.client.get("/api/calendar").status_code, 401)
        response = self.client.get(
            "/api/calendar",
            headers={"Authorization": "Bearer private-test-token"},
        )
        self.assertEqual(response.status_code, 200)

    def test_calendar_is_read_without_model_call(self):
        with patch.object(jarvis, "get_groq_response") as model:
            response = self.client.get("/api/calendar")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"events": []})
        model.assert_not_called()

    def test_chat_persists_memory_by_session(self):
        captured_histories = []

        def fake_response(message, history):
            captured_histories.append(history)
            return f"Respuesta a {message}", "test-model"

        with patch.object(jarvis, "get_groq_response", side_effect=fake_response):
            first = self.client.post(
                "/chat", json={"message": "primero", "session_id": "mateo"}
            )
            second = self.client.post(
                "/chat", json={"message": "segundo", "session_id": "mateo"}
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(captured_histories[0], [])
        self.assertEqual(
            captured_histories[1],
            [
                {"role": "user", "content": "primero"},
                {"role": "assistant", "content": "Respuesta a primero"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
