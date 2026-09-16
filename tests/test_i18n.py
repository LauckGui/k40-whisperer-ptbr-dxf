import unittest

from k40core.i18n import translate_text


class TranslationTests(unittest.TestCase):
    def test_exact_translation_and_round_trip(self):
        english = translate_text("Configurações de raster", "en")
        self.assertEqual(english, "Raster settings")
        self.assertEqual(translate_text(english, "pt-BR"), "Configurações de raster")

    def test_dynamic_message_preserves_values(self):
        text = "Calculando tempo do raster: 42.5 %"
        self.assertEqual(
            translate_text(text, "en"),
            "Calculating raster time: 42.5 %",
        )

    def test_unknown_internal_value_is_unchanged(self):
        self.assertEqual(translate_text("Floyd–Steinberg", "en"), "Floyd–Steinberg")


if __name__ == "__main__":
    unittest.main()
