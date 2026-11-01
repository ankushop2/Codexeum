import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app as api
import game

pytest.importorskip("textual")
pytest.importorskip("PIL")

from codexeum.agent import CodexPlayer
from codexeum.api import ArenaClient
from codexeum.pets import load_pet
from codexeum.tui import ArenaApp
from test_game import MemoryStore, generated_questions


class PairStore(MemoryStore):
    def __init__(self):
        super().__init__()
        self.pairs = {}

    def command(self, command, *args):
        with self.lock:
            if command == "SET":
                key, value = args[:2]
                if key in self.pairs:
                    return None
                self.pairs[key] = value
                return "OK"
            if command == "EVAL":
                return self.pairs.pop(args[2], None)
            raise AssertionError(command)


def test_pairing_requires_player_and_redeems_once(monkeypatch):
    store = PairStore()
    monkeypatch.setattr(api, "store", store)
    client = TestClient(api.app)
    first = client.post("/api/games", json={"category": "maths"}).json()
    endpoint = f"/api/games/{first['code']}/pairing"
    assert client.post(endpoint).status_code == 401
    pair = client.post(endpoint, headers={"Authorization": "Bearer " + first["token"]})
    assert pair.status_code == 200
    assert pair.headers["Cache-Control"] == "no-store"
    assert pair.json()["expires_in"] == 300
    code = pair.json()["pairing_code"]
    assert len(code) == 12
    redeemed = client.post("/api/pairings/redeem", json={"code": code})
    assert redeemed.json() == first
    assert client.post("/api/pairings/redeem", json={"code": code}).status_code == 404
    state = client.get(
        f"/api/games/{first['code']}",
        headers={"Authorization": "Bearer " + first["token"]},
    ).json()
    assert len(state["players"]) == 1
    assert state["players"][0]["controller"] == "codex"
    assert "token" not in state["players"][0]
    assert (
        client.post("/api/pairings/redeem", json={"code": "invalid"}).status_code == 400
    )


class FakeAgent:
    def __init__(self):
        self.seen = []
        self.closed = False

    async def decide(self, question, timeout):
        self.seen.append(question)
        await asyncio.sleep(0.03)
        return {"answer": 0, "message": "Move chosen!"}

    async def close(self):
        self.closed = True


def test_terminal_new_room_and_five_autoplay_rounds(monkeypatch, tmp_path):
    store = PairStore()
    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(game, "generate_questions", generated_questions)

    async def run():
        agent = FakeAgent()
        client = ArenaClient("http://arena", httpx.ASGITransport(app=api.app))
        app = ArenaApp(
            "new",
            "http://arena",
            nickname="PIXEL",
            bot=True,
            client=client,
            agent=agent,
        )
        try:
            async with app.run_test(size=(120, 44)) as pilot:
                await pilot.click("#connect")
                for _ in range(40):
                    await pilot.pause(0.05)
                    if app.game:
                        break
                assert app.game["phase"] == "waiting"
                assert len(app.game["players"]) == 2
                await app.ready()
                assert app.game["phase"] == "ready"
                await app.ready()
                assert app.game["phase"] == "playing"
                app.save_screenshot("arena.svg", path=str(tmp_path))
                for _ in range(150):
                    await pilot.pause(0.1)
                    if app.game["phase"] == "finished":
                        break
                assert app.game["phase"] == "finished"
                assert len(app.game["history"]) == 5
                assert len(agent.seen) == 5
                assert all("answer" not in question for question in agent.seen)
                assert all(row["sources"][0] == "pet" for row in app.game["history"])
                assert app.game["players"][0]["score"] == 10
        finally:
            await app.shutdown()
        assert agent.closed

    asyncio.run(run())


def test_pet_extracts_idle_frame_and_retains_name(tmp_path):
    from PIL import Image

    root = tmp_path / "pixel"
    root.mkdir()
    (root / "pet-record.json").write_text(json.dumps({"name": "Pixel"}))
    Image.new("RGBA", (1536, 2288), "black").save(root / "spritesheet.png")
    pet = load_pet(root)
    assert pet.name == "Pixel"
    assert pet.image.size == (192, 208)
    assert pet.payload()["image"].startswith("data:image/png;base64,")


def test_codex_protocol_stream_returns_valid_decision(tmp_path, monkeypatch):
    server = tmp_path / "fake-codex"
    server.write_text("""#!/usr/bin/env python3
import sys, json
for line in sys.stdin:
 m=json.loads(line); method=m.get("method"); rid=m.get("id")
 if rid is None: continue
 result={}
 if method=="thread/start": result={"thread":{"id":"quiz"}}
 if method=="turn/start": result={"turn":{"id":"turn1"}}
 print(json.dumps({"id":rid,"result":result}),flush=True)
 if method=="turn/start":
  print(json.dumps({"method":"item/completed","params":{"threadId":"quiz","item":{"type":"agentMessage","text":json.dumps({"answer":1,"message":"Two!"})}}}),flush=True)
  print(json.dumps({"method":"turn/completed","params":{"threadId":"quiz","turn":{"id":"turn1","status":"completed"}}}),flush=True)
""")
    server.chmod(0o700)
    monkeypatch.setenv("CODEXEUM_CODEX_BIN", str(server))

    async def run():
        player = CodexPlayer()
        try:
            result = await player.decide(
                {"prompt": "1+1?", "options": ["1", "2", "3", "4"]}, 10
            )
            assert result["answer"] == 1
        finally:
            await player.close()

    asyncio.run(run())


def test_human_answer_cancels_pending_codex_move(monkeypatch):
    store = PairStore()
    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(game, "generate_questions", generated_questions)

    class SlowAgent(FakeAgent):
        cancelled = False

        async def decide(self, question, timeout):
            try:
                await asyncio.sleep(10)
                return {"answer": 1, "message": "Late move"}
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    async def run():
        agent = SlowAgent()
        client = ArenaClient("http://arena", httpx.ASGITransport(app=api.app))
        app = ArenaApp("new", "http://arena", bot=True, client=client, agent=agent)
        try:
            async with app.run_test(size=(80, 32)) as pilot:
                app.query_one("#connect").scroll_visible(animate=False)
                await pilot.pause()
                await pilot.click("#connect")
                for _ in range(40):
                    await pilot.pause(0.05)
                    if app.game:
                        break
                await app.ready()
                await app.ready()
                await pilot.pause(0.1)
                assert app.thinking
                app.action_answer(0)
                await pilot.pause(0.2)
                assert agent.cancelled
                assert app.game["answered"]
                saved = json.loads(store.get(client.session["code"]))
                assert saved["answers"]["0"]["source"] == "trainer"
                assert len(saved["answers"]) == 1
        finally:
            await app.shutdown()

    asyncio.run(run())
