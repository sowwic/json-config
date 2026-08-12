import dataclasses
import pathlib
import shutil

import pytest

from json_config.api import ConfigLayer, ConfigValues, ConfigLayerManager

TESTS_DIR = pathlib.Path.cwd() / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"
TEST_OUTPUT_DIR = pathlib.Path.cwd() / ".test_output"

# Config testing fixtures
CONFIG_TESTING_FIXTURES_DIR = FIXTURES_DIR / "config_testing"
FIXTURE_LAYERS_DIR = CONFIG_TESTING_FIXTURES_DIR / "app_layers"
MAIN_CONFIG_FIXTURE = FIXTURE_LAYERS_DIR / "main.json"
WORKSPACE_CONFIG_FIXTURE = FIXTURE_LAYERS_DIR / "workspace.json"
USER_CONFIG_FIXTURE = FIXTURE_LAYERS_DIR / "user.json"
SIMPLE_CONFIG_FIXTURE = CONFIG_TESTING_FIXTURES_DIR / "simple_config.json"

FIXTURE_USER_LAYERS_DIR = CONFIG_TESTING_FIXTURES_DIR / "user_layers"
USER_DEFAULT_FIXTURE = FIXTURE_USER_LAYERS_DIR / "default.json"
USER1_FIXTURE = FIXTURE_USER_LAYERS_DIR / "user1.json"
USER2_FIXTURE = FIXTURE_USER_LAYERS_DIR / "user2.json"

# Layer file fixtures
LAYER_TESTING_FIXTURES_DIR = FIXTURES_DIR / "layer_testing"
EMPTY_LAYER_FILE = LAYER_TESTING_FIXTURES_DIR / "empty_layer.json"
INVALID_NOT_DICT_LAYER = LAYER_TESTING_FIXTURES_DIR / "invalid_not_dict_layer.json"


# ---------------------------------------------------------------------------
# ConfigValues category-nesting fixtures
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _CategoryAValues(ConfigValues):
    field_one: int = 100
    field_two: int = 100


@dataclasses.dataclass
class _CategoryBValues(ConfigValues):
    label: str = "test"


@dataclasses.dataclass
class _CategoryValues(ConfigValues):
    """ConfigValues with a single level of category nesting.

    Structure::

        category_a (category) -> field_one, field_two
        category_b (category) -> label
        flat_value            -> flat field
    """

    category_a: _CategoryAValues = dataclasses.field(
        default_factory=_CategoryAValues, metadata={"category": "category_a"}
    )
    category_b: _CategoryBValues = dataclasses.field(
        default_factory=_CategoryBValues, metadata={"category": "category_b"}
    )
    flat_value: int = 10


@dataclasses.dataclass
class _SubCategoryValues(ConfigValues):
    x: int = 0
    y: int = 0


@dataclasses.dataclass
class _NestedCategoryAValues(ConfigValues):
    field_one: int = 100
    field_two: int = 100
    sub_category: _SubCategoryValues = dataclasses.field(
        default_factory=_SubCategoryValues, metadata={"category": "sub_category"}
    )


@dataclasses.dataclass
class _NestedCategoryValues(ConfigValues):
    """ConfigValues with three levels of category nesting.

    Structure::

        category_a (category) -> field_one, field_two, sub_category (category) -> x, y
        category_b (category) -> label
        flat_value            -> flat field
    """

    category_a: _NestedCategoryAValues = dataclasses.field(
        default_factory=_NestedCategoryAValues, metadata={"category": "category_a"}
    )
    category_b: _CategoryBValues = dataclasses.field(
        default_factory=_CategoryBValues, metadata={"category": "category_b"}
    )
    flat_value: int = 10


# One subdirectory per test module that may write output under
# TEST_OUTPUT_DIR, so the layout is predictable even for modules that don't
# currently exercise their own output dir fixture.
_TEST_OUTPUT_SUBDIRS = (
    "config",
    "config_values",
    "layer_manager",
    "config_layer",
)


@pytest.fixture(scope="session", autouse=True)
def _clean_test_output_dir() -> None:
    """Remove any leftover .test_output directory at the start of the session,
    then recreate its per-module subdirectories.

    The various *_output_dir fixtures below only ever `mkdir(exist_ok=True)`
    and never clean up after themselves, so stale files from a previous run
    (e.g. written under an old field/category name) could otherwise bleed
    into a fresh run's assertions. Subdirectories are (re)created eagerly
    here so the expected layout exists even for modules that don't
    currently request their output dir fixture.
    """
    shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)
    for subdir in _TEST_OUTPUT_SUBDIRS:
        (TEST_OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def fresh_manager() -> None:
    yield
    ConfigLayerManager.clear()


@pytest.fixture(scope="session")
def output_dir() -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)
    return TEST_OUTPUT_DIR


@pytest.fixture(scope="session")
def config_output_dir() -> pathlib.Path:
    """Output directory for tests in ``test_config.py``.

    Returns:
        pathlib.Path: path to test output directory.

    """
    out_dir = TEST_OUTPUT_DIR / "config"
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


@pytest.fixture(scope="session")
def config_values_output_dir() -> pathlib.Path:
    """Output directory for tests in ``test_config_values.py``.

    Returns:
        pathlib.Path: path to test output directory.
    """
    out_dir = TEST_OUTPUT_DIR / "config_values"
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


@pytest.fixture(scope="session")
def layer_manager_output_dir() -> pathlib.Path:
    """Output directory for tests in ``test_layer_manager.py``.

    Returns:
        pathlib.Path: path to test output directory.
    """
    out_dir = TEST_OUTPUT_DIR / "layer_manager"
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


@pytest.fixture(scope="session")
def config_layer_output_dir() -> pathlib.Path:
    """Output directory for tests in ``test_config_layer.py``.

    Returns:
        pathlib.Path: path to test output directory.
    """
    out_dir = TEST_OUTPUT_DIR / "config_layer"
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


@pytest.fixture()
def preset_app_manager() -> ConfigLayerManager:
    manager = ConfigLayerManager()
    main_layer = ConfigLayer("main", file_path=MAIN_CONFIG_FIXTURE)
    workspace_layer = ConfigLayer(
        "workspace", file_path=WORKSPACE_CONFIG_FIXTURE, depends_on=["main"]
    )
    user_layer = ConfigLayer(
        "user", file_path=USER_CONFIG_FIXTURE, depends_on=["workspace"]
    )

    manager.register(main_layer)
    manager.register(workspace_layer)
    manager.register(user_layer)
    yield manager
    ConfigLayerManager.clear()


@pytest.fixture()
def preset_user_manager() -> ConfigLayerManager:
    manager = ConfigLayerManager()
    default_layer = ConfigLayer("default", file_path=USER_DEFAULT_FIXTURE)
    user1_layer = ConfigLayer("user1", file_path=USER1_FIXTURE, depends_on=["default"])
    user2_layer = ConfigLayer("user2", file_path=USER2_FIXTURE, depends_on=["default"])

    manager.register(default_layer)
    manager.register(user1_layer)
    manager.register(user2_layer)
    yield manager
    ConfigLayerManager.clear()


@pytest.fixture()
def category_values_class() -> type[_CategoryValues]:
    """ConfigValues class with a single level of category nesting.

    Returns:
        type[_CategoryValues]: The ConfigValues subclass
            (category_a/category_b/flat_value).
    """
    return _CategoryValues


@pytest.fixture()
def nested_category_values_class() -> type[_NestedCategoryValues]:
    """ConfigValues class with three levels of category nesting.

    Returns:
        type[_NestedCategoryValues]: The ConfigValues subclass with a nested
            category_a.sub_category category.
    """
    return _NestedCategoryValues


@pytest.fixture(scope="session")
def simple_config_file() -> pathlib.Path:
    """Path to a simple config file for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return SIMPLE_CONFIG_FIXTURE


@pytest.fixture(scope="session")
def main_config_file() -> pathlib.Path:
    """Path to a simple root config file for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return MAIN_CONFIG_FIXTURE


@pytest.fixture(scope="session")
def workspace_config_file() -> pathlib.Path:
    """Path to a simple workspace config file for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return WORKSPACE_CONFIG_FIXTURE


@pytest.fixture(scope="session")
def user_config_file() -> pathlib.Path:
    """Path to a simple user config file for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return USER_CONFIG_FIXTURE


@pytest.fixture(scope="session")
def empty_layer_file() -> pathlib.Path:
    """Path to an empty layer file for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return EMPTY_LAYER_FILE


@pytest.fixture(scope="session")
def invalid_not_dict_layer() -> pathlib.Path:
    """Path to an invalid layer file that is not a dict for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return INVALID_NOT_DICT_LAYER
