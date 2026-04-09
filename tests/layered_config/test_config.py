import dataclasses
import pathlib

import pytest

from json_config.api import (
    ConfigLayer,
    ConfigValues,
    LayeredConfig,
    LayeredConfigManager,
)


def test_init_with_single_layer(
    simple_config_file: pathlib.Path,
    layered_config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    @dataclasses.dataclass
    class TestValues(ConfigValues):
        int_value: int = 0

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = LayeredConfigManager()
    root_layer = ConfigLayer("root", file_path=simple_config_file)
    manager.register(root_layer)
    manager.load_all()

    config = TestConfig(manager)
    assert config.values.int_value == 0
    config.resolve()
    assert config.values.int_value == 5

    config.values.int_value = 10
    config.manager["root"].file_path = (
        layered_config_output_dir / f"{request.node.name}_config.json"
    )
    config.save()


def test_defaults_writing(
    layered_config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that defaults are written to the root layer file when saving."""

    @dataclasses.dataclass
    class TestValues(ConfigValues):
        int_value: int = dataclasses.field(default=0)
        str_value: str = dataclasses.field(default="default")
        list_value: list[str] = dataclasses.field(
            default_factory=lambda: ["a", "b", "c"]
        )

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    # Setup manager
    manager = LayeredConfigManager()
    root_layer = ConfigLayer(
        "root", file_path=layered_config_output_dir / f"{request.node.name}_config.json"
    )
    extra_root_layer = ConfigLayer(
        "extra_root",
        file_path=layered_config_output_dir
        / f"{request.node.name}_extra_root_config.json",
    )
    extra_child_layer = ConfigLayer(
        "extra",
        file_path=layered_config_output_dir / f"{request.node.name}_extra_config.json",
        depends_on=["root"],
    )
    manager.register(root_layer)
    manager.register(extra_root_layer)
    manager.register(extra_child_layer)
    manager.load_all()

    config = TestConfig(manager)
    #! Do not run resolve so that defaults are written to the file
    config.save()
    assert manager["root"].file_path.is_file()

    # After saving files for root layers should contain the defaults
    manager.load_all()
    assert (
        root_layer.get_data()
        == extra_root_layer.get_data()
        == TestValues.get_defaults()
    )
    # The extra layer file should not be created as it's empty
    assert extra_child_layer.get_data() == {}
    assert not extra_child_layer.file_path.is_file()
