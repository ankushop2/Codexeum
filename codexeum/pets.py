"""Read installed custom pet artwork; never import account credentials."""

import base64
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from rich.style import Style
from rich.text import Text


@dataclass
class Pet:
    name: str = "CODEX"
    color: str = "#aaa0e8"
    image: Image.Image | None = None
    note: str = "Choose a local pet folder or image with --pet to use its artwork."

    def payload(self):
        result = {"name": self.name[:20], "color": self.color}
        if self.image:
            frame = self.image.copy()
            frame.thumbnail((128, 128))
            canvas = Image.new("RGBA", (128, 128))
            canvas.alpha_composite(
                frame, ((128 - frame.width) // 2, 128 - frame.height)
            )
            output = io.BytesIO()
            canvas.save(output, format="PNG")
            result["image"] = (
                "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
            )
        return result


def installed_pets(home=None):
    root = (
        Path(home) if home else Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    ) / "pets"
    return (
        sorted(
            p
            for p in root.iterdir()
            if p.is_dir() and (p / "pet-record.json").is_file()
        )
        if root.is_dir()
        else []
    )


def load_pet(path=None):
    path = path or os.getenv("CODEXEUM_PET")
    if not path:
        pets = installed_pets()
        if len(pets) != 1:
            return Pet(
                note="No single local custom pet found. Use --pet PATH to select your pet artwork."
            )
        path = pets[0]
    source = Path(path).expanduser()
    record = {}
    if source.is_dir():
        metadata = source / "pet-record.json"
        if metadata.is_file():
            record = json.loads(metadata.read_text())
            if not isinstance(record, dict):
                raise ValueError("pet-record.json must contain an object")
        source = next(
            (
                source / name
                for name in ("spritesheet.png", "spritesheet.webp")
                if (source / name).is_file()
            ),
            source / "spritesheet.png",
        )
    with Image.open(source) as original:
        original.load()
        image = original.convert("RGBA")
    if image.size in ((1536, 1872), (1536, 2288)):
        image = image.crop((0, 0, 192, 208))
    image.thumbnail((192, 208))
    return Pet(
        name=str(record.get("name") or source.parent.name if record else source.stem)[
            :20
        ],
        image=image,
        note=f"Using {source.name}",
    )


def pet_from_player(player):
    value = player.get("pet", {})
    pet = Pet(name=value.get("name", "RIVAL"), color=value.get("color", "#edac79"))
    data = value.get("image", "")
    if data.startswith("data:image/png;base64,") and len(data) <= 100000:
        try:
            with Image.open(
                io.BytesIO(base64.b64decode(data.split(",", 1)[1], validate=True))
            ) as image:
                if image.width <= 128 and image.height <= 128:
                    pet.image = image.convert("RGBA")
        except (ValueError, OSError):
            pass
    return pet


def draw_pet(pet, width=24, mirror=False):
    if not pet.image:
        return Text(
            "      /\\_/\\\n     ( o.o )\n      > ^ <\n     /|   |\\\n    (_|___|_)\n",
            style=pet.color,
        )
    image = pet.image.copy()
    if mirror:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    image.thumbnail((width, 24))
    output = Text()
    background = (24, 31, 29)

    def rgb(pixel):
        r, g, b, a = pixel
        return tuple(
            round(c * a / 255 + bg * (1 - a / 255))
            for c, bg in zip((r, g, b), background)
        )

    for y in range(0, image.height, 2):
        for x in range(image.width):
            top = rgb(image.getpixel((x, y)))
            bottom = rgb(image.getpixel((x, min(y + 1, image.height - 1))))
            output.append(
                "▀",
                Style(
                    color="rgb({},{},{})".format(*top),
                    bgcolor="rgb({},{},{})".format(*bottom),
                ),
            )
        if y + 2 < image.height:
            output.append("\n")
    return output
