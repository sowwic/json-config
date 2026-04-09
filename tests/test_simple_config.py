import pathlib

from json_config.api import SimpleConfig


def test_init_empty_config(simple_config_output_dir: pathlib.Path):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / "test_init_empty_config.json"

    TestConfig.load()
    assert TestConfig.FILE_PATH.is_file()


def test_init_config_with_multiple_variables(simple_config_output_dir: pathlib.Path):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / "test_init_mutiple_values_config.json"

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


def test_config_reset(simple_config_output_dir: pathlib.Path):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / "test_reset_config.json"

        int_value: int = 5

    instance = TestConfig.load()
    instance.int_value = 10
    instance.save()
    assert instance.int_value == 10

    instance = TestConfig.reset()
    assert hasattr(instance, "int_value")
    assert instance.int_value == 5


def test_config_get_fields_names(simple_config_output_dir: pathlib.Path):
    class TestConfig(SimpleConfig):
        FILE_PATH = simple_config_output_dir / "test_get_field_names_config.json"

        int_value: int = 5
        str_value: str = "test_value"

    TestConfig.load()
    field_names = TestConfig.get_fields_names()
    assert field_names == {"int_value", "str_value"}
