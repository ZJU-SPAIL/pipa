import unittest
from unittest.mock import patch, MagicMock
from pipa.common.hardware.cpu import get_cpu_cores

from pipa.service.gengerate.parse_pipashu_config import build_command, quest, main


class TestPipashuConfig(unittest.TestCase):

    @patch("pipa.common.hardware.cpu.get_cpu_cores")
    def test_build_command_with_taskset(self, mock_get_cpu_cores):
        mock_get_cpu_cores.return_value = list(range(16))
        command = build_command(True, "0-7", "echo test")
        self.assertEqual(command, "/usr/bin/taskset -c 0,1,2,3,4,5,6,7 echo test")

    def test_build_command_without_taskset(self):
        command = build_command(False, "0-7", "echo test")
        self.assertEqual(command, "echo test")

    def test_build_command_invalid_core_range(self):
        with self.assertRaises(ValueError):
            build_command(True, "invalid_range", "echo test")

    @patch("questionary.text")
    def test_quest(self, mock_text):
        mock_text.return_value.ask.return_value = "./test-config.yaml"
        result = quest()
        self.assertEqual(result, "./test-config.yaml")

    @patch("pipa.service.gengerate.parse_pipashu_config.quest")
    @patch("pipa.service.gengerate.parse_pipashu_config.build")
    def test_main_with_config_path(self, mock_build, mock_quest):
        config_path = "test-config.yaml"
        main(config_path)
        mock_build.assert_called_once_with(config_path)
        mock_quest.assert_not_called()

    @patch("pipa.service.gengerate.parse_pipashu_config.quest")
    @patch("pipa.service.gengerate.parse_pipashu_config.build")
    def test_main_without_config_path(self, mock_build, mock_quest):
        mock_quest.return_value = "test-config.yaml"
        main()
        mock_quest.assert_called_once()
        mock_build.assert_called_once_with("test-config.yaml")


if __name__ == "__main__":
    unittest.main()
