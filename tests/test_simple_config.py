import json
import pathlib

import pytest

from json_config.api import SimpleConfig


def test_init_empty(
    simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_config.json"

    TestConfig.load()
    assert TestConfig.FILE_PATH.is_file()


def test_init_with_multiple_variables(
    simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_config.json"

        int_value: int = 5
        str_value: str = "test_value"
        list_value: list = [2, 4, 6]
        dict_value: dict = {"a": [2, 3, 5]}

    instance = TestConfig.load()
    instance.save()
    assert hasattr(instance, "int_value")
    assert instance.int_value == 5
    assert hasattr(instance, "str_value")
    assert instance.str_value == "test_value"
    assert hasattr(instance, "list_value")
    assert instance.list_value == [2, 4, 6]
    assert hasattr(instance, "dict_value")
    assert instance.dict_value == {"a": [2, 3, 5]}


def test_reset(simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_config.json"

        int_value: int = 5

    instance = TestConfig.load()
    instance.int_value = 10
    instance.save()
    assert instance.int_value == 10

    instance = TestConfig.reset()
    assert hasattr(instance, "int_value")
    assert instance.int_value == 5


def test_get_fields_names(
    simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_config.json"

        int_value: int = 5
        str_value: str = "test_value"

    TestConfig.load()
    field_names = TestConfig.get_fields_names()
    assert field_names == {"int_value", "str_value"}


def test_multiple_config_classes_do_not_share_singleton_cache(
    simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """Regression test: resetting one SimpleConfig subclass must not clear
    or evict the cached singleton instance of a different subclass.

    ``Singleton._instances`` is a single dict shared by every SimpleConfig
    subclass (keyed by class). ``clear_instances()`` must only remove *its
    own* class's entry from that shared dict.
    """

    class ConfigA(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_a_config.json"

        value: int = 1

    class ConfigB(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_b_config.json"

        value: int = 2

    a = ConfigA.load()
    b = ConfigB.load()
    a.value = 100
    b.value = 200

    ConfigA.reset()

    assert ConfigB() is b
    assert ConfigB().value == 200


def test_loading_one_config_class_does_not_skip_loading_another(
    simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """Regression test: load() must check whether *this specific* class
    already has a cached singleton instance, not whether *any*
    SimpleConfig subclass does.
    """

    class ConfigA(SimpleConfig):
        FILE_PATH = simple_config_output_dir / f"{request.node.name}_a_config.json"

        value: int = 1

    # Prime the shared singleton registry with ConfigA's cached instance.
    ConfigA.load()

    b_path = simple_config_output_dir / f"{request.node.name}_b_config.json"
    b_path.write_text(json.dumps({"value": 999}))

    class ConfigB(SimpleConfig):
        FILE_PATH = b_path

        value: int = 2

    instance = ConfigB.load()
    assert instance.value == 999


def test_load_creates_missing_nested_directories(
    simple_config_output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """Regression test: FILE_PATH nested several directories deep (where
    none of the intermediate directories exist yet) must be created
    correctly rather than raising FileNotFoundError.
    """
    nested_dir = simple_config_output_dir / request.node.name / "a" / "b" / "c"

    class NestedConfig(SimpleConfig):
        FILE_PATH = nested_dir / "config.json"

        value: int = 1

    instance = NestedConfig.load()
    assert instance.value == 1
    assert NestedConfig.FILE_PATH.is_file()
