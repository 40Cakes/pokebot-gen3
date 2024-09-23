from dataclasses import dataclass
from enum import Enum, auto

from modules.context import context
from modules.memory import read_symbol, unpack_uint16


class TextPrinterState(Enum):
    PrintingCharacter = auto()
    Scrolling = auto()
    WaitForButton = auto()
    PlayingSound = auto()
    Unknown = auto()


@dataclass
class TextPrinter:
    active: bool
    state: TextPrinterState
    raw_state: str

    @classmethod
    def from_rs_window_struct(cls, data: bytes) -> "TextPrinter":
        raw_state = "unknown"
        state = TextPrinterState.Unknown
        match unpack_uint16(data[0x16:0x18]):
            case 0:
                raw_state = "End"
            case 1:
                raw_state = "Begin"
            case 2:
                raw_state = "Normal"
            case 3:
                raw_state = "CharDelay"
                state = TextPrinterState.PrintingCharacter
            case 4:
                raw_state = "Pause"
            case 5:
                raw_state = "WaitButton"
            case 6:
                raw_state = "Newline"
            case 7:
                raw_state = "Placeholder"
            case 8:
                raw_state = "WaitClear"
                state = TextPrinterState.WaitForButton
            case 9:
                raw_state = "WaitScroll"
                state = TextPrinterState.WaitForButton
            case 10:
                raw_state = "WaitSound"
                state = TextPrinterState.PlayingSound

        return TextPrinter(
            active=raw_state != "End",
            state=state,
            raw_state=raw_state,
        )

    @classmethod
    def from_emerald_frlg_text_printer_struct(cls, data: bytes) -> "TextPrinter":
        raw_state = "unknown"
        state = TextPrinterState.Unknown
        match data[0x1C]:
            case 0:
                raw_state = "HandleCharacter"
                state = TextPrinterState.PrintingCharacter
            case 1:
                raw_state = "Wait"
            case 2:
                raw_state = "Clear"
                state = TextPrinterState.WaitForButton
            case 3:
                raw_state = "ScrollStart"
                state = TextPrinterState.WaitForButton
            case 4:
                raw_state = "Scroll"
                state = TextPrinterState.Scrolling
            case 5:
                raw_state = "WaitSE"
                state = TextPrinterState.PlayingSound
            case 6:
                raw_state = "Pause"

        return TextPrinter(
            active=bool(data[0x1B]),
            state=state,
            raw_state=raw_state,
        )


def get_text_printer(index: int = 0) -> TextPrinter:
    if context.rom.is_rs:
        if index == 0:
            symbol = "gWindowTemplate_Contest_MoveDescription"
        else:
            symbol = "gMenuWindow"

        data = read_symbol(symbol)
        return TextPrinter.from_rs_window_struct(data)
    else:
        data = read_symbol("sTextPrinters", offset=0x24 * index, size=0x24)
        return TextPrinter.from_emerald_frlg_text_printer_struct(data)
