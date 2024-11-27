import pytest
from unittest.mock import patch, mock_open
from pipa.common.utils import FileFormat, check_file_format


@patch(
    "builtins.open", new_callable=mock_open, read_data=b"\xFD\x37\x7A\x58\x5A\x00"
)  # xz magic number
def test_check_file_format_xz(mock_open):
    assert check_file_format(file="test.xz") == FileFormat.xz
    mock_open.assert_called_with("test.xz", "rb")


@patch("builtins.open", new_callable=mock_open, read_data=b"BZh")  # bz2 magic number
def test_check_file_format_bzip2(mock_open):
    assert check_file_format(file="test.xz") == FileFormat.bzip2
    mock_open.assert_called_with("test.xz", "rb")


@patch(
    "builtins.open", new_callable=mock_open, read_data=b"\x7f\x45\x4c\x46"
)  # elf magic number
def test_check_file_format_elf(mock_open):
    assert check_file_format(file="test.xz") == FileFormat.elf
    mock_open.assert_called_with("test.xz", "rb")


@patch(
    "builtins.open", new_callable=mock_open, read_data=b"RandomBytes"
)  # other file format
def test_check_file_format_other(mock_open):
    assert check_file_format(file="test.xz") == FileFormat.other
    mock_open.assert_called_with("test.xz", "rb")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
