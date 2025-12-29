import tarfile
from unittest.mock import mock_open, patch

import pytest

from pipa.common.cmd import run_command
from pipa.common.utils import (
    FileFormat,
    check_file_format,
    find_closest_factor_pair,
    generate_unique_rgb_color,
    handle_user_cancelled,
    process_compression,
    tar,
    untar,
)


@patch(
    "builtins.open", new_callable=mock_open, read_data=b"\xfd\x37\x7a\x58\x5a\x00"
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


def test_run_command_success():
    assert run_command("echo hello") == "hello"


def test_run_command_failure():
    with pytest.raises(Exception) as excinfo:
        run_command("bash -c 'echo error >&2; exit 2'")
    assert "error" in str(excinfo.value)


def test_tar_and_untar_roundtrip(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("a")
    (src_dir / "b.txt").write_text("b")

    tar_path = tmp_path / "out.tar"
    extract_dir = tmp_path / "extract"

    tar(
        str(tar_path), ["a.txt", "b.txt", "missing.txt", "a.txt"], base_dir=str(src_dir)
    )
    with tarfile.open(tar_path, mode="r") as tf:
        names = sorted(tf.getnames())
    assert names == ["a.txt", "b.txt"]

    untar(str(tar_path), str(extract_dir))
    assert (extract_dir / "a.txt").read_text() == "a"
    assert (extract_dir / "b.txt").read_text() == "b"


def test_process_compression_xz_roundtrip(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("hello")
    compressed = tmp_path / "plain.xz"
    restored = tmp_path / "restored.txt"

    process_compression(str(compressed), str(plain), FileFormat.xz, decompress=False)
    assert compressed.exists()

    process_compression(str(compressed), str(restored), FileFormat.xz, decompress=True)
    assert restored.read_text() == "hello"


def test_process_compression_unsupported(tmp_path):
    compressed = tmp_path / "plain.tar"
    restored = tmp_path / "restored.txt"
    # Should no-op and not create output when unsupported format
    process_compression(str(compressed), str(restored), FileFormat.tar, decompress=True)
    assert not compressed.exists()
    assert not restored.exists()


def test_find_closest_factor_pair():
    assert find_closest_factor_pair(36) == (6, 6)
    assert find_closest_factor_pair(20) == (4, 5)


def test_handle_user_cancelled_keyboard_interrupt():
    @handle_user_cancelled
    def will_interrupt():
        raise KeyboardInterrupt()

    with pytest.raises(SystemExit) as excinfo:
        will_interrupt()
    assert excinfo.value.code == 0


def test_handle_user_cancelled_type_error():
    @handle_user_cancelled
    def will_type_error():
        raise TypeError("bad")

    with pytest.raises(SystemExit) as excinfo:
        will_type_error()
    assert excinfo.value.code == 0


def test_generate_unique_rgb_color_deterministic():
    data = [1, 2, 3]
    color1 = generate_unique_rgb_color(data.copy(), generate_seed=False)
    color2 = generate_unique_rgb_color(data.copy(), generate_seed=False)
    assert color1 == color2
    assert all(0 <= c <= 255 for c in color1)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
