# -*- coding: utf-8 -*-
"""
Unit tests for modules/map.py
"""

import unittest
import modules.map

from modules.pokemon_party import PartyPokemon
from modules.pokemon import get_species_by_index

# Common lead definitions
regular_lead = bytearray(
    b"\xe3\xbc\xb1\x149\xe9\xca\xb7\xbc\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02\x02\xca\xd9\xe8\xd9\xff\xff\xff\x00\xe6\x81\x00\x00\xc4T{\xa3\xdaE{\xa3\xda&{\xa3\xdaU{\xa3\xdaU{\xa3\xdaU{\xa3\xa8J\xfd\xb27\x0f\x83\x8d\xdaU{\xa3\xfbU+\xa2\xc6UW\xa3\xf9}t\xba\x00\x00\x00\x00\x10\xff'\x00'\x00\x1a\x00\x13\x00\x10\x00\x11\x00\x13\x00"
)
magnet_pull = bytearray(
    b'Z\xae\xad\xf09\xe9\xca\xb7\xc7\xbb\xc1\xc8\xbf\xc7\xc3\xce\xbf\xff\x02\x02\xca\xd9\xe8\xd9\xff\xff\xff\x00\xd6\t\x00\x002GgGcqgGc\x08gGcGgGcGgGcGgG7GWGRG1G}SsS\x11y\xffVA\xa8{[cGgG\x00\x00\x00\x00\x18\xff$\x00.\x00\x1d\x00-\x00\x1c\x002\x00"\x00'
)
static = bytearray(
    b'"p\xd7.9\xe9\xca\xb7\xca\xc3\xc5\xbb\xbd\xc2\xcf\xff%\x00\x02\x02\xca\xd9\xe8\xd9\xff\xff\xff\x00\xc9a\x00\x00\x02\x99\x1d\x99\x12\xa4\x1d\x99\x1b\xdc\x1d\x99\x1b\x99\x1d\x99\x1b\x99\x1d\x99\x1b\x99\x1d\x99M\x99\x7f\x99s\x99\x08\x99\x0f\x87\x12\x8di\xa0\x84\xb0R\xb8\xe6\xbe\x1b\x99\x1d\x99\x00\x00\x00\x00\x19\xff6\x006\x00#\x00\x18\x001\x00%\x00\x1d\x00'
)
pressure = bytearray(
    b"=\x05\xce[9\xe9\xca\xb7\xbe\xcf\xcd\xbd\xc6\xc9\xca\xcd\xff\x00\x02\x02\xca\xd9\xe8\xd9\xff\xff\xff\x00\x00a\x00\x00\x04\xad\x9a\xf5\n\x00\xb2\xc7\x04\xec\x04\xecA\xed2\xedi\xec\xe0\xec\x10\xe3\x0e\xf8\x04\xec\x04\xec\x04\xec\x04\xec\x04\xec\x04\xecn\xed\x04\xecNr\x04\xec\x04\xc4\x04\xec\x00\x00\x00\x00%\xffQ\x00Q\x008\x00o\x00\x1e\x005\x00l\x00"
)
intimidate21 = bytearray(
    b"\x8b\xd2y\x8c9\xe9\xca\xb7\xc1\xd3\xbb\xcc\xbb\xbe\xc9\xcd\xff\x00\x02\x02\xca\xd9\xe8\xd9\xff\xff\xff\x00P}\x00\x00\xf3\x18'*\x80W\x03\x01\xb2;\xb3;0;\xb3;\x8a\x16\xb3;\xb2k\xb3;\xb2;\xb3;\xb2;\xb3;\xb2;\xb3;$;\x92;\xb2;\xb3;\x9a\x18\xb3;\x00\x00\x00\x00\x15\xffJ\x00J\x003\x00+\x00'\x00 \x00:\x00"
)

# Common species definitions
poochyena = get_species_by_index(286)
zigzagoon = get_species_by_index(288)
wurmple = get_species_by_index(290)
lotad = get_species_by_index(295)
seedot = get_species_by_index(298)
ralts = get_species_by_index(392)
geodude = get_species_by_index(74)
nosepass = get_species_by_index(320)
spinda = get_species_by_index(308)
slugma = get_species_by_index(218)
skarmory = get_species_by_index(227)
electrike = get_species_by_index(337)
gulpin = get_species_by_index(367)
minun = get_species_by_index(354)
oddish = get_species_by_index(43)
wingull = get_species_by_index(309)
plusle = get_species_by_index(353)
clamperl = get_species_by_index(373)
chinchou = get_species_by_index(170)
relicanth = get_species_by_index(381)

# Common route encounters definitions
granite_cave_rock_smash = [
    modules.map.WildEncounter(geodude, 10, 15, 60),
    modules.map.WildEncounter(nosepass, 10, 20, 30),
    modules.map.WildEncounter(geodude, 5, 10, 5),
    modules.map.WildEncounter(geodude, 15, 20, 4),
    modules.map.WildEncounter(geodude, 15, 20, 1),
]

route113_land = [
    modules.map.WildEncounter(spinda, 15, 15, 20),
    modules.map.WildEncounter(spinda, 15, 15, 20),
    modules.map.WildEncounter(slugma, 15, 15, 10),
    modules.map.WildEncounter(spinda, 14, 14, 10),
    modules.map.WildEncounter(spinda, 14, 14, 10),
    modules.map.WildEncounter(slugma, 14, 14, 10),
    modules.map.WildEncounter(spinda, 16, 16, 5),
    modules.map.WildEncounter(slugma, 16, 16, 5),
    modules.map.WildEncounter(spinda, 16, 16, 4),
    modules.map.WildEncounter(skarmory, 16, 16, 4),
    modules.map.WildEncounter(spinda, 16, 16, 1),
    modules.map.WildEncounter(skarmory, 16, 16, 1),
]

route110_land = [
    modules.map.WildEncounter(poochyena, 12, 12, 20),
    modules.map.WildEncounter(electrike, 12, 12, 20),
    modules.map.WildEncounter(gulpin, 12, 12, 10),
    modules.map.WildEncounter(electrike, 13, 13, 10),
    modules.map.WildEncounter(minun, 13, 13, 10),
    modules.map.WildEncounter(oddish, 13, 13, 10),
    modules.map.WildEncounter(minun, 13, 13, 5),
    modules.map.WildEncounter(gulpin, 13, 13, 5),
    modules.map.WildEncounter(wingull, 12, 12, 4),
    modules.map.WildEncounter(wingull, 12, 12, 4),
    modules.map.WildEncounter(plusle, 12, 12, 1),
    modules.map.WildEncounter(plusle, 13, 13, 1),
]

underwater = [
    modules.map.WildEncounter(clamperl, 20, 30, 60),
    modules.map.WildEncounter(chinchou, 20, 30, 30),
    modules.map.WildEncounter(clamperl, 30, 35, 5),
    modules.map.WildEncounter(relicanth, 30, 35, 4),
    modules.map.WildEncounter(relicanth, 30, 35, 1),
]


class TestEffectiveEncounterRatesForCurrentMap(unittest.TestCase):

    # assertEffectiveEncountersEqual checks that every effective encounter in `first` is also present in `second`,
    # comparing species name, levels, and encounter rate.  This is used instead of assertCountEqual because
    # assertCountEqual asserts exact equality between elements, which means floating point rounding can cause an
    # otherwise sound test to fail.
    def assertEffectiveEncountersEqual(
        self, first: list[modules.map.EffectiveWildEncounter], second: list[modules.map.EffectiveWildEncounter]
    ):
        for encounter in first:
            found = False
            for m in second:
                if encounter.species.name != m.species.name:
                    continue
                self.assertFalse(found, msg=f"Too many encounters in second for species {encounter.species.name}")
                found = True
                self.assertEqual(
                    encounter.min_level,
                    m.min_level,
                    msg=f"minimum levels do not match for species {encounter.species.name}",
                )
                self.assertEqual(
                    encounter.max_level,
                    m.max_level,
                    msg=f"maximum levels do not match for species {encounter.species.name}",
                )
                self.assertAlmostEqual(
                    encounter.encounter_rate,
                    m.encounter_rate,
                    msg=f"encounter rates do not match for species {encounter.species.name}",
                )
            self.assertTrue(found, msg=f"No matching encounters in second for species {encounter.species.name}")

    def test_route102_plain(self):
        encounters = [
            modules.map.WildEncounter(poochyena, 3, 3, 20),
            modules.map.WildEncounter(wurmple, 3, 3, 20),
            modules.map.WildEncounter(poochyena, 4, 4, 10),
            modules.map.WildEncounter(wurmple, 4, 4, 10),
            modules.map.WildEncounter(lotad, 3, 3, 10),
            modules.map.WildEncounter(lotad, 4, 4, 10),
            modules.map.WildEncounter(zigzagoon, 3, 3, 5),
            modules.map.WildEncounter(zigzagoon, 3, 3, 5),
            modules.map.WildEncounter(zigzagoon, 4, 4, 4),
            modules.map.WildEncounter(ralts, 4, 4, 4),
            modules.map.WildEncounter(zigzagoon, 4, 4, 1),
            modules.map.WildEncounter(seedot, 3, 3, 1),
        ]
        party_lead = PartyPokemon(regular_lead, 0)

        want = [
            modules.map.EffectiveWildEncounter(poochyena, 3, 4, 0.3),
            modules.map.EffectiveWildEncounter(wurmple, 3, 4, 0.3),
            modules.map.EffectiveWildEncounter(lotad, 3, 4, 0.2),
            modules.map.EffectiveWildEncounter(zigzagoon, 3, 4, 0.15),
            modules.map.EffectiveWildEncounter(ralts, 4, 4, 0.04),
            modules.map.EffectiveWildEncounter(seedot, 3, 3, 0.01),
        ]

        got = modules.map.calculate_effective_encounters(encounters, "land", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_empty_encounters(self):
        party_lead = PartyPokemon(regular_lead, 0)
        got = modules.map.calculate_effective_encounters([], "rock_smash", party_lead, 0)
        # Imprtantly, doesn't crash.
        self.assertEqual(got, [])

    # Nosepass for testing repel on level range encounters, and interactions
    # with pressure and intimidate
    def test_nosepass_plain(self):
        party_lead = PartyPokemon(regular_lead, 0)

        want = [
            modules.map.EffectiveWildEncounter(geodude, 5, 20, 0.7),
            modules.map.EffectiveWildEncounter(nosepass, 10, 20, 0.3),
        ]

        got = modules.map.calculate_effective_encounters(granite_cave_rock_smash, "rock_smash", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_nosepass_repel13(self):
        party_lead = PartyPokemon(regular_lead, 0)

        want = [
            modules.map.EffectiveWildEncounter(geodude, 13, 20, 154 / 250),
            modules.map.EffectiveWildEncounter(nosepass, 13, 20, 48 / 125),
        ]

        got = modules.map.calculate_effective_encounters(granite_cave_rock_smash, "rock_smash", party_lead, 13)

        self.assertEffectiveEncountersEqual(got, want)

    def test_nosepass_pressure(self):
        party_lead = PartyPokemon(pressure, 0)

        want = [
            modules.map.EffectiveWildEncounter(geodude, 5, 20, 0.7),
            modules.map.EffectiveWildEncounter(nosepass, 10, 20, 0.3),
        ]

        got = modules.map.calculate_effective_encounters(granite_cave_rock_smash, "rock_smash", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_nosepass_intimidate21(self):
        party_lead = PartyPokemon(intimidate21, 0)

        want = [
            modules.map.EffectiveWildEncounter(geodude, 5, 20, 242 / 377),
            modules.map.EffectiveWildEncounter(nosepass, 10, 20, 135 / 377),
        ]

        got = modules.map.calculate_effective_encounters(granite_cave_rock_smash, "rock_smash", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_nosepass_repel13_intimidate21(self):
        party_lead = PartyPokemon(intimidate21, 0)

        want = [
            modules.map.EffectiveWildEncounter(geodude, 13, 20, 253 / 469),
            modules.map.EffectiveWildEncounter(nosepass, 13, 20, 216 / 469),
        ]

        got = modules.map.calculate_effective_encounters(granite_cave_rock_smash, "rock_smash", party_lead, 13)

        self.assertEffectiveEncountersEqual(got, want)

    def test_nosepass_repel13_pressure(self):
        party_lead = PartyPokemon(pressure, 0)

        want = [
            modules.map.EffectiveWildEncounter(geodude, 13, 20, 110 / 167),
            modules.map.EffectiveWildEncounter(nosepass, 13, 20, 57 / 167),
        ]

        got = modules.map.calculate_effective_encounters(granite_cave_rock_smash, "rock_smash", party_lead, 13)

        self.assertEffectiveEncountersEqual(got, want)

    # Skarmory for testing simple magnet pull and repel interactions
    def test_skarmory_magnetpull(self):
        party_lead = PartyPokemon(magnet_pull, 0)

        want = [
            modules.map.EffectiveWildEncounter(spinda, 14, 16, 0.35),
            modules.map.EffectiveWildEncounter(slugma, 14, 16, 0.125),
            modules.map.EffectiveWildEncounter(skarmory, 16, 16, 0.525),
        ]

        got = modules.map.calculate_effective_encounters(route113_land, "land", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_skarmory_repel16_magnetpull(self):
        party_lead = PartyPokemon(magnet_pull, 0)

        want = [
            modules.map.EffectiveWildEncounter(spinda, 16, 16, 1 / 12),
            modules.map.EffectiveWildEncounter(slugma, 16, 16, 1 / 24),
            modules.map.EffectiveWildEncounter(skarmory, 16, 16, 0.875),
        ]

        got = modules.map.calculate_effective_encounters(route113_land, "land", party_lead, 16)

        self.assertEffectiveEncountersEqual(got, want)

    # Plusle for testing complex static and repel interactions
    def test_plusle_static(self):
        party_lead = PartyPokemon(static, 0)

        want = [
            modules.map.EffectiveWildEncounter(electrike, 12, 13, 19 / 60),
            modules.map.EffectiveWildEncounter(minun, 13, 13, 29 / 120),
            modules.map.EffectiveWildEncounter(plusle, 12, 13, 53 / 300),
            modules.map.EffectiveWildEncounter(poochyena, 12, 12, 0.1),
            modules.map.EffectiveWildEncounter(gulpin, 12, 13, 0.075),
            modules.map.EffectiveWildEncounter(oddish, 13, 13, 0.05),
            modules.map.EffectiveWildEncounter(wingull, 12, 12, 0.04),
        ]

        got = modules.map.calculate_effective_encounters(route110_land, "land", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_plusle_repel13_static(self):
        party_lead = PartyPokemon(static, 0)

        want = [
            modules.map.EffectiveWildEncounter(electrike, 13, 13, 80 / 323),
            modules.map.EffectiveWildEncounter(minun, 13, 13, 145 / 323),
            modules.map.EffectiveWildEncounter(plusle, 13, 13, 53 / 323),
            modules.map.EffectiveWildEncounter(gulpin, 13, 13, 15 / 323),
            modules.map.EffectiveWildEncounter(oddish, 13, 13, 30 / 323),
        ]

        got = modules.map.calculate_effective_encounters(route110_land, "land", party_lead, 13)

        self.assertEffectiveEncountersEqual(got, want)

    # Chinchou for testing static + repel combos on level ranges
    def test_chinchou_static(self):
        party_lead = PartyPokemon(static, 0)

        want = [
            modules.map.EffectiveWildEncounter(clamperl, 20, 35, 13 / 40),
            modules.map.EffectiveWildEncounter(chinchou, 20, 30, 13 / 20),
            modules.map.EffectiveWildEncounter(relicanth, 30, 35, 1 / 40),
        ]

        got = modules.map.calculate_effective_encounters(underwater, "surf", party_lead, 0)

        self.assertEffectiveEncountersEqual(got, want)

    def test_chinchou_repel26_static(self):
        party_lead = PartyPokemon(static, 0)

        want = [
            modules.map.EffectiveWildEncounter(clamperl, 26, 35, 71 / 212),
            modules.map.EffectiveWildEncounter(chinchou, 26, 30, 65 / 106),
            modules.map.EffectiveWildEncounter(relicanth, 30, 35, 55 / 1060),
        ]

        got = modules.map.calculate_effective_encounters(underwater, "surf", party_lead, 26)

        self.assertEffectiveEncountersEqual(got, want)


if __name__ == "__main__":
    print("pls")
    unittest.main()
