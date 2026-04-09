import pathlib

from json_config.api import ConfigLayer, LayeredConfigManager


def test_init_with_single_layer(simple_config_file: pathlib.Path) -> None:
    """Test initializing with a single layer and resolving values."""
    manager = LayeredConfigManager()
    layer = ConfigLayer("main", file_path=simple_config_file)
    manager.register(layer)
    manager.load_all()
    assert layer.get_data() == manager.resolve()


def test_init_with_multiple_layers(
    main_config_file: pathlib.Path,
    workspace_config_file: pathlib.Path,
    user_config_file: pathlib.Path,
) -> None:
    """Test resolving values from multiple layers with dependencies."""
    manager = LayeredConfigManager()
    main_layer = ConfigLayer("main", file_path=main_config_file)
    workspace_layer = ConfigLayer(
        "workspace", file_path=workspace_config_file, depends_on=["main"]
    )
    user_layer = ConfigLayer(
        "user", file_path=user_config_file, depends_on=["workspace"]
    )

    manager.register(main_layer)
    manager.register(workspace_layer)
    manager.register(user_layer)
    manager.load_all()

    assert main_layer.get_data() != manager.resolve()
    assert user_layer.get_data()["int_value"] == manager.resolve()["int_value"]
    assert user_layer.get_data()["dict_value"] == manager.resolve()["dict_value"]
    assert workspace_layer.get_data()["str_value"] == manager.resolve()["str_value"]


def test_init_from_path_tree(
    main_config_file: pathlib.Path,
    workspace_config_file: pathlib.Path,
    user_config_file: pathlib.Path,
) -> None:
    """Test resolving values from multiple layers with dependencies."""
    path_tree = {main_config_file: {workspace_config_file: {user_config_file: {}}}}
    manager = LayeredConfigManager()
    manager.register_from_paths_tree(path_tree)
    manager.load_all()

    assert manager["main"].get_data() != manager.resolve()
    assert manager["user"].get_data()["int_value"] == manager.resolve()["int_value"]
    assert manager["user"].get_data()["dict_value"] == manager.resolve()["dict_value"]
    assert (
        manager["workspace"].get_data()["str_value"] == manager.resolve()["str_value"]
    )


def test_loading_to_layer(preset_app_manager: LayeredConfigManager) -> None:
    """Test loading a layer from its file and resolving it."""
    preset_app_manager.load_all()
    config_dict = preset_app_manager.resolve(up_to="main")
    assert config_dict == preset_app_manager["main"].get_data()

    config_dict = preset_app_manager.resolve(up_to="workspace")
    assert (
        config_dict["str_value"]
        == preset_app_manager["workspace"].get_data()["str_value"]
    )


def test_load_branching_configs(preset_user_manager: LayeredConfigManager) -> None:
    """Test loading a branching config with multiple layers."""
    ...
    preset_user_manager.load_all()
    config_dict = preset_user_manager.resolve(up_to="user1")
    assert (
        config_dict["user_name"] == preset_user_manager["user1"].get_data()["user_name"]
    )
    config_dict = preset_user_manager.resolve(up_to="user2")
    assert (
        config_dict["user_name"] == preset_user_manager["user2"].get_data()["user_name"]
    )


def test_multiple_root_configs(
    main_config_file: pathlib.Path,
    workspace_config_file: pathlib.Path,
) -> None:
    """Test resolving a config with multiple root layers."""
    manager = LayeredConfigManager()
    root_layer_1 = ConfigLayer("root_1", file_path=main_config_file)
    root_layer_2 = ConfigLayer("root_2", file_path=workspace_config_file)
    manager.register(root_layer_1)
    manager.register(root_layer_2)
    manager.load_all()
    config = manager.resolve()
    assert config == {
        **root_layer_1.get_data(),
        **root_layer_2.get_data(),
    }


def test_resolve_many(
    main_config_file: pathlib.Path,
    workspace_config_file: pathlib.Path,
) -> None:
    """Test resolving multiple independent branches and merging them in order."""
    manager = LayeredConfigManager()
    root_layer_1 = ConfigLayer("root_1", file_path=main_config_file)
    root_layer_2 = ConfigLayer("root_2", file_path=workspace_config_file)
    manager.register(root_layer_1)
    manager.register(root_layer_2)
    manager.load_all()
    config = manager.resolve_many("root_2", "root_1")
    assert config == {
        **root_layer_2.get_data(),
        **root_layer_1.get_data(),
    }
