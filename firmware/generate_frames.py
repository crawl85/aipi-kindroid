"""Convert two sets of portrait PNGs to the firmware's RGB565 headers."""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

SIDE = 96
FRAMES = ("Closed", "Parted", "Open", "Blink")


def encode_frame(path):
    with Image.open(path) as image:
        fitted = ImageOps.fit(image.convert("RGB"), (SIDE, SIDE))
        pixels = bytearray()
        for red, green, blue in fitted.getdata():
            value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
            pixels.extend(value.to_bytes(2, "little"))
    return pixels


def render_header(folder, prefix):
    lines = ["#pragma once", "#include <cstdint>", ""]
    if not prefix:
        lines.append(f"inline constexpr int kAvatarSize = {SIDE};")
    for frame in FRAMES:
        symbol = f"k{prefix}{frame}"
        pixels = encode_frame(folder / f"{frame.lower()}.png")
        lines.append(f"alignas(4) inline constexpr uint8_t {symbol}[] = {{")
        for offset in range(0, len(pixels), 16):
            row = ", ".join(f"0x{byte:02x}" for byte in pixels[offset:offset + 16])
            lines.append(f"    {row},")
        lines.extend(["};", f"static_assert(sizeof({symbol}) == {SIDE * SIDE * 2});", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("default_frames", type=Path)
    parser.add_argument("alternate_frames", type=Path)
    parser.add_argument("board_directory", type=Path)
    args = parser.parse_args()
    default_header = render_header(args.default_frames, "")
    alternate_header = render_header(args.alternate_frames, "Harley")
    (args.board_directory / "gamora_frames.h").write_text(default_header)
    (args.board_directory / "harley_frames.h").write_text(alternate_header)


if __name__ == "__main__":
    main()
