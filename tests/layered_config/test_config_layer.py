import pathlib

import pytest

from json_config.api import ConfigLayer


def test_repr() -> None:
    """Test the __repr__ method."""
    layer = ConfigLayer("test", file_path=None)
    assert repr(layer) == "ConfigLayer(name=test)"


def test_empty_layer():
    """Test that an empty layer has no data."""
    layer = ConfigLayer("test", file_path=None)
    assert layer.get_data() == {}


def test_set_values():
    """Test that values can be set on a layer."""
    layer = ConfigLayer("test", file_path=None)
    layer.set(a=1, b=2)
    assert layer.get_data() == {"a": 1, "b": 2}


def test_load_values():
    """Test that values can be loaded from a file."""
    layer = ConfigLayer("test", file_path=None)
    layer.load()
    assert layer.get_data() == {}


def test_load_empty_file(empty_layer_file: pathlib.Path):
    """Test that an empty file is loaded as an empty layer."""
    layer = ConfigLayer("test", file_path=empty_layer_file)
    layer.load()
    assert layer.get_data() == {}


def test_load_invalid_not_dict_layer_value_error(
    invalid_not_dict_layer: pathlib.Path,
):
    """Test that a non-dict layer raises a ValueError."""
    layer = ConfigLayer("test", file_path=invalid_not_dict_layer)
    with pytest.raises(ValueError):
        layer.load()


def test_save_with_no_filepath_runtime_error():
    """Test that saving with no file path raises a RuntimeError."""
    layer = ConfigLayer("test", file_path=None)
    layer.set(a=1, b=2)
    with pytest.raises(RuntimeError):
        layer.save()


def test_save_empty_layer(
    config_layer_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """Test that an empty layer is not saved."""
    test_data = {}
    output_file = config_layer_output_dir / f"{request.node.name}.json"
    layer = ConfigLayer("test", file_path=output_file)
    layer.set(**test_data)
    layer.save()
    assert not output_file.exists()


def test_save_with_filepath(
    config_layer_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """Test that values are saved to a file."""
    output_file = config_layer_output_dir / f"{request.node.name}.json"
    layer = ConfigLayer("test", file_path=output_file)
    test_data = {"a": 1, "b": 2}

    layer.set(**test_data)
    layer.save()

    assert output_file.exists()
    layer.load()
    assert layer.get_data() == test_data
