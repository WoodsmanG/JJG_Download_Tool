import unittest

from JJG_Download_Tool import extract_reader_args, parse_standard


class ParseStandardTests(unittest.TestCase):
    def test_current_detail_url(self):
        value = (
            "https://jjg.spc.org.cn/resmea/standard/detail.html?"
            "standno=JJF+1070-2023&pageindex=1&rows=10"
        )
        self.assertEqual(parse_standard(value), ("JJF", "1070-2023"))

    def test_legacy_detail_url(self):
        value = "http://jjg.spc.org.cn/resmea/standard/JJF%25201261.9-2013/?"
        self.assertEqual(parse_standard(value), ("JJF", "1261.9-2013"))

    def test_identifier(self):
        self.assertEqual(parse_standard("jjf 1070-2023"), ("JJF", "1070-2023"))


class ExtractReaderArgsTests(unittest.TestCase):
    def test_current_token_variable(self):
        html = 'var enc = "abc\\/def=="; var token = "token=="; var rc = token;'
        self.assertEqual(extract_reader_args(html), ("abc/def==", "token=="))

    def test_legacy_rc_variable(self):
        html = 'var enc = "myfoxit=="; var rc = "legacy-token==";'
        self.assertEqual(
            extract_reader_args(html), ("myfoxit==", "legacy-token==")
        )


if __name__ == "__main__":
    unittest.main()
