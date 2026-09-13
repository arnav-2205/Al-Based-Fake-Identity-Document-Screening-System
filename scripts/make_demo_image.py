"""Generate a demo passport image with an embedded <MRZ> EXIF sidecar so the
stub OCR path returns real, controllable data.

    python scripts/make_demo_image.py out.jpg --tampered

Requires: pillow  (pip install pillow)
"""
import argparse

from PIL import Image, ImageDraw

GOOD_MRZ = (
    "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
    "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
)
# passport number check digit deliberately broken -> fails ICAO 9303
TAMPERED_MRZ = GOOD_MRZ.replace("L898902C36", "L898902C99")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--tampered", action="store_true", help="embed an invalid MRZ check digit")
    ap.add_argument("--blacklist", action="store_true", help="use a blacklisted passport number (P1234567)")
    args = ap.parse_args()

    mrz = TAMPERED_MRZ if args.tampered else GOOD_MRZ
    if args.blacklist:
        mrz = mrz.replace("L898902C3", "P1234567<").replace("L898902C99", "P1234567<")

    img = Image.new("RGB", (900, 620), "#e8e4d8")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 250, 300], fill="#b9c4d0")            # portrait box
    d.text((60, 150), "PHOTO", fill="#333")
    d.text((300, 60), "PASSPORT / UTOPIA", fill="#1b1b1b")
    d.text((300, 110), "ERIKSSON, ANNA MARIA", fill="#1b1b1b")
    d.text((300, 150), "Passport No: L898902C3", fill="#1b1b1b")
    d.text((300, 190), "Nationality: UTO   DOB: 12 AUG 1974", fill="#1b1b1b")
    d.text((300, 230), "Expiry: 15 APR 2012", fill="#1b1b1b")
    d.rectangle([40, 520, 860, 590], fill="#f5f2ea")
    for i, line in enumerate(mrz.splitlines()):
        d.text((50, 530 + i * 28), line, fill="#000")

    exif = img.getexif()
    exif[0x9286] = f"<MRZ>{mrz}</MRZ>"     # UserComment
    if args.tampered:
        exif[0x0131] = "Adobe Photoshop 25.0 (Windows)"   # Software tag -> EXIF editor flag

    img.save(args.out, "JPEG", quality=92, exif=exif)
    print(f"wrote {args.out}")
    print(mrz)


if __name__ == "__main__":
    main()
