import json
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
import game


def generated_questions(first, second, other):
    return [
        {
            "category": category,
            "prompt": f"Question {index}",
            "options": ["yes", "no"],
            "answer": 0,
        }
        for index, category in enumerate([first, first, second, second, other])
    ]


class MemoryStore:
    def __init__(self):
        self.games = {}
        self.lock = threading.Lock()

    def create(self, code, value):
        with self.lock:
            if code in self.games:
                return False
            self.games[code] = json.dumps(value)
            return True

    def get(self, code):
        with self.lock:
            return self.games.get(code)

    def replace(self, code, old, value):
        with self.lock:
            if self.games.get(code) != old:
                return False
            self.games[code] = json.dumps(value)
            return True


class GameTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        generator = patch("game.generate_questions", side_effect=generated_questions)
        generator.start()
        self.addCleanup(generator.stop)
        self.first = game.create_game(self.store, "maths")
        self.code = self.first["code"]
        self.second = game.join_game(self.store, self.code, "geography")
        self.tokens = [self.first["token"], self.second["token"]]
        for token in self.tokens:
            game.ready_game(self.store, self.code, token)
        game.start_game(self.store, self.code, self.tokens[0])

    def test_concurrent_answers_score_and_advance_once(self):
        current = json.loads(self.store.get(self.code))
        correct = current["questions"][0]["answer"]
        errors = []

        def submit(token):
            try:
                game.answer_game(self.store, self.code, token, 1, correct)
            except game.GameError as error:
                errors.append(error)

        threads = [
            threading.Thread(target=submit, args=(token,)) for token in self.tokens
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        state = game.get_game(self.store, self.code, self.tokens[0])
        category = current["questions"][0]["category"]
        self.assertEqual(
            [p["score"] for p in state["players"]],
            [2 if category == c else 5 for c in ("maths", "geography")],
        )
        self.assertEqual(state["round"], 2)
        self.assertEqual(len(state["history"]), 1)
        with self.assertRaises(game.GameError):
            game.answer_game(self.store, self.code, self.tokens[0], 1, correct)

    def test_timeout_rejects_late_answer_and_next_poll_advances(self):
        current = json.loads(self.store.get(self.code))
        with patch("game.time.time", return_value=current["deadline"]):
            with self.assertRaises(game.GameError):
                game.answer_game(self.store, self.code, self.tokens[0], 1, 0)
            state = game.get_game(self.store, self.code, self.tokens[0])
        self.assertEqual(state["round"], 2)
        self.assertEqual(state["history"][0]["answers"], [None, None])
        self.assertEqual(state["deadline"], current["deadline"] + 30)

    def test_complete_five_rounds_and_hide_answers(self):
        for round_number in range(1, 6):
            current = json.loads(self.store.get(self.code))
            state = game.get_game(self.store, self.code, self.tokens[0])
            self.assertNotIn("answer", state["question"])
            for token in self.tokens:
                result = game.answer_game(
                    self.store,
                    self.code,
                    token,
                    round_number,
                    current["questions"][round_number - 1]["answer"],
                )
        self.assertEqual(result["phase"], "finished")
        self.assertEqual(len(result["history"]), 5)
        scores = [p["score"] for p in result["players"]]
        self.assertEqual(
            result["winner"],
            None if scores[0] == scores[1] else scores.index(max(scores)),
        )

    def test_scores_hidden_until_round_resolves(self):
        current = json.loads(self.store.get(self.code))
        correct = current["questions"][0]["answer"]
        after_answer = game.answer_game(
            self.store, self.code, self.tokens[0], 1, correct
        )
        opponent_view = game.get_game(self.store, self.code, self.tokens[1])
        self.assertEqual([p["score"] for p in after_answer["players"]], [0, 0])
        self.assertEqual([p["score"] for p in opponent_view["players"]], [0, 0])
        finished = game.answer_game(self.store, self.code, self.tokens[1], 1, 1)
        self.assertGreater(finished["players"][0]["score"], 0)
        self.assertEqual(finished["history"][0]["answers"], [True, False])

    def test_scores_revealed_after_timeout(self):
        current = json.loads(self.store.get(self.code))
        game.answer_game(self.store, self.code, self.tokens[0], 1, 0)
        with patch("game.time.time", return_value=current["deadline"]):
            state = game.get_game(self.store, self.code, self.tokens[1])
        self.assertGreater(state["players"][0]["score"], 0)
        self.assertEqual(state["history"][0]["answers"], [True, None])

    def test_authentication_and_invalid_inputs(self):
        with self.assertRaises(game.GameError):
            game.get_game(self.store, self.code, "invalid")
        with self.assertRaises(game.GameError):
            game.answer_game(self.store, self.code, self.tokens[0], 1, True)
        self.assertEqual(len(json.loads(self.store.get(self.code))["answers"]), 0)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        generator = patch("game.generate_questions", side_effect=generated_questions)
        generator.start()
        self.addCleanup(generator.stop)
        self.patcher = patch.object(app, "store", self.store)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = TestClient(app.app)

    def test_create_join_get_answer(self):
        first = self.client.post("/api/games", json={"category": "maths"})
        self.assertEqual(first.status_code, 201)
        code = first.json()["code"]
        second = self.client.post(
            f"/api/games/{code}/join", json={"category": "geography"}
        )
        self.assertEqual(second.status_code, 200)
        headers = {"Authorization": "Bearer " + first.json()["token"]}
        self.assertEqual(
            self.client.get(f"/api/games/{code}", headers=headers).json()["phase"],
            "waiting",
        )
        self.client.post(f"/api/games/{code}/ready", headers=headers)
        second_headers = {"Authorization": "Bearer " + second.json()["token"]}
        prepared = self.client.post(f"/api/games/{code}/ready", headers=second_headers)
        self.assertEqual(prepared.json()["phase"], "ready")
        self.assertNotIn("question", prepared.json())
        started = self.client.post(f"/api/games/{code}/start", headers=headers)
        self.assertEqual(started.json()["deadline"] - started.json()["server_time"], 30)
        state = self.client.get(f"/api/games/{code}", headers=headers)
        self.assertEqual(state.json()["phase"], "playing")
        self.assertEqual(state.headers["Cache-Control"], "no-store")
        self.assertEqual(
            self.client.post(
                f"/api/games/{code}/answers",
                headers=headers,
                json={"round": 1, "answer": 0},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                f"/api/games/{code}/answers",
                headers=headers,
                json={"round": 1, "answer": 0},
            ).status_code,
            409,
        )
        self.assertEqual(self.client.get(f"/api/games/{code}").status_code, 401)


if __name__ == "__main__":
    unittest.main()
