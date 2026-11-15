"""Seed account avatars from bundled images without external runtime requests."""

import urllib.error
from io import BytesIO

from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError


def profile_picture_matches(api, user, employee):
    """Compare rendered avatars, allowing small resize/compression differences.

    Default generated avatars do not match. Failed lookups produce the same
    cosmetic warning as a mismatch; they never block recovery.
    """
    if not user.get('last_picture_update', 0):
        return False
    try:
        staff = api.find('/users/username/' + employee)
        if not staff or not staff.get('last_picture_update', 0):
            return False
        pictures = []
        for user_id in (user['id'], staff['id']):
            with Image.open(BytesIO(api.get_profile_image(user_id))) as image:
                # Compare what is visible on a white background, not hidden RGB
                # values in transparent pixels. Both endpoints use the same crop.
                image = image.convert('RGBA')
                background = Image.new('RGBA', image.size, 'white')
                background.alpha_composite(image)
                pictures.append(background.convert('RGB').resize((32, 32)))
        difference = ImageChops.difference(*pictures)
        return sum(ImageStat.Stat(difference).mean) / 3 <= 12
    except (OSError, urllib.error.URLError, UnidentifiedImageError, Image.DecompressionBombError):
        return False
