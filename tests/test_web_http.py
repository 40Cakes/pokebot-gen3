import json
from unittest import TestCase
from unittest.mock import MagicMock

from modules.web.http import _encounters_to_response


class TestEncountersToResponse(TestCase):
    def test_it_returns_503_when_no_encounter_data_is_available(self):
        response = _encounters_to_response(None)

        self.assertEqual(503, response.status)

    def test_it_returns_encounter_data_as_json(self):
        encounters = MagicMock()
        encounters.to_dict.return_value = {"land": []}

        response = _encounters_to_response(encounters)

        self.assertEqual(200, response.status)
        self.assertEqual({"land": []}, json.loads(response.text))
