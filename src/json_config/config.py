import dataclasses
import logging
from typing import Any, Self

from .config_manager import LayeredConfigManager

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class ResolvedConfig:
    """Typed wrapper over a LayeredConfigManager.

    Subclass with typed fields and defaults. On first run, if the root
    layer has no file on disk yet, the defaults are written to it
    automatically.

    Example::

        @dataclasses.dataclass
        class AppConfig(ResolvedConfig):
            theme: str = "light"
            max_retries: int = 3
            database: dict = dataclasses.field(default_factory=dict)

        cfg = AppConfig.from_manager(manager)
        print(cfg.theme)
    """

    @classmethod
    def get_field_names(cls) -> set[str]:
        return {f.name for f in dataclasses.fields(cls)}

    @classmethod
    def _get_defaults(cls) -> dict[str, Any]:
        """Return a dict of field names to their default values."""
        defaults = {}
        for field in dataclasses.fields(cls):
            if field.default is not dataclasses.MISSING:
                defaults[field.name] = field.default
            elif field.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
                defaults[field.name] = field.default_factory()

        return defaults

    @classmethod
    def _seed_root_layer(cls, manager: LayeredConfigManager) -> None:
        """Seed the root layer with defaults and persist if its file is absent.

        The root layer is the one with no dependencies (i.e. no depends_on).
        If multiple roots exist, each one that has no file on disk is seeded.
        """
        defaults = cls._get_defaults()
        for name in manager.sorted_names():
            layer = manager[name]
            if layer.depends_on:
                continue  # not a root
            # Only set keys not already present in the layer.
            missing = {k: v for k, v in defaults.items() if k not in layer._data}
            if missing:
                layer.set(**missing)
            if layer.file_path and not layer.file_path.is_file():
                layer.save()
                LOGGER.info(f"First run: wrote defaults to '{layer.file_path}'")

    @classmethod
    def from_manager(
        cls,
        manager: LayeredConfigManager,
        up_to: str | None = None,
        *,
        ignore_unknown: bool = True,
    ) -> Self:
        cls._seed_root_layer(manager)
        data = manager.resolve(up_to)
        field_names = cls.get_field_names()
        if ignore_unknown:
            for key in list(data.keys()):
                if key not in field_names:
                    LOGGER.warning(f"Ignoring unknown config key: '{key}'")
                    data.pop(key)

        return cls(**data)
