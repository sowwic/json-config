import functools
import logging
import pathlib
from typing import Any

from ..helpers import deep_merge_dicts, topological_sort_layers
from .config_layer import ConfigLayer

LOGGER = logging.getLogger(__name__)


class _ManagerMeta(type):
    """Singleton metaclass for LayeredConfigManager."""

    _instance: LayeredConfigManager | None = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance

    def clear_instance(cls) -> None:
        cls._instance = None


class LayeredConfigManager(metaclass=_ManagerMeta):
    """Central manager that owns and resolves all config layers.

    Usage::

        manager = LayeredConfigManager()

        # Register layers (order of registration does NOT matter;
        # depends_on drives the merge order).
        manager.register(ConfigLayer("main",  file_path=Path("config/main.json")))
        manager.register(ConfigLayer("user",  depends_on=["main"],
                                              file_path=Path("config/user.json")))
        manager.register(ConfigLayer("local", depends_on=["user"],
                                              file_path=Path("config/local.json")))

        # Load all layers from disk.
        manager.load_all()

        # Get the fully-merged view.
        cfg = manager.resolve()          # -> dict[str, Any]
        cfg = manager.resolve("user")    # -> only main + user merged

        # Modify a layer at runtime.
        manager["user"].set(theme="dark")
        manager.save("user")
    """

    def __init__(self) -> None:
        self._layers: dict[str, ConfigLayer] = {}

    def register(self, layer: ConfigLayer) -> None:
        """Add a layer to the manager."""
        if layer.name in self._layers:
            raise ValueError(f"A layer named '{layer.name}' is already registered.")
        self._layers[layer.name] = layer
        LOGGER.debug(f"Registered layer '{layer.name}'")

    def register_from_paths_tree(
        self,
        tree: dict,
    ) -> None:
        """Build and register config layers from a nested directory path tree.

        The tree structure encodes parent-child dependencies directly.
        Each key is a directory path string; its value is either a nested
        dict of children, or an empty dict / set leaf.

        Args:
            tree:            Nested mapping of directory path strings.
            config_filename: JSON filename looked for inside each directory.

        Example::

            manager.register_from_paths({
                "configs/root.json": {
                    "configs/root/child.json": {
                        "configs/root/child/grandchild.json": {}
                    },
                    "configs/root/other": {}
                }
            })
            # Registers:
            #   root        (no parent)
            #   child       (depends_on=["root"])
            #   grandchild  (depends_on=["child"])
            #   other       (depends_on=["root"])
        """

        def _walk(subtree: dict | set, parent_name: str | None) -> None:
            """Recursively walk the tree and register layers.

            Args:
                subtree: The current subtree to walk.
                parent_name: The name of the parent layer, or None for root layers.
            """
            items = subtree if isinstance(subtree, dict) else {p: {} for p in subtree}
            for path_str, children in items.items():
                path = pathlib.Path(path_str)
                name = path.stem
                depends_on = [parent_name] if parent_name else []
                layer = ConfigLayer(
                    name=name,
                    depends_on=depends_on,
                    file_path=path,
                )
                self.register(layer)
                LOGGER.debug(f"Registered layer '{name}' (depends_on={depends_on})")
                if children:
                    _walk(children, name)

        _walk(tree, parent_name=None)

    def unregister(self, name: str) -> None:
        """Remove a layer (and any references to it are the caller's problem).

        Args:
            name: Name of the layer to remove.
        """
        self._layers.pop(name, None)

    def __getitem__(self, name: str) -> ConfigLayer:
        """Return a layer by name."""
        return self._layers[name]

    def seed_root_layers(self, defaults: dict[str, Any]) -> None:
        """Seed root layers with defaults and persist if file is absent.

        Args:
            defaults: Dictionary of field names to default values
            to seed into root layers.
        """
        for name in self.sorted_names():
            layer = self[name]
            if layer.depends_on:
                continue

            missing = {k: v for k, v in defaults.items() if k not in layer._data}
            if missing:
                layer.set(**missing)
            if layer.file_path and not layer.file_path.is_file():
                layer.save()
                LOGGER.info(f"Initialized default config: '{layer.file_path}'")

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    @property
    def root_layers(self) -> list[str]:
        """Return the root layers as a dict.

        Returns:
            list[str]: The root layer names.
        """
        return [k for k, v in self._layers.items() if not v.depends_on]

    def sorted_names(self, up_to: str | None = None) -> list[str]:
        """Return layer names in topological order.

        Args:
            up_to: If given, return only the sub-graph needed to resolve
                   that layer (the layer itself + all its transitive deps).
        """
        if up_to is not None:
            subset = self._reachable_subgraph(up_to)
            return topological_sort_layers(subset)
        return topological_sort_layers(self._layers)

    def _reachable_subgraph(self, name: str) -> dict[str, ConfigLayer]:
        """Return the layers reachable from *name* (including itself)."""
        seen: set[str] = set()
        stack = [name]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._layers[current].depends_on)
        return {k: self._layers[k] for k in seen}

    # ------------------------------------------------------------------
    # Resolution (deep merge)
    # ------------------------------------------------------------------

    def resolve(self, up_to: str | None = None) -> dict[str, Any]:
        """Return the fully-merged config dict.

        Args:
            up_to: Resolve only up to (and including) this layer.
                   Useful to preview what a specific layer contributes.
        """
        return functools.reduce(
            deep_merge_dicts,
            (self._layers[name].get_data() for name in self.sorted_names(up_to)),
            {},
        )

    def resolve_many(self, *names: str) -> dict[str, Any]:
        """Resolve multiple independent branches and merge them in order.

        Each name is resolved against its own subgraph (i.e. including its
        transitive dependencies), then the results are deep-merged left to
        right — so later names take precedence over earlier ones on conflicts.

        Args:
            names: Layer names to resolve, in ascending priority order.

        Example::

            # default → user1
            # default → user2
            cfg = manager.resolve_many("user1", "user2")
            # user2 wins over user1 on conflicting keys;
            # both override default.
        """
        return functools.reduce(
            deep_merge_dicts,
            (self.resolve(name) for name in names),
            {},
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        """Load every registered layer from its file (if any)."""
        for name in self.sorted_names():
            self._layers[name].load()

    def save(self, name: str) -> None:
        """Persist a single layer by name."""
        self._layers[name].save()

    def save_all(self) -> None:
        """Persist every layer that has a file_path."""
        for layer in self._layers.values():
            if layer.file_path is not None:
                layer.save()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def clear(cls) -> None:
        """Destroy the singleton (useful in tests)."""
        cls.clear_instance()  # type: ignore[attr-defined]

    def __repr__(self) -> str:
        order = self.sorted_names()
        return f"LayeredConfigManager(layers={order})"
