import re
from urllib.parse import urlsplit

import httpx


class ArenaError(Exception):
    pass


class ArenaClient:
    def __init__(self, url, transport=None):
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            raise ArenaError("Use an http(s) arena URL without embedded credentials.")
        self.http = httpx.AsyncClient(
            base_url=url.rstrip("/") + "/", timeout=95, transport=transport
        )
        self.session = None

    async def request(self, method, path, data=None):
        headers = (
            {"Authorization": "Bearer " + self.session["token"]} if self.session else {}
        )
        try:
            response = await self.http.request(
                method, path.lstrip("/"), json=data, headers=headers
            )
            result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ArenaError(
                "Arena connection failed. Check the URL and connection."
            ) from exc
        if not response.is_success:
            detail = result.get("error") or result.get("detail")
            raise ArenaError(
                detail
                if isinstance(detail, str)
                else f"Arena returned HTTP {response.status_code}"
            )
        return result

    async def enter(
        self, target, category, profile, bot=False, question_difficulty="med"
    ):
        target = target.upper()
        if target.startswith("P-"):
            if not re.fullmatch(r"P-[A-Z2-9]{10}", target):
                raise ArenaError("Invalid pairing code.")
            self.session = await self.request(
                "POST", "api/pairings/redeem", {"code": target}
            )
        elif target == "NEW":
            self.session = await self.request(
                "POST",
                "api/games",
                {
                    "category": category,
                    "profile": profile,
                    "mode": "bot" if bot else "player",
                    "question_difficulty": question_difficulty,
                },
            )
        elif re.fullmatch(r"[A-Z2-9]{6}", target):
            self.session = await self.request(
                "POST",
                f"api/games/{target}/join",
                {"category": category, "profile": profile},
            )
        else:
            raise ArenaError(
                "Enter new, a six-character room code, or a P- pairing code."
            )
        return self.session

    async def game(self, action="", data=None):
        path = "api/games/" + self.session["code"]
        return await self.request(
            "POST" if action else "GET", path + ("/" + action if action else ""), data
        )

    async def close(self):
        await self.http.aclose()
