import json
import os
import tempfile
import unittest

from k40core.configuration import (ConfigurationError, configuration_path,
                                   load_configuration, save_configuration)


class ConfigurationTests(unittest.TestCase):
    def test_round_trip_preserves_process_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "k40.json")
            expected = {"Reng_feed": "123", "Reng_passes": "2", "rast_step": "0.003"}
            save_configuration(path, expected)
            self.assertEqual(load_configuration(path), expected)

    def test_unknown_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "k40.json")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump({"schema_version": 99, "settings": {}}, stream)
            with self.assertRaises(ConfigurationError):
                load_configuration(path)

    def test_installed_application_uses_local_app_data(self):
        path = configuration_path(
            r"C:\Program Files\K40 Whisperer\k40_whisperer.py",
            frozen=True,
            environment={"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"},
        )
        self.assertEqual(
            path,
            os.path.join(r"C:\Users\Test\AppData\Local", "K40 Whisperer",
                         "k40_whisperer.config.json"),
        )


if __name__ == "__main__":
    unittest.main()
