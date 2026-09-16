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

    def test_translation_is_idempotent_for_prefix_labels(self):
        for portuguese, english in (("Rasterizar", "Raster"), ("Processo", "Process")):
            self.assertEqual(translate_text(portuguese, "pt-BR"), portuguese)
            self.assertEqual(translate_text(english, "en"), english)
            self.assertEqual(translate_text(translate_text(portuguese, "en"), "en"), english)
            self.assertEqual(
                translate_text(translate_text(english, "pt-BR"), "pt-BR"),
                portuguese,
            )


if __name__ == "__main__":
    unittest.main()
