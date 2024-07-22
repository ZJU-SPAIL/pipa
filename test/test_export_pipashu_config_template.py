import unittest
from unittest.mock import patch
from pipa.service.gengerate.export_pipashu_config_template import (
    query_filepath,
    generate_pipashu_template,
    generate_upload_template,
    CONFIG_TEMPLATE,
    UPLOAD_TEMPLATE,
)


class TestExportPipashuConfigTemplate(unittest.TestCase):

    @patch("questionary.text")
    def test_query_filepath_default(self, mock_text):
        mock_text.return_value.ask.return_value = ""
        self.assertEqual(query_filepath(), "./")

    @patch("questionary.text")
    def test_query_filepath_input(self, mock_text):
        mock_text.return_value.ask.return_value = "/path/to/config"
        self.assertEqual(query_filepath(), "/path/to/config")

    @patch("pipa.service.gengerate.export_pipashu_config_template.generate_template")
    def test_generate_pipashu_template(self, mock_generate_template):
        mock_generate_template.return_value = len(CONFIG_TEMPLATE)
        result = generate_pipashu_template()
        mock_generate_template.assert_called_once_with(
            CONFIG_TEMPLATE, "config-pipa-shu.yaml"
        )
        self.assertEqual(result, len(CONFIG_TEMPLATE))

    @patch("pipa.service.gengerate.export_pipashu_config_template.generate_template")
    def test_generate_upload_template(self, mock_generate_template):
        filename = "config-upload.yaml"
        mock_generate_template.return_value = len(UPLOAD_TEMPLATE)
        result = generate_upload_template(filename)
        mock_generate_template.assert_called_once_with(UPLOAD_TEMPLATE, filename)
        self.assertEqual(result, len(UPLOAD_TEMPLATE))


if __name__ == "__main__":
    unittest.main()
