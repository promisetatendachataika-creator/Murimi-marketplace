"""
Checking and cleaning uploaded photos (never trust the browser).

1. Size: at most 10 MB.
2. Type: decided by READING THE FILE'S BYTES with Pillow, not by its name or the
   browser's label (same rule as the Hub's documents app). Only JPEG, PNG and WebP.
3. Re-saved as a fresh JPEG, at most 1600 px: this throws away anything hidden in
   the file, including the phone's GPS location (EXIF), which would show where the
   farm or the farmer's home is.
"""
import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {"JPEG", "PNG", "WEBP"}
MAX_SIDE = 1600
MAX_PIXELS = 40_000_000       # refuse "decompression bombs" (tiny files that unpack to huge images)


class PhotoError(ValueError):
    pass


def clean_photo(upload):
    """Return a ContentFile with a safe JPEG, or raise PhotoError with a friendly message."""
    name = getattr(upload, "name", "photo")
    if upload.size > MAX_BYTES:
        raise PhotoError(f'"{name}" is bigger than 10 MB.')
    try:
        with Image.open(upload) as probe:
            kind = probe.format
            if probe.width * probe.height > MAX_PIXELS:
                raise PhotoError(f'"{name}" is too large in pixels.')
            probe.verify()                          # checks the file isn't broken
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise PhotoError(f'"{name}" isn\'t a photo we can open.')
    if kind not in ALLOWED:
        raise PhotoError(f'"{name}" must be a JPG, PNG or WebP photo.')

    upload.seek(0)
    with Image.open(upload) as img:
        img = ImageOps.exif_transpose(img)        # keep it the right way up...
        img = img.convert("RGB")                  # ...then drop transparency and all metadata
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return ContentFile(out.getvalue(), name=f"{uuid.uuid4().hex}.jpg")
