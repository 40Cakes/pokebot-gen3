def iv_colour(value: int):
    if value == 31:
        return "yellow"
    if value == 0:
        return "purple"
    if value >= 26:
        return "green"
    if value <= 5:
        return "red"
    return "white"


def iv_sum_colour(value: int):
    if value == 186:
        return "yellow"
    if value == 0:
        return "purple"
    if value >= 140:
        return "green"
    if value <= 50:
        return "red"
    return "white"


def sv_colour(value: int):
    if value <= 7:
        return "yellow"
    if value >= 65528:
        return "purple"
    return "red"
