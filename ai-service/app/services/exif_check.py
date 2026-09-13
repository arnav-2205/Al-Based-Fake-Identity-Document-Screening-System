"""EXIF metadata analysis (Spec Part 1, case #13).

Editing-software signatures and timestamp inconsistencies are supporting
evidence alongside ELA.
"""
from __future__ import annotations

import io

from PIL import Image, ExifTags

_EDITOR_HINTS = ("photoshop", "gimp", "lightroom", "affinity", "paint.net", "pixlr", "snapseed")


def analyse_exif(data: bytes) -> dict:
    result: dict = {"hasExif": False, "software": None, "editorDetected": False, "notes": []}
    try:
        img = Image.open(io.BytesIO(data))
        exif = img.getexif()
        if not exif:
            result["notes"].append("No EXIF metadata (common for scans/screenshots)")
            return result
        result["hasExif"] = True
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        software = str(tags.get("Software", "") or "")
        result["software"] = software or None
        if any(h in software.lower() for h in _EDITOR_HINTS):
            result["editorDetected"] = True
            result["notes"].append(f"Image processed by editing software: {software}")
        dt_original = tags.get("DateTimeOriginal")
        dt_modified = tags.get("DateTime")
        if dt_original and dt_modified and dt_original != dt_modified:
            result["notes"].append(
                f"Timestamp inconsistency: original={dt_original} modified={dt_modified}")
    except Exception as exc:  # noqa: BLE001
        result["notes"].append(f"EXIF parse error: {exc}")
    return result
