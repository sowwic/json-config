import pathlib

import pytest

from json_config.api import ConfigLayer, LayeredConfigManager, SimpleConfig

TESTS_DIR = pathlib.Path.cwd() / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"

FIXTURE_LAYERS_DIR = FIXTURES_DIR / "app_layers"
MAIN_CONFIG_FIXTURE = FIXTURE_LAYERS_DIR / "main.json"
WORKSPACE_CONFIG_FIXTURE = FIXTURE_LAYERS_DIR / "workspace.json"
USER_CONFIG_FIXTURE = FIXTURE_LAYERS_DIR / "user.json"
SIMPLE_CONFIG_FIXTURE = FIXTURES_DIR / "simple_config.json"

FIXTURE_USER_LAYERS_DIR = FIXTURES_DIR / "user_layers"
USER_DEFAULT_FIXTURE = FIXTURE_USER_LAYERS_DIR / "default.json"
USER1_FIXTURE = FIXTURE_USER_LAYERS_DIR / "user1.json"
USER2_FIXTURE = FIXTURE_USER_LAYERS_DIR / "user2.json"


@pytest.fixture(autouse=True)
def fresh_manager() -> None:
    yield
    LayeredConfigManager.clear()


@pytest.fixture(autouse=True)
def fresh_simple_config() -> None:
    yield
    SimpleConfig.clear_instances()


@pytest.fixture(scope="session")
def output_dir() -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    out_dir = pathlib.Path.cwd() / ".test_output"
    out_dir.mkdir(exist_ok=True)
    return out_dir


@pytest.fixture(scope="session")
def simple_config_output_dir() -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    out_dir = pathlib.Path.cwd() / ".test_output" / "simple_config"
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


@pytest.fixture(scope="session")
def layered_config_output_dir() -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    out_dir = pathlib.Path.cwd() / ".test_output" / "layered_config"
    out_dir.mkdir(exist_ok=True, parents=True)
    return out_dir


@pytest.fixture()
def preset_app_manager() -> LayeredConfigManager:
    manager = LayeredConfigManager()
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
    LayeredConfigManager.clear()


@pytest.fixture()
def preset_user_manager() -> LayeredConfigManager:
    manager = LayeredConfigManager()
    default_layer = ConfigLayer("default", file_path=USER_DEFAULT_FIXTURE)
    user1_layer = ConfigLayer("user1", file_path=USER1_FIXTURE, depends_on=["default"])
    user2_layer = ConfigLayer("user2", file_path=USER2_FIXTURE, depends_on=["default"])

    manager.register(default_layer)
    manager.register(user1_layer)
    manager.register(user2_layer)
    yield manager
    LayeredConfigManager.clear()


@pytest.fixture(scope="session")
def simple_config_file() -> pathlib.Path:
    """Path to a simple config file for testing.

    Returns:
        pathlib.Path: path to test output directory.

    """
    return pathlib.Path.cwd() / "tests/fixtures/simple_config.json"


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
