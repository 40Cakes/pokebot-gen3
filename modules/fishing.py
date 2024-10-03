from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.pokemon import Pokemon


class FishingRod(Enum):
    OldRod = 0
    GoodRod = 1
    SuperRod = 2


class FishingResult(Enum):
    Encounter = auto()
    GotAway = auto()
    Unsuccessful = auto()


@dataclass
class FishingAttempt:
    rod: FishingRod
    result: FishingResult
    encounter: Optional["Pokemon"] = None

    def __eq__(self, other):
        if other is None:
            return False
        elif isinstance(other, FishingAttempt):
            return other.rod is self.rod and other.result is self.result and other.encounter == self.encounter
        else:
            return NotImplemented

    def to_dict(self) -> dict:
        return {
            "rod": self.rod.name,
            "result": self.result.name,
            "encounter": self.encounter.to_dict() if self.encounter is not None else None,
        }
