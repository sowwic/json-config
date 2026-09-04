import json
import pathlib

import pytest
from pydantic import Field

from json_config.api import ConfigValues

# ---------------------------------------------------------------------------
# category metadata support (single level of nesting)
# ---------------------------------------------------------------------------


def test_get_defaults_expands_category_fields_into_nested_dicts(
    category_values_class: type[ConfigValues],
):
    """Test that get_defaults() nests category-tagged fields by category name."""
    assert category_values_class.get_defaults() == {
        "category_a": {"field_one": 100, "field_two": 100},
        "category_b": {"label": "test"},
        "flat_value": 10,
    }


def test_to_dict_nests_category_fields_by_category_name(
    category_values_class: type[ConfigValues],
):
    """Test that to_dict() mirrors get_defaults() for a freshly built instance."""
    values = category_values_class()
    assert values.to_dict() == {
        "category_a": {"field_one": 100, "field_two": 100},
        "category_b": {"label": "test"},
        "flat_value": 10,
    }


def test_to_dict_reflects_mutated_nested_values(
    category_values_class: type[ConfigValues],
):
    """Test that to_dict() reflects in-place mutations of nested category values."""
    values = category_values_class()
    values.category_a.field_one = 1920
    values.flat_value = 42
    assert values.to_dict() == {
        "category_a": {"field_one": 1920, "field_two": 100},
        "category_b": {"label": "test"},
        "flat_value": 42,
    }


def test_replace_updates_nested_category_field_and_preserves_siblings(
    category_values_class: type[ConfigValues],
):
    """Test that replace() recurses into category fields, keyed by category name."""
    values = category_values_class()
    updated = values.replace({"category_a": {"field_one": 1024}})

    assert updated.category_a.field_one == 1024
    # field_two wasn't in the update dict, so it should be preserved.
    assert updated.category_a.field_two == 100
    # Unrelated category and flat field must be untouched.
    assert updated.category_b.label == "test"
    assert updated.flat_value == 10


def test_replace_with_full_nested_dict(category_values_class: type[ConfigValues]):
    """Test that replace() accepts a fully-specified nested dict (round-trip)."""
    values = category_values_class()
    resolved = values.to_dict()
    resolved["category_a"]["field_one"] = 4
    resolved["category_b"]["label"] = "prod"
    resolved["flat_value"] = 99

    updated = values.replace(resolved)
    assert updated.to_dict() == resolved


def test_category_key_can_differ_from_field_name():
    """Test that the category metadata value, not the attribute name, is used
    as the serialized key."""

    class InnerValues(ConfigValues):
        value: int = 1

    class OuterValues(ConfigValues):
        inner: InnerValues = Field(
            default_factory=InnerValues, alias="renamed"
        )

    values = OuterValues()
    assert values.to_dict() == {"renamed": {"value": 1}}
    assert OuterValues.get_defaults() == {"renamed": {"value": 1}}

    updated = values.replace({"renamed": {"value": 5}})
    assert updated.inner.value == 5


def test_nested_config_values_without_category_raises_value_error():
    """Test that a nested ConfigValues field missing category metadata
    raises a ValueError as soon as the outer class is instantiated."""

    class InnerValues(ConfigValues):
        value: int = 1

    class OuterValues(ConfigValues):
        inner: InnerValues = Field(default_factory=InnerValues)

    with pytest.raises(ValueError, match="inner"):
        OuterValues()


# ---------------------------------------------------------------------------
# multi-level (3+) category nesting
# ---------------------------------------------------------------------------


def test_get_defaults_supports_three_levels_of_category_nesting(
    nested_category_values_class: type[ConfigValues],
):
    """Test that get_defaults() recurses through multiple levels of nesting."""
    assert nested_category_values_class.get_defaults() == {
        "category_a": {
            "field_one": 100,
            "field_two": 100,
            "sub_category": {"x": 0, "y": 0},
        },
        "category_b": {"label": "test"},
        "flat_value": 10,
    }


def test_to_dict_supports_three_levels_of_category_nesting(
    nested_category_values_class: type[ConfigValues],
):
    """Test that to_dict() recurses through multiple levels of nesting."""
    values = nested_category_values_class()
    assert values.to_dict() == {
        "category_a": {
            "field_one": 100,
            "field_two": 100,
            "sub_category": {"x": 0, "y": 0},
        },
        "category_b": {"label": "test"},
        "flat_value": 10,
    }


def test_replace_updates_deeply_nested_category_and_preserves_siblings(
    nested_category_values_class: type[ConfigValues],
):
    """Test that replace() recurses through multiple levels, keyed by category,
    leaving sibling values at every level untouched."""
    values = nested_category_values_class()
    updated = values.replace({"category_a": {"sub_category": {"x": 42}}})

    # The deeply-nested value was updated.
    assert updated.category_a.sub_category.x == 42
    # Its sibling at the same (deepest) level is preserved.
    assert updated.category_a.sub_category.y == 0
    # Siblings at the intermediate level are preserved.
    assert updated.category_a.field_one == 100
    assert updated.category_a.field_two == 100
    # Unrelated top-level category and flat field are untouched.
    assert updated.category_b.label == "test"
    assert updated.flat_value == 10


# ---------------------------------------------------------------------------
# JSON round-tripping (to_dict()/replace() against actual files on disk)
# ---------------------------------------------------------------------------


def test_to_dict_json_round_trip_supports_three_levels_of_nesting(
    nested_category_values_class: type[ConfigValues],
    config_values_output_dir: pathlib.Path,
    request: pytest.FixtureRequest,
):
    """Test that to_dict() produces a JSON-serializable structure that can be
    written to disk and loaded back via replace() without any loss, through
    three levels of category nesting."""
    values = nested_category_values_class()
    values.category_a.field_one = 1920
    values.category_a.sub_category.x = 42
    values.category_a.sub_category.y = 84
    values.category_b.label = "prod"
    values.flat_value = 99

    output_file = config_values_output_dir / f"{request.node.name}.json"
    output_file.write_text(json.dumps(values.to_dict(), indent=4))

    loaded = json.loads(output_file.read_text())
    restored = nested_category_values_class().replace(loaded)

    assert restored.to_dict() == values.to_dict()
