import random
from pathlib import Path

import PIL.Image
import PIL.ImageDraw

from modules.runtime import get_sprites_path


def choose_random_sprite() -> Path:
    """
    :return: Path to a random Pokemon sprite file
    """
    rand = random.randint(0, 99)
    match rand:
        case _ if rand < 10:
            icon_dir = get_sprites_path() / "pokemon" / "shiny"
        case _ if rand < 99:
            icon_dir = get_sprites_path() / "pokemon" / "normal"
        case _:
            icon_dir = get_sprites_path() / "pokemon" / "anti-shiny"

    files = [x for x in icon_dir.glob("*.png") if x.is_file()]

    return random.choice(files)


def crop_sprite_square(path: Path) -> PIL.Image:
    """
    Crops a sprite to the smallest possible size while keeping the image square.
    :param path: Path to the sprite
    :return: Cropped image
    """
    image: PIL.Image = PIL.Image.open(path)
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    bbox = list(image.getbbox())
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    # Make sure the image is sqare (width == height)
    if bbox_width - bbox_height:
        # Wider than high
        missing_height = bbox_width - bbox_height
        bbox[1] -= missing_height // 2
        bbox[3] += missing_height // 2 + (missing_height % 2)
    else:
        # Higher than wide (or equal sizes)
        missing_width = bbox_height - bbox_width
        bbox[0] -= missing_width // 2
        bbox[2] += missing_width // 2 + (missing_width % 2)

    # Make sure we didn't move the bounding box out of scope
    if bbox[0] < 0:
        bbox[2] -= bbox[0]
        bbox[0] = 0
    if bbox[1] < 0:
        bbox[3] -= bbox[1]
        bbox[1] = 0
    if bbox[2] > image.width:
        bbox[0] -= bbox[2] - image.width
        bbox[2] = image.width
    if bbox[3] > image.height:
        bbox[1] -= bbox[3] - image.height
        bbox[3] = image.height

    return image.crop(bbox)


def generate_placeholder_image(width: int, height: int) -> PIL.Image:
    """
    Create a black placeholder image with a random sprite in the middle.
    :param width: Image width
    :param height: Image height
    :return: The generated image
    """
    placeholder = PIL.Image.new(mode="RGBA", size=(width, height))
    draw = PIL.ImageDraw.Draw(placeholder)

    # Black background
    draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill="#000000FF")

    # Paste a random sprite on top
    sprite = PIL.Image.open(choose_random_sprite())
    if sprite.mode != "RGBA":
        sprite = sprite.convert("RGBA")
    sprite_position = (placeholder.width // 2 - sprite.width // 2, placeholder.height // 2 - sprite.height // 2)
    placeholder.paste(sprite, sprite_position, sprite)

    return placeholder
