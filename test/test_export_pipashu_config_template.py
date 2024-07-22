import pytest
from unittest.mock import patch
from pipa.service.gengerate.export_pipashu_config_template import (
    query_filepath,
    generate_pipashu_template,
    generate_upload_template,
    CONFIG_TEMPLATE,
    UPLOAD_TEMPLATE,
)


def test_query_filepath_default(monkeypatch):
    mock_text = patch("questionary.text").start()
    mock_text.return_value.ask.return_value = ""
    monkeypatch.setattr("questionary.text", mock_text)
    assert query_filepath() == "./"
    patch.stopall()


def test_query_filepath_input(monkeypatch):
    mock_text = patch("questionary.text").start()
    mock_text.return_value.ask.return_value = "/path/to/config"
    monkeypatch.setattr("questionary.text", mock_text)
    assert query_filepath() == "/path/to/config"
    patch.stopall()


def test_generate_pipashu_template(monkeypatch):
    mock_generate_template = patch(
        "pipa.service.gengerate.export_pipashu_config_template.generate_template"
    ).start()
    mock_generate_template.return_value = len(CONFIG_TEMPLATE)
    monkeypatch.setattr(
        "pipa.service.gengerate.export_pipashu_config_template.generate_template",
        mock_generate_template,
    )
    result = generate_pipashu_template()
    mock_generate_template.assert_called_once_with(
        CONFIG_TEMPLATE, "config-pipa-shu.yaml"
    )
    assert result == len(CONFIG_TEMPLATE)
    patch.stopall()


def test_generate_upload_template(monkeypatch):
    filename = "config-upload.yaml"
    mock_generate_template = patch(
        "pipa.service.gengerate.export_pipashu_config_template.generate_template"
    ).start()
    mock_generate_template.return_value = len(UPLOAD_TEMPLATE)
    monkeypatch.setattr(
        "pipa.service.gengerate.export_pipashu_config_template.generate_template",
        mock_generate_template,
    )
    result = generate_upload_template(filename)
    mock_generate_template.assert_called_once_with(UPLOAD_TEMPLATE, filename)
    assert result == len(UPLOAD_TEMPLATE)
    patch.stopall()


if __name__ == "__main__":
    pytest.main([__file__])
