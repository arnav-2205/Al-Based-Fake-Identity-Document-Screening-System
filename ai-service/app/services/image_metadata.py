"""Lightweight Image Metadata Analysis Module (Spec P1.7)
Audits image headers, EXIF tags, format consistency, software signatures, and timestamp anomalies.
"""
import io
import re
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ExifTags

_EDITOR_SIGNATURES = (
    "photoshop", "gimp", "lightroom", "affinity", "paint.net",
    "pixlr", "snapseed", "canva", "picsart", "adobe", "exiftool"
)


def extract_image_metadata(data: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
    """Extracts raw available metadata without fabricating missing values."""
    if not data:
        return {
            "format": "NONE",
            "width": None,
            "height": None,
            "mode": None,
            "fileSize": 0,
            "exifPresent": False,
            "cameraMake": None,
            "cameraModel": None,
            "software": None,
            "dateTimeOriginal": None,
            "dateTime": None,
            "dateTimeDigitized": None,
            "orientation": None,
            "gpsPresent": False,
            "formatMismatch": False,
        }

    file_size = len(data)

    # Detect SVG / Vector documents gracefully
    header_start = data[:100].lower()
    if b"<svg" in header_start or b"<?xml" in header_start:
        return {
            "format": "SVG",
            "width": None,
            "height": None,
            "mode": "VECTOR",
            "fileSize": file_size,
            "exifPresent": False,
            "cameraMake": None,
            "cameraModel": None,
            "software": None,
            "dateTimeOriginal": None,
            "dateTime": None,
            "dateTimeDigitized": None,
            "orientation": None,
            "gpsPresent": False,
            "formatMismatch": False,
        }

    # Attempt raster image inspection via Pillow
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format or "UNKNOWN"
        w, h = img.size
        mode = img.mode

        camera_make = None
        camera_model = None
        software = None
        dt_orig = None
        dt_mod = None
        dt_dig = None
        orientation = None
        gps_present = False
        exif_present = False

        exif_data = img.getexif()
        if exif_data:
            exif_present = True
            tags = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items()}

            camera_make = str(tags.get("Make", "") or "").strip() or None
            camera_model = str(tags.get("Model", "") or "").strip() or None
            software = str(tags.get("Software", "") or "").strip() or None
            dt_orig = str(tags.get("DateTimeOriginal", "") or "").strip() or None
            dt_mod = str(tags.get("DateTime", "") or "").strip() or None
            dt_dig = str(tags.get("DateTimeDigitized", "") or "").strip() or None
            orientation = tags.get("Orientation")

            # Check for GPS tag (34853) presence without exposing coordinates
            if 34853 in exif_data:
                gps_present = True

        # Check for filename extension vs actual encoding format mismatch
        format_mismatch = False
        if filename:
            fn_lower = filename.lower()
            if fn_lower.endswith((".jpg", ".jpeg")) and fmt.upper() not in ("JPEG", "JPG"):
                format_mismatch = True
            elif fn_lower.endswith(".png") and fmt.upper() != "PNG":
                format_mismatch = True
            elif fn_lower.endswith(".svg") and fmt.upper() != "SVG":
                format_mismatch = True

        return {
            "format": fmt,
            "width": w,
            "height": h,
            "mode": mode,
            "fileSize": file_size,
            "exifPresent": exif_present,
            "cameraMake": camera_make,
            "cameraModel": camera_model,
            "software": software,
            "dateTimeOriginal": dt_orig,
            "dateTime": dt_mod,
            "dateTimeDigitized": dt_dig,
            "orientation": orientation,
            "gpsPresent": gps_present,
            "formatMismatch": format_mismatch,
        }
    except Exception:
        return {
            "format": "UNKNOWN",
            "width": None,
            "height": None,
            "mode": None,
            "fileSize": file_size,
            "exifPresent": False,
            "cameraMake": None,
            "cameraModel": None,
            "software": None,
            "dateTimeOriginal": None,
            "dateTime": None,
            "dateTimeDigitized": None,
            "orientation": None,
            "gpsPresent": False,
            "formatMismatch": False,
        }


def analyze_image_metadata(data: Any, filename: Optional[str] = None) -> Dict[str, Any]:
    """Performs observational forensic evaluation on extracted image metadata."""
    if isinstance(data, dict):
        meta = data
    else:
        meta = extract_image_metadata(data, filename)

    reasons: List[str] = []
    signals: List[str] = []

    # SVG / Vector Handling
    if meta["format"] == "SVG":
        return {
            "status": "NOT_AVAILABLE",
            "confidence": 0.95,
            "signals": ["VECTOR_DOCUMENT"],
            "metadata": meta,
            "reasons": ["Vector/SVG document provided; EXIF metadata not applicable."],
        }

    # Missing EXIF metadata -> NOT_AVAILABLE (0 points)
    if not meta["exifPresent"]:
        reasons.append("No EXIF metadata embedded in document image.")
        if meta["formatMismatch"]:
            reasons.append("File extension disagrees with internal image container, but file conversion may be benign.")
            signals.extend(["FORMAT_MISMATCH_OBSERVED", "FILE_EXTENSION_FORMAT_MISMATCH"])
            return {
                "status": "INCONCLUSIVE",
                "confidence": 0.70,
                "signals": signals,
                "metadata": meta,
                "reasons": reasons,
            }
        return {
            "status": "NOT_AVAILABLE",
            "confidence": 0.0,
            "signals": ["NO_EXIF"],
            "metadata": meta,
            "reasons": reasons,
        }

    # Evaluate indicators
    software = meta.get("software")
    editor_detected = False
    if software:
        if any(sig in software.lower() for sig in _EDITOR_SIGNATURES):
            editor_detected = True

    dt_orig = meta.get("dateTimeOriginal")
    dt_mod = meta.get("dateTime")
    timestamp_contradiction = False

    if dt_orig and dt_mod:
        if dt_orig != dt_mod:
            if dt_mod > dt_orig:
                timestamp_contradiction = True
                signals.append("TIMESTAMP_MODIFIED_AFTER_CAPTURE")
                reasons.append(f"Modification timestamp ({dt_mod}) is later than capture date ({dt_orig}).")
            elif dt_mod < dt_orig:
                timestamp_contradiction = True
                signals.append("TIMESTAMP_MODIFIED_BEFORE_CAPTURE")
                reasons.append(f"Modification timestamp ({dt_mod}) precedes capture date ({dt_orig}).")

    if meta["cameraMake"] or meta["cameraModel"]:
        signals.append("CAMERA_METADATA_PRESENT")

    if meta["gpsPresent"]:
        signals.append("GPS_METADATA_PRESENT")

    if meta["formatMismatch"]:
        signals.append("FILE_EXTENSION_FORMAT_MISMATCH")

    # Classification logic
    if editor_detected and timestamp_contradiction:
        signals.extend(["EDITING_SOFTWARE_DETECTED", "TIMESTAMP_CONTRADICTION"])
        reasons.insert(0, f"Image metadata identifies image-editing software ({software}) with conflicting modification timestamps.")
        return {
            "status": "SUSPICIOUS",
            "confidence": 0.85,
            "signals": signals,
            "metadata": meta,
            "reasons": reasons,
        }

    if editor_detected:
        signals.extend(["EDITING_SOFTWARE_DETECTED", "SOFTWARE_TAG_OBSERVED"])
        reasons.append(f"Image metadata identifies software tag ({software}), but evidence is insufficient alone to determine document manipulation.")
        return {
            "status": "INCONCLUSIVE",
            "confidence": 0.75,
            "signals": signals,
            "metadata": meta,
            "reasons": reasons,
        }

    if timestamp_contradiction:
        signals.append("TIMESTAMP_INCONSISTENCY")
        reasons.append("Metadata contains timestamp inconsistencies, but evidence is insufficient to determine document manipulation.")
        return {
            "status": "INCONCLUSIVE",
            "confidence": 0.70,
            "signals": signals,
            "metadata": meta,
            "reasons": reasons,
        }

    if meta["formatMismatch"]:
        signals.append("FORMAT_MISMATCH_OBSERVED")
        reasons.append("File extension disagrees with internal image container, but file conversion may be benign.")
        return {
            "status": "INCONCLUSIVE",
            "confidence": 0.70,
            "signals": signals,
            "metadata": meta,
            "reasons": reasons,
        }

    # Clean camera / standard metadata
    reasons.append("Standard image metadata detected; no suspicious metadata indicators.")
    signals.append("STANDARD_METADATA")
    return {
        "status": "CLEAN",
        "confidence": 0.95,
        "signals": signals,
        "metadata": meta,
        "reasons": reasons,
    }
