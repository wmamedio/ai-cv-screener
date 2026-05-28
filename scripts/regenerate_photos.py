"""Regenerate just the photos (and re-render the PDFs) for existing profiles.

Reuses the saved data/profiles/*.json so the CV text — including the seeded
"Jane Doe" / UPC demo facts — stays identical; only the headshot changes.
This is the cheap way to swap photos without re-running text generation.

Usage:
  python scripts/regenerate_photos.py                 # all profiles
  python scripts/regenerate_photos.py jane_doe marco_rossi   # only these slugs
"""
import base64
import sys
import time

from weasyprint import HTML

from generate_cvs import (
    ACCENTS, CV, CVS_DIR, PHOTO_DIR, PROFILE_DIR, TEMPLATE,
    IMAGE_MODEL, generate_photo,
)


def main():
    profiles = sorted(PROFILE_DIR.glob("*.json"))
    if not profiles:
        raise SystemExit(f"No profiles in {PROFILE_DIR} — run generate_cvs.py first.")

    # Accent is keyed to the full-list position so PDFs stay consistent whether
    # we regenerate everything or just a subset.
    accents = {p.stem: ACCENTS[i % len(ACCENTS)] for i, p in enumerate(profiles, 1)}

    only = set(sys.argv[1:])
    selected = [p for p in profiles if p.stem in only] if only else profiles
    if only and not selected:
        raise SystemExit(f"No matching profiles for: {', '.join(sorted(only))}")

    print(f"Regenerating {len(selected)} photo(s) with {IMAGE_MODEL} (+ OpenAI fallback)...\n")
    for n, path in enumerate(selected, 1):
        slug = path.stem
        cv = CV.model_validate_json(path.read_text())

        photo = generate_photo(cv)
        if photo:
            ext = "png" if photo.startswith("data:image/png") else "jpg"
            for old in PHOTO_DIR.glob(f"{slug}.*"):
                old.unlink()
            (PHOTO_DIR / f"{slug}.{ext}").write_bytes(base64.b64decode(photo.split(",", 1)[1]))

        html = TEMPLATE.render(accent=accents[slug], photo_data_uri=photo, **cv.model_dump())
        HTML(string=html).write_pdf(CVS_DIR / f"{slug}.pdf")
        print(f"  [{n:2}/{len(selected)}] {cv.name:28} {cv.title}")
        time.sleep(1.2)

    print(f"\nDone. Photos in {PHOTO_DIR.relative_to(PHOTO_DIR.parents[1])}, "
          f"PDFs re-rendered in {CVS_DIR.relative_to(CVS_DIR.parents[1])}")


if __name__ == "__main__":
    main()
