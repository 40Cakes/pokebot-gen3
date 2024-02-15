from datetime import datetime
from pathlib import Path

from modules.context import context
from modules.pokemon import Pokemon

from PIL import Image, ImageDraw, ImageFont, ImageSequence

from modules.runtime import get_sprites_path
from modules.version import pokebot_name


TCG_REVISION = "Rev. 1.0"


def suffix(d):
    return {1: "st", 2: "nd", 3: "rd"}.get(d % 20, "th")


def custom_strftime(format, t):
    return t.strftime(format).replace("{S}", str(t.day) + suffix(t.day))


def resize_image(image: Image, factor: int) -> Image:
    return image.resize(size=tuple(factor * x for x in image.size), resample=Image.NEAREST)


def draw_text(
    draw: ImageDraw,
    text: str,
    coords: tuple[int, int] = (0, 0),
    size: int = 15,
    text_colour: str = "#FFF",
    shadow_colour: str = "#6B5A73",
    anchor: str = "lt",
) -> ImageDraw:
    font = ImageFont.truetype(font=str(Path(__file__).parent / "fonts" / "pokemon-rs.ttf"), size=size)

    # Draw text shadow
    draw.text(
        xy=(coords[0] + (size / 15), coords[1] + (size / 15)), text=text, fill=shadow_colour, font=font, anchor=anchor
    )

    # Draw text
    draw.text(xy=(coords[0], coords[1]), text=text, fill=text_colour, font=font, anchor=anchor)

    return draw


def generate_tcg_card(pokemon: Pokemon, gif_path: Path) -> None:
    tcg_sprites = get_sprites_path() / "tcg"

    # Set up base, transparent card image, add border
    card = Image.new("RGBA", (620, 850), (255, 255, 255, 0))
    card_border = Image.open(tcg_sprites / "border.png")
    card.paste(card_border, (0, 0), mask=card_border)

    # Type background
    background = Image.open(tcg_sprites / "background" / f"{pokemon.species.types[0]}.png")
    card.paste(background, (29, 30))

    # Type portrait border
    border = Image.open(tcg_sprites / "border" / f"{pokemon.species.types[0]}.png")
    card.paste(border, (59, 94), mask=border)

    # PKMN data
    pkmn_data = Image.open(tcg_sprites / "pkmn_data.png")
    card.paste(pkmn_data, (235, 426), mask=pkmn_data)

    # Type name plate
    name_plate = Image.open(tcg_sprites / "name_plate" / f"{pokemon.species.types[0]}.png")
    card.paste(name_plate, (67, 58), mask=name_plate)

    # Primary type
    type_1 = resize_image(Image.open(get_sprites_path() / "types" / f"{pokemon.species.types[0]}.png"), 2)
    card.paste(type_1, (480, 74), mask=type_1)

    # Secondary type
    if len(pokemon.species.types) > 1:
        type_2 = resize_image(Image.open(get_sprites_path() / "types" / f"{pokemon.species.types[1]}.png"), 2)
        card.paste(type_2, (480, 46), mask=type_2)

    draw = ImageDraw.Draw(card)

    # Game of origin badge
    game_badge = (572, 36, 584, 48)
    match pokemon.game_of_origin:
        case "Sapphire":
            draw.rectangle(game_badge, fill="#0021F3")
        case "Ruby":
            draw.rectangle(game_badge, fill="#9B111E")
        case "Emerald":
            draw.rectangle(game_badge, fill="#009C4A")
        case "FireRed":
            draw.ellipse(game_badge, fill="#FFAC1C")
        case "LeafGreen":
            draw.ellipse(game_badge, fill="#AAFF00")
        case _:
            draw.rectangle(game_badge, fill="#000")

    # Shiny badge
    if pokemon.is_shiny:
        shiny = Image.open(tcg_sprites / "shiny.png")
        card.paste(shiny, (567, 55), mask=shiny)

    # Name text
    draw = draw_text(draw, text=pokemon.species.name, coords=(192, 78), size=30, anchor="mm")

    # Nat dex number
    draw = draw_text(
        draw,
        text=f"{pokemon.species.national_dex_number:03} / 386",
        coords=(557, 442),
        shadow_colour="#000",
        anchor="rm",
    )

    # Bot version + date
    draw = draw_text(
        draw,
        text=f"{pokebot_name} ~ {TCG_REVISION} ~ {custom_strftime('%b {S}, %Y', datetime.now())}",
        coords=(33, 804),
        shadow_colour="#000",
        anchor="lm",
    )

    # Copyright text
    draw = draw_text(
        draw,
        text=f"(c)1995-{datetime.now().strftime('%Y')} Nintendo, Creatures, GAMEFREAK",
        coords=(588, 804),
        shadow_colour="#000",
        anchor="rm",
    )

    # Moves
    for i, move in enumerate(pokemon.moves):
        if move:
            draw = draw_text(
                draw, text=move.move.name, coords=(130, 480 + (i * 80)), size=30, shadow_colour="#000", anchor="lm"
            )
            draw = draw_text(
                draw,
                text=move.move.description,
                coords=(130, 505 + (i * 80)),
                size=15,
                shadow_colour="#000",
                anchor="lm",
            )
            draw = draw_text(
                draw,
                text=str(move.move.base_power),
                coords=(525, 496 + (i * 80)),
                size=30,
                shadow_colour="#000",
                anchor="rm",
            )
            move_type = Image.open(get_sprites_path() / "types" / "swsh" / f"{move.move.type}.png")
            card.paste(move_type, (80, 473 + (i * 80)), mask=move_type)

    # Portrait image screenshot
    gif = Image.open(gif_path)
    gif = ImageSequence.Iterator(gif)
    first_frame = resize_image(gif[0], 2).convert("RGBA")
    card.paste(first_frame, (70, 105), mask=first_frame)

    # IVs
    ivs = Image.open(tcg_sprites / "ivs.png")
    card.paste(ivs, (324, 255), mask=ivs)
    draw = draw_text(
        draw, text=str(pokemon.ivs.hp), coords=(375, 274), text_colour="#000", shadow_colour="#DED7B5", anchor="lm"
    )
    draw = draw_text(
        draw, text=str(pokemon.ivs.attack), coords=(434, 274), text_colour="#000", shadow_colour="#DED7B5", anchor="lm"
    )
    draw = draw_text(
        draw, text=str(pokemon.ivs.defence), coords=(491, 274), text_colour="#000", shadow_colour="#DED7B5", anchor="lm"
    )
    draw = draw_text(
        draw,
        text=str(pokemon.ivs.special_attack),
        coords=(381, 297),
        text_colour="#000",
        shadow_colour="#DED7B5",
        anchor="lm",
    )
    draw = draw_text(
        draw,
        text=str(pokemon.ivs.special_defence),
        coords=(434, 297),
        text_colour="#000",
        shadow_colour="#DED7B5",
        anchor="lm",
    )
    draw = draw_text(
        draw, text=str(pokemon.ivs.speed), coords=(491, 297), text_colour="#000", shadow_colour="#DED7B5", anchor="lm"
    )

    # Game text box
    # draw.rectangle((89, 342, 531, 412), fill="#6BA5A5")  # Blanks text box on Emerald screenshot, useful for testing
    draw = draw_text(draw, text=f"Nature: {pokemon.nature.name}", coords=(525, 360), size=30, anchor="rm")
    draw = draw_text(draw, text=f"Ability: {pokemon.ability.name}", coords=(525, 395), size=30, anchor="rm")
    draw = draw_text(draw, text=f"OT: {pokemon.original_trainer.name}", coords=(95, 360), size=30, anchor="lm")
    draw = draw_text(draw, text=f"OTID: {pokemon.original_trainer.id:05}", coords=(95, 395), size=30, anchor="lm")

    # Exp bar
    draw.rectangle((386, 321, 386 + ((pokemon.ivs.sum() / 186) * 128), 324), fill="#42CEFF")

    # Save card
    card_file = f"{pokemon.species.national_dex_number:03}"

    if pokemon.is_shiny:
        card_file = f"{card_file} ★"

    card_file = (
        f"{card_file} - {pokemon.name} - {pokemon.nature} "
        f"[{pokemon.ivs.sum()}] - {hex(pokemon.personality_value)[2:].upper()}.png"
    )

    cards_dir = context.profile.path / "screenshots" / "cards"

    if not cards_dir.exists():
        cards_dir.mkdir(parents=True)

    card_file = str(cards_dir / card_file)

    card.save(card_file)
