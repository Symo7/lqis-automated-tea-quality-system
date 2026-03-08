from __future__ import annotations

from PIL import Image, ImageFilter, ImageStat


def _class_from_score(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Fair"
    return "Poor"


def run_baseline_prediction(image_field_file) -> dict:
    image_field_file.open("rb")
    image = Image.open(image_field_file).convert("RGB")
    image_small = image.resize((128, 128))

    stat = ImageStat.Stat(image_small)
    r_avg, g_avg, b_avg = stat.mean
    brightness = (r_avg + g_avg + b_avg) / 3.0

    green_pixels = 0
    total_pixels = image_small.width * image_small.height
    for r, g, b in image_small.getdata():
        if g > r * 1.05 and g > b * 1.05 and g > 45:
            green_pixels += 1
    green_ratio = green_pixels / max(total_pixels, 1)

    gray = image_small.convert("L")
    texture_std = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0]

    leaf_density_proxy = max(0.0, min(1.0, (255 - brightness) / 255))
    texture_proxy = max(0.0, min(1.0, texture_std / 100))
    brightness_proxy = max(0.0, min(1.0, 1 - abs(brightness - 120) / 120))

    score = int(
        100
        * (
            0.45 * green_ratio
            + 0.2 * brightness_proxy
            + 0.2 * texture_proxy
            + 0.15 * leaf_density_proxy
        )
    )
    score = max(0, min(100, score))
    confidence = round(60 + (green_ratio * 25) + (texture_proxy * 15), 2)
    confidence = max(0.0, min(100.0, confidence))

    return {
        "predicted_pluck_class": _class_from_score(score),
        "predicted_pluck_score": score,
        "confidence": confidence,
        "metrics": {
            "green_ratio": round(green_ratio, 4),
            "brightness": round(brightness, 2),
            "texture_proxy": round(texture_proxy, 4),
            "leaf_density_proxy": round(leaf_density_proxy, 4),
        },
    }
