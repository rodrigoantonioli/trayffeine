from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MSIX_ASSETS = ROOT / "packaging" / "msix" / "assets"


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    MSIX_ASSETS.mkdir(parents=True, exist_ok=True)
    active = create_icon(
        cup="#a05d2a",
        steam="#f5e2b8",
        accent="#3e2615",
        pressed=True,
        shadow="#28180d",
    )
    inactive = create_icon(
        cup="#8e98a6",
        steam="#d7dce3",
        accent="#41505e",
        pressed=False,
        shadow="#32404d",
    )
    app_icon = create_icon(
        cup="#a05d2a",
        steam="#f5e2b8",
        accent="#3e2615",
        pressed=False,
        shadow="#28180d",
    )

    active.save(ASSETS / "trayffeine-active.png")
    inactive.save(ASSETS / "trayffeine-inactive.png")
    app_icon.save(
        ASSETS / "trayffeine-app.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    create_msix_visual_assets(app_icon)


def create_msix_visual_assets(app_icon: Image.Image) -> None:
    for filename, size in (
        ("Square44x44Logo.png", (44, 44)),
        ("Square150x150Logo.png", (150, 150)),
        ("StoreLogo.png", (50, 50)),
    ):
        _fit_icon(app_icon, size).save(MSIX_ASSETS / filename)

    wide = Image.new("RGBA", (310, 150), (0, 0, 0, 0))
    logo = _fit_icon(app_icon, (132, 132))
    wide.alpha_composite(logo, ((wide.width - logo.width) // 2, (wide.height - logo.height) // 2))
    wide.save(MSIX_ASSETS / "Wide310x150Logo.png")


def _fit_icon(app_icon: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    logo = app_icon.copy()
    logo.thumbnail(size, Image.Resampling.LANCZOS)
    image.alpha_composite(logo, ((size[0] - logo.width) // 2, (size[1] - logo.height) // 2))
    return image


def create_icon(*, cup: str, steam: str, accent: str, pressed: bool, shadow: str) -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    body_top = 94 if pressed else 88
    body_bottom = 194 if pressed else 188
    handle_top = 111 if pressed else 105
    handle_bottom = 174 if pressed else 168
    base_top = 190 if pressed else 184
    base_bottom = 204 if pressed else 198
    inner_top = 104 if pressed else 98
    inner_bottom = 184 if pressed else 178

    draw.ellipse((20, 150, 236, 228), fill=(0, 0, 0, 32))
    draw.rounded_rectangle((58, body_top + 4, 174, body_bottom + 6), radius=24, fill=shadow)
    draw.rounded_rectangle((60, body_top, 172, body_bottom), radius=22, fill=cup)
    draw.rounded_rectangle((70, inner_top, 162, inner_bottom), radius=18, fill=accent)
    draw.rounded_rectangle((165, handle_top, 214, handle_bottom), radius=22, outline=cup, width=14)
    draw.rounded_rectangle((72, base_top, 200, base_bottom), radius=6, fill=accent)
    draw.rounded_rectangle(
        (72, body_top + 8, 160, body_top + 20),
        radius=8,
        fill=(255, 255, 255, 32),
    )

    draw.line((98, 78, 90, 42), fill=steam, width=12, joint="curve")
    draw.line((126, 74, 126, 30), fill=steam, width=12, joint="curve")
    draw.line((154, 78, 164, 42), fill=steam, width=12, joint="curve")
    return image


if __name__ == "__main__":
    main()
