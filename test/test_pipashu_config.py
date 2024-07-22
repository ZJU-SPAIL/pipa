import pytest
from unittest.mock import patch
from pipa.service.gengerate.parse_pipashu_config import build_command, quest, main


def test_build_command_without_taskset():
    command = build_command(False, "0-7", "echo test")
    assert command == "echo test"


def test_build_command_invalid_core_range():
    with pytest.raises(ValueError):
        build_command(True, "invalid_range", "echo test")


@patch("questionary.text")
def test_quest(mock_text):
    mock_text.return_value.ask.return_value = "./test-config.yaml"
    result = quest()
    assert result == "./test-config.yaml"


@patch("pipa.service.gengerate.parse_pipashu_config.quest")
@patch("pipa.service.gengerate.parse_pipashu_config.build")
def test_main_with_config_path(mock_build, mock_quest):
    config_path = "test-config.yaml"
    main(config_path)
    mock_build.assert_called_once_with(config_path)
    mock_quest.assert_not_called()


@patch("pipa.service.gengerate.parse_pipashu_config.quest")
@patch("pipa.service.gengerate.parse_pipashu_config.build")
def test_main_without_config_path(mock_build, mock_quest):
    mock_quest.return_value = "test-config.yaml"
    main()
    mock_quest.assert_called_once()
    mock_build.assert_called_once_with("test-config.yaml")


if __name__ == "__main__":
    pytest.main([__file__])
