import json
import pathlib

import pytest
from pydantic import Field

from json_config.api import (
    ConfigLayer,
    ConfigValues,
    LayeredConfig,
    ConfigLayerManager,
)


def test_init_with_single_layer(
    simple_config_file: pathlib.Path,
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    class TestValues(ConfigValues):
        int_value: int = 0

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = ConfigLayerManager()
    root_layer = ConfigLayer("root", file_path=simple_config_file)
    manager.register(root_layer)
    manager.load_all()

    config = TestConfig(manager)
    assert config.values.int_value == 0
    config.resolve()
    assert config.values.int_value == 5

    config.values.int_value = 10
    config.layer_manager["root"].file_path = (
        config_output_dir / f"{request.node.name}_config.json"
    )
    config.save()


def test_defaults_writing(
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that defaults are written to the root layer file when saving."""

    class TestValues(ConfigValues):
        int_value: int = Field(default=0)
        str_value: str = Field(default="default")
        list_value: list[str] = Field(default_factory=lambda: ["a", "b", "c"])

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    # Setup manager
    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root", file_path=config_output_dir / f"{request.node.name}_config.json"
    )
    extra_root_layer = ConfigLayer(
        "extra_root",
        file_path=config_output_dir / f"{request.node.name}_extra_root_config.json",
    )
    extra_child_layer = ConfigLayer(
        "extra",
        file_path=config_output_dir / f"{request.node.name}_extra_config.json",
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
        root_layer.get_data() == extra_root_layer.get_data() == TestValues.get_defaults()
    )
    # The extra layer file should not be created as it's empty
    assert extra_child_layer.get_data() == {}
    assert not extra_child_layer.file_path.is_file()


def test_layer_filter_limits_resolve_to_expected_values(
    preset_app_manager: ConfigLayerManager,
):
    """Test that layer filtering limits resolve to the expected values."""

    class TestConfig(LayeredConfig[ConfigValues]):
        VALUES_CLASS = ConfigValues

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
    preset_app_manager: ConfigLayerManager,
):
    """Test that resolving with an invalid layer filter raises a ValueError."""

    class TestConfig(LayeredConfig[ConfigValues]):
        VALUES_CLASS = ConfigValues

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
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that saving a ConfigValues with category fields produces the
    expected nested JSON structure through a single ConfigLayer/file."""

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root", file_path=config_output_dir / f"{request.node.name}_config.json"
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
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test load -> resolve -> mutate a nested category value -> save round-trips."""

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root", file_path=config_output_dir / f"{request.node.name}_config.json"
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
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that a child layer overriding only part of a category is deep-merged
    with the root layer's defaults for that same category."""
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
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
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Regression test: save/load/mutate/save round-trips correctly through
    three levels of category nesting (category_a.sub_category.x/y)."""

    class TestConfig(LayeredConfig[nested_category_values_class]):
        VALUES_CLASS = nested_category_values_class

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root", file_path=config_output_dir / f"{request.node.name}_config.json"
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


def test_save_to_fresh_child_layer_persists_changed_values(
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Regression test: saving with a layer filter pointing at a child layer
    that has never been written to before must actually persist the current
    values.

    Previously, ``write_to_layer`` only wrote keys that already existed in
    the target layer's own data, which meant nothing could ever be written
    to a brand new, previously-empty layer.
    """

    class TestValues(ConfigValues):
        theme: str = "light"
        font_size: int = 12

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root", file_path=config_output_dir / f"{request.node.name}_root.json"
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    config = TestConfig(manager, layer_filter="child")
    config.resolve()
    config.values.theme = "dark"
    config.save()

    # The change was persisted...
    assert child_layer.get_data() == {"theme": "dark"}
    assert child_layer.file_path.is_file()
    # ...but the unchanged sibling field is not duplicated into the child
    # layer -- it should stay a sparse override file.
    assert "font_size" not in child_layer.get_data()

    on_disk = json.loads(child_layer.file_path.read_text())
    assert on_disk == {"theme": "dark"}


def test_save_removes_override_that_now_matches_parent_layer(
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Regression test: if a value in a child layer is set back to the same
    value as its parent layer, the override must be removed from the child
    layer entirely (rather than remaining as a stale, redundant override).
    """

    class TestValues(ConfigValues):
        option1: int = 0

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    # Seed root with option1=1, and child with an override of option1=2.
    root_layer.set(option1=1)
    root_layer.save()
    child_layer.set(option1=2)
    child_layer.save()

    manager.load_all()
    config = TestConfig(manager, layer_filter="child")
    config.resolve()
    assert config.values.option1 == 2

    # Set the child's value back to the same value as the parent layer.
    config.values.option1 = 1
    config.save()

    # The override must be gone entirely from the child layer...
    assert "option1" not in child_layer.get_data()
    on_disk = json.loads(child_layer.file_path.read_text())
    assert on_disk == {}

    # ...and the resolved value should still be correct (inherited from root).
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    assert config2.values.option1 == 1


def test_save_removes_nested_category_override_that_now_matches_parent(
    category_values_class: type[ConfigValues],
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Regression test: the same override-pruning behavior must apply to
    nested category values, not just flat top-level fields.

    If a nested category value in a child layer is set back so the whole
    category matches what the parent layer would already provide, the
    entire category key must be removed from the child layer.
    """
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    # Seed root defaults: category_a.field_one=100, field_two=100.
    config = TestConfig(manager)
    config.save()

    # Override category_a in the child layer.
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    config2.values.category_a.field_one = 4000
    config2.save()

    assert child_layer.get_data() == {"category_a": {"field_one": 4000}}

    # Now set the whole category back to match the parent's values exactly.
    manager.load_all()
    config3 = TestConfig(manager, layer_filter="child")
    config3.resolve()
    assert config3.values.category_a.field_one == 4000
    config3.values.category_a.field_one = 100
    config3.save()

    # The entire category override must be gone from the child layer...
    assert "category_a" not in child_layer.get_data()
    on_disk = json.loads(child_layer.file_path.read_text())
    assert "category_a" not in on_disk

    # ...and the resolved value should still be correct (inherited from root).
    manager.load_all()
    config4 = TestConfig(manager, layer_filter="child")
    config4.resolve()
    assert config4.values.category_a.field_one == 100
    assert config4.values.category_a.field_two == 100


def test_save_prunes_nested_category_field_that_now_matches_parent(
    category_values_class: type[ConfigValues],
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Pruning is per-field within nested categories: if only part of an
    overridden category is reverted to the parent's value while another
    field in that same category still diverges, only the reverted field is
    dropped -- the still-diverging field remains as an override, and the
    matching one does not.
    """
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    # Seed root defaults: category_a.field_one=100, field_two=100.
    config = TestConfig(manager)
    config.save()

    # Override both fields of category_a in the child layer.
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    config2.values.category_a.field_one = 4000
    config2.values.category_a.field_two = 5000
    config2.save()

    assert child_layer.get_data() == {
        "category_a": {"field_one": 4000, "field_two": 5000}
    }

    # Revert only field_one back to the parent's value; field_two still diverges.
    manager.load_all()
    config3 = TestConfig(manager, layer_filter="child")
    config3.resolve()
    config3.values.category_a.field_one = 100
    config3.save()

    # Only field_two remains as an override; field_one was pruned since it
    # now matches the parent's value.
    assert child_layer.get_data() == {"category_a": {"field_two": 5000}}
    on_disk = json.loads(child_layer.file_path.read_text())
    assert on_disk == {"category_a": {"field_two": 5000}}

    manager.load_all()
    config4 = TestConfig(manager, layer_filter="child")
    config4.resolve()
    assert config4.values.category_a.field_one == 100
    assert config4.values.category_a.field_two == 5000


def test_save_prunes_three_level_nested_category_field_that_now_matches_parent(
    nested_category_values_class: type[ConfigValues],
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Per-field pruning must also work through three levels of category
    nesting (category_a.sub_category.x/y): reverting just ``x`` back to the
    parent's value should drop only ``x``, leaving ``y`` (still diverging)
    and the rest of the structure intact.
    """
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[nested_category_values_class]):
        VALUES_CLASS = nested_category_values_class

    # Seed root defaults: category_a.{field_one,field_two}=100,
    # category_a.sub_category.{x,y}=0.
    config = TestConfig(manager)
    config.save()

    # Override both x and y (three levels deep) in the child layer.
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    config2.values.category_a.sub_category.x = 42
    config2.values.category_a.sub_category.y = 84
    config2.save()

    assert child_layer.get_data() == {"category_a": {"sub_category": {"x": 42, "y": 84}}}

    # Revert only x back to the parent's value; y still diverges.
    manager.load_all()
    config3 = TestConfig(manager, layer_filter="child")
    config3.resolve()
    config3.values.category_a.sub_category.x = 0
    config3.save()

    # Only y remains as an override, nested three levels deep; x and the
    # rest of category_a were pruned entirely since they now match root.
    assert child_layer.get_data() == {"category_a": {"sub_category": {"y": 84}}}
    on_disk = json.loads(child_layer.file_path.read_text())
    assert on_disk == {"category_a": {"sub_category": {"y": 84}}}

    manager.load_all()
    config4 = TestConfig(manager, layer_filter="child")
    config4.resolve()
    assert config4.values.category_a.field_one == 100
    assert config4.values.category_a.field_two == 100
    assert config4.values.category_a.sub_category.x == 0
    assert config4.values.category_a.sub_category.y == 84


def test_revert_value_removes_flat_override_from_current_layer(
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """``revert_value`` should immediately drop a flat field's override
    from the current layer's own data and update ``values`` in-memory to
    whatever would be inherited from that layer's dependencies.
    """

    class TestValues(ConfigValues):
        option1: int = 0

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    root_layer.set(option1=1)
    root_layer.save()
    child_layer.set(option1=2)
    child_layer.save()

    manager.load_all()
    config = TestConfig(manager, layer_filter="child")
    config.resolve()
    assert config.values.option1 == 2

    assert "option1" in TestValues.model_fields
    config.revert_value("option1")

    # The override is gone from the layer's own data immediately...
    assert "option1" not in child_layer.get_data()
    # ...and the in-memory value now reflects the inherited (root) value.
    assert config.values.option1 == 1

    # Persisting confirms the override stays gone on disk too.
    config.save()
    on_disk = json.loads(child_layer.file_path.read_text())
    assert on_disk == {}


def test_revert_value_falls_back_to_default_with_no_dependency_value(
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """If no dependency layer provides a value for the reverted field
    either, ``revert_value`` should fall back to the field's own default."""

    class TestValues(ConfigValues):
        option1: int = 7

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    manager.register(root_layer)
    manager.load_all()

    test_option_name = "option1"

    config = TestConfig(manager)
    config.values.option1 = 99
    config.save()
    assert root_layer.get_data() == {test_option_name: 99}

    config.revert_value(test_option_name)

    assert test_option_name not in root_layer.get_data()
    assert config.values.option1 == 7


def test_revert_value_removes_nested_category_override_from_current_layer(
    category_values_class: type[ConfigValues],
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """``revert_value`` should also work for a category field, removing the
    whole category's override from the current layer and restoring the
    in-memory value to whatever is inherited from its dependencies.
    """
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    # Seed root defaults: category_a.field_one=100, field_two=100.
    config = TestConfig(manager)
    config.save()

    # Override category_a in the child layer.
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    config2.values.category_a.field_one = 4000
    config2.values.category_a.field_two = 5000
    config2.save()

    assert child_layer.get_data() == {
        "category_a": {"field_one": 4000, "field_two": 5000}
    }

    config2.revert_value("category_a")

    # The whole category override is gone from the layer immediately...
    assert "category_a" not in child_layer.get_data()
    # ...and the in-memory value now reflects the inherited (root) values.
    assert config2.values.category_a.field_one == 100
    assert config2.values.category_a.field_two == 100


def test_revert_value_with_dotted_path_only_reverts_leaf_field(
    category_values_class: type[ConfigValues],
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """A dot-separated path string lets ``revert_value`` target a single
    leaf field nested within a category, leaving sibling overrides in that
    same category untouched -- e.g.::

        config.revert_value("category_a.field_one")
    """
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[category_values_class]):
        VALUES_CLASS = category_values_class

    # Seed root defaults: category_a.field_one=100, field_two=100.
    config = TestConfig(manager)
    config.save()

    # Override both fields of category_a in the child layer.
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    config2.values.category_a.field_one = 4000
    config2.values.category_a.field_two = 5000
    config2.save()

    assert child_layer.get_data() == {
        "category_a": {"field_one": 4000, "field_two": 5000}
    }

    # Revert only field_one via its dotted path; field_two must stay overridden.
    config2.revert_value("category_a.field_one")

    assert child_layer.get_data() == {"category_a": {"field_two": 5000}}
    assert config2.values.category_a.field_one == 100
    assert config2.values.category_a.field_two == 5000

    config2.save()
    on_disk = json.loads(child_layer.file_path.read_text())
    assert on_disk == {"category_a": {"field_two": 5000}}


def test_revert_value_with_dotted_path_supports_three_levels_of_nesting(
    nested_category_values_class: type[ConfigValues],
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """A dotted path can also address a leaf field three levels deep, e.g.
    ``"category_a.sub_category.x"``."""
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    child_layer = ConfigLayer(
        "child",
        file_path=config_output_dir / f"{request.node.name}_child.json",
        depends_on=["root"],
    )
    manager = ConfigLayerManager()
    manager.register(root_layer)
    manager.register(child_layer)
    manager.load_all()

    class TestConfig(LayeredConfig[nested_category_values_class]):
        VALUES_CLASS = nested_category_values_class

    # Seed root defaults: category_a.sub_category.{x,y}=0.
    config = TestConfig(manager)
    config.save()

    # Override both x and y (three levels deep) in the child layer.
    manager.load_all()
    config2 = TestConfig(manager, layer_filter="child")
    config2.resolve()
    config2.values.category_a.sub_category.x = 42
    config2.values.category_a.sub_category.y = 84
    config2.save()

    assert child_layer.get_data() == {"category_a": {"sub_category": {"x": 42, "y": 84}}}

    # Revert only x via its dotted path; y must stay overridden.
    config2.revert_value("category_a.sub_category.x")

    assert child_layer.get_data() == {"category_a": {"sub_category": {"y": 84}}}
    assert config2.values.category_a.sub_category.x == 0
    assert config2.values.category_a.sub_category.y == 84


def test_revert_value_raises_for_field_not_on_values_class(
    config_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """``revert_value`` should reject a field that doesn't belong to this
    config's ``VALUES_CLASS``."""

    class TestValues(ConfigValues):
        option1: int = 0

    class OtherValues(ConfigValues):
        other_option: int = 0

    class TestConfig(LayeredConfig[TestValues]):
        VALUES_CLASS = TestValues

    manager = ConfigLayerManager()
    root_layer = ConfigLayer(
        "root",
        file_path=config_output_dir / f"{request.node.name}_root.json",
    )
    manager.register(root_layer)
    manager.load_all()

    config = TestConfig(manager)
    with pytest.raises(ValueError):
        config.revert_value("other_option")
