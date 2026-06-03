from __future__ import annotations

import io
import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

SCREEN_RESOLUTIONS: dict[str, tuple[int, int]] = {
    "hd": (1280, 720),
    "full_hd": (1920, 1080),
    "2k": (2560, 1440),
    "4k": (3840, 2160),
}

MAX_DIMENSION = 3840


def detect_screen_resolution() -> tuple[int, int]:
    try:
        result = subprocess.run(
            ["xrandr"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            max_w, max_h = 0, 0
            for line in result.stdout.splitlines():
                if " connected" in line:
                    for token in line.split():
                        if "x" in token and token[0].isdigit():
                            try:
                                dims = token.split("+")[0]
                                w_s, h_s = dims.split("x")
                                w, h = int(w_s), int(h_s)
                                if w > max_w:
                                    max_w = w
                                if h > max_h:
                                    max_h = h
                            except (ValueError, IndexError):
                                continue
            if max_w > 0 and max_h > 0:
                logger.debug(
                    "Detected screen resolution via xrandr: %dx%d",
                    max_w, max_h,
                )
                return (max_w, max_h)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    wayland = os.environ.get("WAYLAND_DISPLAY")
    if wayland:
        xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "sway" in xdg_desktop:
            try:
                result = subprocess.run(
                    ["swaymsg", "-t", "get_outputs"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    outputs = json.loads(result.stdout)
                    max_w, max_h = 0, 0
                    for output in outputs:
                        rect = output.get("rect", {})
                        w, h = rect.get("width", 0), rect.get("height", 0)
                        if w > max_w:
                            max_w = w
                        if h > max_h:
                            max_h = h
                    if max_w > 0 and max_h > 0:
                        logger.debug(
                            "Detected screen resolution via swaymsg: %dx%d",
                            max_w, max_h,
                        )
                        return (max_w, max_h)
            except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass

    logger.debug("Could not detect screen resolution, defaulting to Full HD")
    return (1920, 1080)


def get_target_resolution(config_resolution: str) -> tuple[int, int]:
    if config_resolution == "original":
        return (0, 0)

    res = SCREEN_RESOLUTIONS.get(config_resolution)
    if res:
        return res

    screen = detect_screen_resolution()
    return (min(screen[0], MAX_DIMENSION), min(screen[1], MAX_DIMENSION * 1080 // 1920))


def optimize_image(data: bytes, max_width: int, max_height: int) -> bytes:
    if max_width <= 0 or max_height <= 0:
        return data

    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as img:
            original_w, original_h = img.size

            if original_w <= max_width and original_h <= max_height:
                logger.debug(
                    "Image %dx%d within limits %dx%d, no resize needed",
                    original_w, original_h, max_width, max_height,
                )
                return data

            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            output = io.BytesIO()
            save_format = img.format or "JPEG"
            save_kwargs: dict = {}
            if save_format.upper() == "JPEG":
                img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
                save_kwargs["quality"] = 90
                save_kwargs["optimize"] = True
                save_format = "JPEG"
            elif save_format.upper() == "PNG":
                save_kwargs["optimize"] = True
                save_format = "PNG"
            elif save_format.upper() == "WEBP":
                save_kwargs["quality"] = 90
                save_format = "WEBP"

            img.save(output, format=save_format, **save_kwargs)
            result = output.getvalue()

            logger.info(
                "Optimized image: %dx%d -> %dx%d (%.1f%% of original)",
                original_w, original_h,
                img.size[0], img.size[1],
                len(result) / len(data) * 100 if data else 0,
            )
            return result

    except ImportError:
        logger.warning("Pillow not available, skipping image optimization")
        return data
    except Exception as e:
        logger.warning("Image optimization failed: %s", e)
        return data
