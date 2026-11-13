import unittest

from assembler import assemble, disassemble_words, hex_words_from_text, parse_number


class AssemblerTests(unittest.TestCase):
    def test_compiles_labels_and_logisim_output(self):
        result = assemble("start:\nLDA 01 ; load A\nADD\nJMP start\n")

        self.assertTrue(result.succeeded)
        self.assertEqual(result.words, [0xA0, 1, 0x40, 0x10, 0])
        self.assertTrue(result.output.startswith("v3.0 hex words addressed\n0000:"))
        self.assertIn("00A0 0001 0040 0010 0000", result.output)

    def test_numeric_jump_targets_are_rebased_to_instruction_addresses(self):
        result = assemble("LDA 01\nLDB 02\nJMP 1\n")

        self.assertTrue(result.succeeded)
        self.assertEqual(result.words, [0xA0, 1, 0xB0, 2, 0x10, 2])

    def test_reports_duplicate_labels_and_bad_operand_counts(self):
        result = assemble("again:\nagain:\nLDA\n")

        self.assertFalse(result.succeeded)
        self.assertEqual(result.output, "")
        self.assertEqual(
            [diagnostic.message for diagnostic in result.diagnostics],
            ["Duplicate label: again.", "LDA expects 1 operand(s), got 0."],
        )

    def test_reports_unknown_symbols_and_out_of_range_operands(self):
        result = assemble("LDA missing\nLDB 10000h\n")

        self.assertFalse(result.succeeded)
        self.assertEqual(
            [diagnostic.line for diagnostic in result.diagnostics],
            [1, 2],
        )

    def test_preserves_hex_operand_notation(self):
        self.assertEqual(parse_number("0x10"), 16)
        self.assertEqual(parse_number("10h"), 16)
        self.assertEqual(parse_number("0010"), 16)

    def test_reads_logisim_hex_and_disassembles_jump_labels(self):
        words = hex_words_from_text(
            "v3.0 hex words addressed\n0000: 00A0 0001 0010 0000\n"
        )

        self.assertEqual(words, [0xA0, 1, 0x10, 0])
        self.assertEqual(
            disassemble_words(words),
            "RAW_0000:\nLDA 0x0001\nJMP RAW_0000",
        )


if __name__ == "__main__":
    unittest.main()
