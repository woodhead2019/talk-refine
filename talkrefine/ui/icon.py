"""Shared app icon generator — microphone with sparkle/magic star."""

from PIL import Image, ImageDraw


def create_app_icon(size: int = 128) -> Image.Image:
    """Create the TalkRefine icon: microphone + magic sparkle star."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size / 128  # scale factor

    # ── Microphone ──
    # Head (rounded rect)
    draw.rounded_rectangle(
        [int(32*s), int(16*s), int(80*s), int(72*s)],
        radius=int(20*s), fill="#a6e3a1")
    # Arc
    draw.arc(
        [int(22*s), int(40*s), int(90*s), int(96*s)],
        start=0, end=180, fill="#cdd6f4", width=max(int(4*s), 1))
    # Stand
    draw.line(
        [int(56*s), int(96*s), int(56*s), int(114*s)],
        fill="#cdd6f4", width=max(int(4*s), 1))
    draw.line(
        [int(40*s), int(114*s), int(72*s), int(114*s)],
        fill="#cdd6f4", width=max(int(4*s), 1))

    # ── Magic sparkle star (top-right) ──
    cx, cy = int(100*s), int(24*s)  # center of star
    r = int(14*s)   # outer radius
    ri = int(5*s)   # inner radius
    color = "#f9e2af"  # golden yellow

    # 4-pointed star
    points = []
    import math
    for i in range(8):
        angle = math.pi / 2 * (i / 2) - math.pi / 2
        radius = r if i % 2 == 0 else ri
        px = cx + int(radius * math.cos(angle))
        py = cy + int(radius * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=color)

    # Small sparkle dots around the star
    dot_r = max(int(2*s), 1)
    for dx, dy in [(-18, -6), (18, -8), (8, 18), (-10, 16)]:
        x, y = cx + int(dx*s), cy + int(dy*s)
        draw.ellipse([x-dot_r, y-dot_r, x+dot_r, y+dot_r], fill=color)

    return img
