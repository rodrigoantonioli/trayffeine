from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    active = create_icon(cup="#a05d2a", steam="#f5e2b8", accent="#3e2615")
    inactive = create_icon(cup="#8e98a6", steam="#d7dce3", accent="#41505e")

    active.save(ASSETS / "trayffeine-active.png")
    inactive.save(ASSETS / "trayffeine-inactive.png")
    active.save(
        ASSETS / "trayffeine-app.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def create_icon(*, cup: str, steam: str, accent: str) -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.ellipse((20, 150, 236, 228), fill=(0, 0, 0, 32))
    draw.rounded_rectangle((60, 88, 172, 188), radius=22, fill=cup)
    draw.rounded_rectangle((70, 98, 162, 178), radius=18, fill=accent)
    draw.rounded_rectangle((165, 105, 214, 168), radius=22, outline=cup, width=14)
    draw.rounded_rectangle((72, 184, 200, 198), radius=6, fill=accent)

    draw.line((98, 78, 90, 42), fill=steam, width=12, joint="curve")
    draw.line((126, 74, 126, 30), fill=steam, width=12, joint="curve")
    draw.line((154, 78, 164, 42), fill=steam, width=12, joint="curve")
    return image


if __name__ == "__main__":
    main()

