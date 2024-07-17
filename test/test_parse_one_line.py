import unittest
from pipa.parser.perf_report import parse_one_line


class TestParseOneLine(unittest.TestCase):

    def setUp(self):
        # 设置示例数据和列位置范围
        self.line = "    14.31%   2.91%  java             libjvm.so                                                           [.] SpinPause"
        self.lr = [(4, 18), (20, 24), (37, 46), (105, -1)]  # 重新调整位置范围

    def test_parse_one_line(self):
        expected_output = (14.31, 2.91, "java", "libjvm.so", ".", "SpinPause")

        result = parse_one_line(self.line, self.lr)
        self.assertEqual(result, expected_output)

    def test_parse_one_line_incorrect_format(self):
        incorrect_line = "incorrect format data"
        result = parse_one_line(incorrect_line, self.lr)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
