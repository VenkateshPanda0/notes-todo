"""Generate TaskFlow's brand assets: the Windows app icon and the GitHub social-preview image.

    python scripts/make_assets.py

Requires Pillow (pip install pillow). Outputs:
    backend/taskflow.ico         multi-size icon embedded into TaskFlow.exe by PyInstaller
    docs/assets/social-preview.png  1280x640 image for the repo's social preview / link cards
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BLUE = (37, 99, 235)
FONT_DIRS = [
    Path("/usr/share/fonts/opentype/inter"),
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
]


def logo(size: int) -> Image.Image:
    """The app mark: a blue rounded square with a white check, drawn 4x and downsampled."""
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.22), fill=BLUE)
    width = max(2, int(big * 0.11))
    points = [(big * 0.27, big * 0.52), (big * 0.43, big * 0.68), (big * 0.74, big * 0.34)]
    draw.line(points, fill="white", width=width, joint="curve")
    for x, y in (points[0], points[-1]):  # round the stroke ends
        draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill="white")
    return img.resize((size, size), Image.LANCZOS)


def font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        for name in names:
            path = directory / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def make_icon() -> Path:
    out = ROOT / "backend" / "taskflow.ico"
    logo(256).save(out, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    return out


def make_social_preview() -> Path:
    width, height = 1280, 640
    img = Image.new("RGB", (width, height), (11, 12, 16))
    top, bottom = (11, 12, 16), (19, 30, 56)
    gradient = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        gradient.line(
            [(0, y), (width, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )

    bold = ["Inter-Bold.otf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
    regular = ["Inter-Regular.otf", "arial.ttf", "DejaVuSans.ttf"]
    draw = ImageDraw.Draw(img)

    img.paste(logo(72), (70, 70), logo(72))
    draw.text((158, 82), "TaskFlow", font=font(bold, 44), fill="white")

    headline = font(bold, 68)
    for i, line in enumerate(["Todos and notes,", "entirely on", "your machine."]):
        draw.text((70, 190 + i * 82), line, font=headline, fill="white")

    sub = font(regular, 28)
    draw.text((70, 460), "Markdown notes · [[links]] · graph view", font=sub, fill=(147, 197, 253))
    draw.text((70, 505), "No account. No cloud. Open source.", font=sub, fill=(156, 163, 175))

    shot = Image.open(ROOT / "screenshots" / "all-tasks.jpg").convert("RGB")
    target_w = 700
    shot = shot.resize((target_w, int(shot.height * target_w / shot.width)), Image.LANCZOS)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *shot.size), radius=18, fill=255)
    x, y = width - target_w + 90, 150  # bleeds off the right edge on purpose

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        (x - 6, y - 6, x + shot.width + 6, y + shot.height + 6), radius=22, fill=(37, 99, 235, 110)
    )
    img.paste(glow.filter(ImageFilter.GaussianBlur(28)), (0, 0), glow.filter(ImageFilter.GaussianBlur(28)))
    img.paste(shot, (x, y), mask)

    out = ROOT / "docs" / "assets" / "social-preview.png"
    img.save(out, optimize=True)
    return out


if __name__ == "__main__":
    for path in (make_icon(), make_social_preview()):
        print(f"wrote {os.path.relpath(path, ROOT)}")
