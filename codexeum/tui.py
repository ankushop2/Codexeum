import asyncio
import time
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Input, Label, Select, Static

from .agent import CodexError, CodexPlayer
from .api import ArenaClient, ArenaError
from .pets import Pet, draw_pet, pet_from_player

CATEGORIES = ("geography", "art", "maths", "biology", "history", "music", "science")


class ArenaApp(App):
    TITLE = "CODEXEUM"
    CSS = """
    Screen { background: #101915; color: #e7edce; }
    #masthead { height: 3; padding: 0 2; color: #9bca84; text-style: bold; border-bottom: solid #576b44; }
    #setup { width: 68; height: auto; max-height: 95%; margin: 2 4; padding: 1 3; border: double #a8bc6c; background: #1a281e; }
    #setup Label { margin-top: 1; }
    Input, Select { margin-bottom: 1; }
    #battle { height: 1fr; padding: 1 2; }
    #room { height: 2; color: #c5dd88; text-style: bold; }
    #arena-row { height: 1fr; min-height: 20; }
    #field { width: 1fr; border: double #a8bc6c; background: #181f1d; padding: 1 2; }
    #rival-card { text-align: right; height: 3; color: #efc88f; }
    #rival-art { text-align: right; height: 1fr; min-height: 6; }
    #mine-art { height: 1fr; min-height: 6; }
    #mine-card { height: 3; color: #c6b2ed; }
    #question-panel { width: 1fr; border: double #a8bc6c; margin-left: 1; padding: 1 2; overflow-y: auto; }
    #round { height: 2; color: #f0cb78; text-style: bold; }
    #question { height: auto; min-height: 3; margin-bottom: 1; }
    .answer { width: 100%; height: auto; min-height: 3; margin-bottom: 1; background: #273b29; color: #e7edce; border: solid #758857; text-align: left; }
    .answer:hover { background: #3d5135; }
    #narration { height: auto; min-height: 4; max-height: 7; padding: 1 2; border: solid #758857; background: #1a281e; }
    #actions { height: 3; }
    #actions Button { margin-right: 1; }
    #log { height: auto; max-height: 7; padding: 0 2; color: #bbca9a; }
    #error { height: auto; max-height: 5; color: #ffaf9e; padding: 0 2; }
    .hidden { display: none; }
    .narrow #arena-row { layout: vertical; overflow-y: auto; }
    .narrow #field { width: 100%; height: 24; }
    .narrow #question-panel { width: 100%; height: auto; min-height: 22; margin-left: 0; }
    """
    BINDINGS: ClassVar = [
        ("q", "quit", "Exit"),
        ("a", "answer(0)", "A"),
        ("b", "answer(1)", "B"),
        ("c", "answer(2)", "C"),
        ("d", "answer(3)", "D"),
        ("space", "toggle_auto", "Auto play"),
    ]

    def __init__(
        self,
        target,
        url,
        pet=None,
        nickname="TRAINER",
        category="maths",
        bot=False,
        model=None,
        client=None,
        agent=None,
    ):
        super().__init__()
        self.target, self.url = target, url
        self.pet = pet or Pet()
        self.nickname, self.category, self.bot = nickname, category, bot
        self.client = client or ArenaClient(url)
        self.agent = agent or CodexPlayer(model)
        self.game = None
        self.connected = False
        self.auto = True
        self.thinking = False
        self.busy = False
        self.attempted = set()
        self.answer_task = None
        self.poll_task = None
        self.setup_task = None
        self.last_clock = (0, 0)
        self.narration = "Your pet is ready. Connect to start a battle."
        self.submit_lock = asyncio.Lock()
        self.version = 0

    def compose(self) -> ComposeResult:
        yield Static("✦ CODEXEUM    YOUR PET. YOUR SKILLS. YOUR MOVE.", id="masthead")
        with VerticalScroll(id="setup"):
            yield Static("THE FIVE-ROUND BRAIN BATTLE", markup=False)
            yield Label(f"{self.pet.name} · {self.pet.note}")
            yield Label("ARENA SERVER")
            yield Input(self.url, id="server")
            yield Label("NEW / ROOM CODE / PAIRING CODE")
            yield Input(self.target, id="target")
            yield Label("TRAINER NAME")
            yield Input(self.nickname, max_length=20, id="nickname")
            yield Label("SPECIALTY (ignored when pairing an existing seat)")
            yield Select(
                [(c.upper(), c) for c in CATEGORIES],
                value=self.category,
                allow_blank=False,
                id="category",
            )
            yield Button("ENTER ARENA →", id="connect", variant="success")
        with Vertical(id="battle", classes="hidden"):
            yield Static("", id="room", markup=False)
            with Horizontal(id="arena-row"):
                with Vertical(id="field"):
                    yield Static("WAITING FOR RIVAL", id="rival-card", markup=False)
                    yield Static("", id="rival-art")
                    yield Static("", id="mine-art")
                    yield Static("", id="mine-card", markup=False)
                with Vertical(id="question-panel"):
                    yield Static("LOBBY", id="round", markup=False)
                    yield Static(
                        "Share your room code to invite a rival.",
                        id="question",
                        markup=False,
                    )
                    for i in range(4):
                        yield Button(
                            f"{chr(65 + i)}.",
                            id=f"answer-{i}",
                            classes="answer",
                            disabled=True,
                        )
                    with Horizontal(id="actions"):
                        yield Button("READY", id="ready", variant="success")
                        yield Button("AUTO: ON", id="auto")
            yield Static(self.narration, id="narration", markup=False)
            yield Static("", id="log", markup=False)
        yield Static("", id="error", markup=False)
        yield Footer()

    def on_mount(self):
        self.set_interval(0.2, self.refresh_clock)
        self.query_one("#mine-art", Static).update(draw_pet(self.pet))
        self.set_class(self.size.width < 85, "narrow")

    def on_resize(self):
        self.set_class(self.size.width < 85, "narrow")

    def error(self, message):
        self.query_one("#error", Static).update(message)

    def say(self, message):
        self.narration = message
        self.query_one("#narration", Static).update(message)

    @on(Button.Pressed, "#connect")
    async def connect_pressed(self):
        if self.setup_task and not self.setup_task.done():
            return
        self.setup_task = asyncio.create_task(self.connect())

    async def connect(self):
        button = self.query_one("#connect", Button)
        button.disabled = True
        try:
            url = self.query_one("#server", Input).value.strip()
            if url != self.url:
                await self.client.close()
                self.client = ArenaClient(url)
                self.url = url
            nickname = self.query_one("#nickname", Input).value.strip()
            if not nickname:
                raise ArenaError("Enter a trainer name.")
            target = self.query_one("#target", Input).value.strip()
            self.category = str(self.query_one("#category", Select).value)
            await self.client.enter(
                target,
                self.category,
                {"nickname": nickname, "pet": self.pet.payload()},
                self.bot,
            )
            self.connected = True
            self.query_one("#setup").add_class("hidden")
            self.query_one("#battle").remove_class("hidden")
            self.error("")
            self.poll_task = asyncio.create_task(self.poll())
        except (ArenaError, OSError, ValueError) as exc:
            self.error(str(exc))
        finally:
            button.disabled = False

    async def poll(self):
        while self.connected:
            try:
                version = self.version
                state = await self.client.game()
                if version != self.version:
                    continue
                self.accept(state)
                self.error("")
                if self.game["phase"] == "finished":
                    return
            except ArenaError as exc:
                self.error(str(exc) + " · retrying…")
            await asyncio.sleep(1)

    def accept(self, state):
        old_round = self.game.get("round") if self.game else None
        self.game = state
        if (
            state.get("round") != old_round
            or state.get("answered")
            or state["phase"] != "playing"
        ) and (
            self.answer_task
            and self.answer_task is not asyncio.current_task()
            and not self.answer_task.done()
        ):
            self.answer_task.cancel()
        self.last_clock = (
            state.get("deadline", 0) - state["server_time"]
            if state.get("deadline")
            else 0,
            time.monotonic(),
        )
        self.render_state()
        key = state.get("round")
        if (
            self.auto
            and state["phase"] == "playing"
            and not state.get("answered")
            and key not in self.attempted
        ):
            self.attempted.add(key)
            self.answer_task = asyncio.create_task(self.think(key, state["question"]))

    def remaining(self):
        return max(0, self.last_clock[0] - (time.monotonic() - self.last_clock[1]))

    def refresh_clock(self):
        if not self.game:
            return
        self.query_one("#round", Static).update(
            f"ROUND {self.game.get('round', '—')} / 5 · {self.game.get('question', {}).get('category', '').upper()} · {self.remaining():.0f}s"
            if self.game["phase"] == "playing"
            else self.game["phase"].upper()
        )
        enabled = (
            self.game["phase"] == "playing"
            and not self.game.get("answered")
            and self.remaining() > 0
            and not self.busy
        )
        for i in range(4):
            self.query_one(f"#answer-{i}", Button).disabled = not enabled or i >= len(
                self.game.get("question", {}).get("options", [])
            )

    def render_state(self):
        state = self.game
        players = state["players"]
        mine = players[state["you"]]
        rival = players[1 - state["you"]] if len(players) == 2 else None
        self.query_one("#room", Static).update(
            f"ROOM {state['code']}  ·  {self.url}  ·  LOCAL CODEX"
        )
        for who, player in (("mine", mine), ("rival", rival)):
            if player:
                self.query_one(f"#{who}-card", Static).update(
                    f"{player['pet']['name']} · {player['nickname']}\n{player['category'].upper()}   POINTS {player['score']}"
                )
                self.query_one(f"#{who}-art", Static).update(
                    draw_pet(pet_from_player(player), mirror=who == "rival")
                )
        phase = state["phase"]
        ready = self.query_one("#ready", Button)
        ready.disabled = self.busy or phase not in ("waiting", "ready")
        ready.label = (
            "START BATTLE"
            if phase == "ready"
            else "READY ✓"
            if mine.get("ready")
            else "READY"
        )
        if (
            phase == "waiting"
            and mine.get("ready")
            and not (len(players) == 2 and all(p.get("ready") for p in players))
        ):
            ready.disabled = True
        question = self.query_one("#question", Static)
        if phase == "playing":
            question.update(state["question"]["prompt"])
            for i, option in enumerate(state["question"]["options"][:4]):
                self.query_one(f"#answer-{i}", Button).label = Text(
                    f"{chr(65 + i)}. {option}"
                )
            if state.get("answered"):
                self.say("Move locked in. Waiting for your rival or the timer…")
        elif phase == "finished":
            winner = state.get("winner")
            result = (
                "IT’S A DRAW!"
                if winner is None
                else "YOU WIN!"
                if winner == state["you"]
                else "RIVAL WINS!"
            )
            question.update(result + "\n\nFive rounds complete. Press Q to return.")
            self.say("The battle is over. Your results are saved by the arena.")
        else:
            question.update(
                {
                    "waiting": "Waiting for a rival. Share the room code, then both players press READY.",
                    "generating": "Imagining five questions… The timer starts after you press START BATTLE.",
                    "ready": "Questions ready. Press START BATTLE when you’re ready.",
                }.get(phase, phase)
            )
        history = []
        for row in state.get("history", []):
            hits = [
                "HIT" if v is True else "MISS" if v is False else "TIMEOUT"
                for v in row["answers"]
            ]
            history.append(
                f"{row['round']}. {row['category'].upper()}  YOU {hits[state['you']]} · RIVAL {hits[1 - state['you']]}  Answer: {row.get('correct_answer', '—')}"
            )
        self.query_one("#log", Static).update("\n".join(history))
        self.refresh_clock()

    @on(Button.Pressed, "#ready")
    def ready_pressed(self):
        if not self.busy:
            self.setup_task = asyncio.create_task(self.ready())

    async def ready(self):
        if not self.game:
            return
        self.busy = True
        self.version += 1
        try:
            action = "start" if self.game["phase"] == "ready" else "ready"
            self.accept(await self.client.game(action))
        except ArenaError as exc:
            self.error(str(exc))
        finally:
            self.busy = False
            if self.game:
                self.render_state()

    async def think(self, round_number, question):
        self.thinking = True
        self.say("Your Codex pet is thinking… Press A–D to answer yourself.")
        try:
            decision = await self.agent.decide(
                question, timeout=max(1, self.remaining() - 1)
            )
            if (
                self.game.get("round") == round_number
                and not self.game.get("answered")
                and self.auto
            ):
                self.say(decision.get("message", "Move chosen."))
                await self.submit(decision["answer"], "pet", round_number)
        except CodexError as exc:
            self.say(str(exc))
        finally:
            self.thinking = False

    def action_toggle_auto(self):
        self.auto = not self.auto
        self.query_one("#auto", Button).label = "AUTO: ON" if self.auto else "AUTO: OFF"
        if not self.auto and self.answer_task and not self.answer_task.done():
            self.answer_task.cancel()
        if self.auto and self.game:
            self.attempted.discard(self.game.get("round"))
            self.accept(self.game)

    @on(Button.Pressed, "#auto")
    def auto_pressed(self):
        self.action_toggle_auto()

    @on(Button.Pressed, ".answer")
    def answer_pressed(self, event):
        self.action_answer(int(event.button.id.rsplit("-", 1)[1]))

    def action_answer(self, index):
        if (
            not self.game
            or self.game["phase"] != "playing"
            or self.game.get("answered")
            or self.remaining() <= 0
            or self.busy
        ):
            return
        if self.answer_task and not self.answer_task.done():
            self.answer_task.cancel()
        self.setup_task = asyncio.create_task(
            self.submit(index, "trainer", self.game["round"])
        )

    async def submit(self, index, source, round_number):
        async with self.submit_lock:
            if (
                self.game.get("round") != round_number
                or self.game.get("answered")
                or self.remaining() <= 0
            ):
                return
            self.busy = True
            self.version += 1
            try:
                self.accept(
                    await self.client.game(
                        "answers",
                        {"round": round_number, "answer": index, "source": source},
                    )
                )
            except ArenaError as exc:
                self.error(str(exc))
            finally:
                self.busy = False
                self.refresh_clock()

    async def shutdown(self):
        self.connected = False
        tasks = [
            t
            for t in (self.answer_task, self.poll_task, self.setup_task)
            if t and not t.done()
        ]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.agent.close()
        await self.client.close()
