import dataclasses
import json
import pathlib

import pytest

from json_config.api import (
    ConfigLayer,
    ConfigValues,
    LayeredConfig,
    LayeredConfigManager,
)


def test_repr() -> None:
    """Test the __repr__ method."""
    config = LayeredConfig()
    assert repr(config) == "LayeredConfig(layer_filter=None)"


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
        dataclasses.field()

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


def test_layer_filter_limits_resolve_to_expected_values(
    preset_app_manager: LayeredConfigManager,
):
    """Test that layer filtering limits resolve to the expected values."""

    class TestConfig(LayeredConfig):
        pass

    config = TestConfig(preset_app_manager)

    config.layer_filter = "main"
    resolved_dict = config.resolve()
    assert preset_app_manager["main"].get_data().items() <= resolved_dict.items()
    # Set filter to "workspace" and verify only workspace layer is included
    config.layer_filter = "workspace"
    resolved_dict = config.resolve()
    assert preset_app_manager["workspace"].get_data().items() <= resolved_dict.items()
    # Set filter to "user" and verify only user layer is included
    config.layer_filter = "user"
    resolved_dict = config.resolve()
    assert (
        not preset_app_manager["workspace"].get_data().items() <= resolved_dict.items()
    )
    assert preset_app_manager["user"].get_data().items() <= resolved_dict.items()
    # Set filter to None and verify only root layers are included
    config.layer_filter = None
    resolved_dict = config.resolve()
    assert preset_app_manager["main"].get_data().items() <= resolved_dict.items()


def test_invalid_layer_filter_resolve(
    preset_app_manager: LayeredConfigManager,
):
    """Test that resolving with an invalid layer filter raises a ValueError."""

    class TestConfig(LayeredConfig):
        pass

    config = TestConfig(preset_app_manager)

    config.layer_filter = "nonexistent"
    with pytest.raises(ValueError):
        config.resolve()


def test_default_values():
    """Test that the default values are returned correctly."""

    class TestValues(ConfigValues):
        name: str = "default"

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    config = TestConfig()
    assert config.defaults() == TestValues()


def test_reset_values():
    """Test that resetting values to defaults works correctly."""

    class TestValues(ConfigValues):
        name: str = "default"

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    config = TestConfig()
    config.values.name = "new_value"
    assert config.values.name != config.defaults().name
    config.reset()
    assert config.defaults().name == TestValues().name


# ---------------------------------------------------------------------------
# LayeredConfig + category metadata integration
# ---------------------------------------------------------------------------


def test_layered_config_save_produces_expected_nested_json(
    category_values_class: type[ConfigValues],
    layered_config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that saving a ConfigValues with category fields produces the
    expected nested JSON structure through a single ConfigLayer/file."""

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    manager = LayeredConfigManager()
    root_layer = ConfigLayer(
        "root", file_path=layered_config_output_dir / f"{request.node.name}_config.json"
    )
    manager.register(root_layer)
    manager.load_all()

    config = TestConfig(manager)
    config.save()

    on_disk = json.loads(root_layer.file_path.read_text())
    assert on_disk == {
        "category_a": {"field_one": 100, "field_two": 100},
        "category_b": {"label": "test"},
        "flat_value": 10,
    }


def test_layered_config_roundtrip_mutating_nested_category_value(
    category_values_class: type[ConfigValues],
    layered_config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test load -> resolve -> mutate a nested category value -> save round-trips."""

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    manager = LayeredConfigManager()
    root_layer = ConfigLayer(
        "root", file_path=layered_config_output_dir / f"{request.node.name}_config.json"
    )
    manager.register(root_layer)
    manager.load_all()

    config = TestConfig(manager)
    config.save()

    manager.load_all()
    config2 = TestConfig(manager)
    config2.resolve()
    config2.values.category_a.field_one = 1920
    config2.save()

    on_disk = json.loads(root_layer.file_path.read_text())
    assert on_disk == {
        "category_a": {"field_one": 1920, "field_two": 100},
        "category_b": {"label": "test"},
        "flat_value": 10,
    }


def test_layered_config_deep_merges_nested_category_across_layers(
    category_values_class: type[ConfigValues],
    layered_config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that a child layer overriding only part of a category is deep-merged
    with the root layer's defaults for that same category."""
    root_layer = ConfigLayer(
        "root",
        file_path=layered_config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=layered_config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = LayeredConfigManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    config = TestConfig(manager)
    #! Seed root defaults without resolving, matching test_defaults_writing.
    config.save()

    # Child layer only overrides one field of category_a; the sibling field
    # should still come from the root layer's seeded defaults after a deep merge.
    child_layer.set(category_a={"field_one": 4000})
    manager.save("child")

    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()

    assert config2.values.category_a.field_one == 4000
    assert config2.values.category_a.field_two == 100
    assert config2.values.category_b.label == "test"
    assert config2.values.flat_value == 10


def test_layered_config_roundtrip_with_three_levels_of_nesting(
    nested_category_values_class: type[ConfigValues],
    layered_config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Regression test: save/load/mutate/save round-trips correctly through
    three levels of category nesting (category_a.sub_category.x/y)."""

    class TestConfig(LayeredConfig[nested_category_values_class]):
        VALUES_CLASS = nested_category_values_class

    manager = LayeredConfigManager()
    root_layer = ConfigLayer(
        "root", file_path=layered_config_output_dir / f"{request.node.name}_config.json"
    )
    manager.register(root_layer)
    manager.load_all()

    config = TestConfig(manager)
    config.save()

    on_disk = json.loads(root_layer.file_path.read_text())
    assert on_disk == {
        "category_a": {
            "field_one": 100,
            "field_two": 100,
            "sub_category": {"x": 0, "y": 0},
        },
        "category_b": {"label": "test"},
        "flat_value": 10,
    }

    # Mutate only the deepest (level-3) values and re-save.
    manager.load_all()
    config2 = TestConfig(manager)
    config2.resolve()
    config2.values.category_a.sub_category.x = 42
    config2.values.category_a.sub_category.y = 84
    config2.save()

    on_disk = json.loads(root_layer.file_path.read_text())
    assert on_disk == {
        "category_a": {
            "field_one": 100,
            "field_two": 100,
            "sub_category": {"x": 42, "y": 84},
        },
        "category_b": {"label": "test"},
        "flat_value": 10,
    }
