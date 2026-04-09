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
