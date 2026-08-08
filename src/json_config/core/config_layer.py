import dataclasses
import json
import logging
import pathlib
from collections.abc import Sequence
from typing import Any

from ..utils import layer_helpers

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class ConfigLayer:
    """A single named layer of configuration.

    Attributes:
        name:       Unique identifier for this layer.
        depends_on: Names of layers this layer overrides (must be registered
                    in the same manager before resolving).
        file_path:  Optional JSON file to persist / load this layer.
        _data:      Raw field-value mapping for this layer (partial is fine).
    """

    name: str
    depends_on: list[str] = dataclasses.field(default_factory=list)
    file_path: pathlib.Path | None = None
    _data: dict[str, Any] = dataclasses.field(default_factory=dict, repr=False)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"

    def set(self, **kwargs: Any) -> None:
        """Update this layer's values."""
        self._data.update(kwargs)

    def unset(self, *keys: str) -> None:
        """Remove *keys* from this layer's own data, if present.

        Used to drop overrides that have become redundant (i.e. equal to
        what would already be inherited from this layer's dependencies),
        keeping the layer limited to genuine overrides.

        Args:
            *keys: str
                The keys to remove from this layer's data.
        """
        for key in keys:
            self._data.pop(key, None)

    def unset_path(self, path: Sequence[str]) -> None:
        """Remove a (possibly nested) value from this layer's own data.

        Unlike `unset`, this can target a single leaf value nested
        within a category override (e.g. ``("category_a", "field_one")``)
        without discarding sibling overrides in that same category. Any
        parent container that becomes empty as a result is removed too.

        Args:
            path: Sequence of keys addressing the value to remove.
        """
        layer_helpers.pop_nested(self._data, path)

    def replace_data(self, data: dict[str, Any]) -> None:
        """Fully replace this layer's own data with *data*.

        Unlike `set`, this does not merge with the existing data --
        any previously-stored keys not present in *data* are dropped. Used
        when writing a fully pruned set of overrides back to the layer.

        Args:
            data: The new raw field-value mapping for this layer.
        """
        self._data = dict(data)

    def get_data(self) -> dict[str, Any]:
        """Return a shallow copy of this layer's raw data."""
        return dict(self._data)

    def load(self) -> None:
        """Load values from *file_path* (if it exists)."""
        if self.file_path is None:
            return

        if not self.file_path.is_file():
            LOGGER.warning(
                f"[{self.name}] No file found at {self.file_path}, skipping load."
            )
            return
        text = self.file_path.read_text().strip()
        if not text:
            LOGGER.warning(
                f"[{self.name}] Empty file at {self.file_path}, skipping load."
            )
            return
        raw = json.loads(self.file_path.read_text())

        if not isinstance(raw, dict):
            raise ValueError(f"[{self.name}] Expected a JSON object in {self.file_path}")
        self._data = raw
        LOGGER.info(f"[{self.name}] Loaded from {self.file_path}")

    def save(self) -> None:
        """Persist this layer's own values to *file_path*."""
        if self.file_path is None:
            raise RuntimeError(f"Layer '{self.name}' has no file_path set.")

        # If layer has no data and the file does not exist, skip saving.
        if not self.get_data() and not self.file_path.is_file():
            LOGGER.debug(f"[{self.name}] No data to save, skipping.")
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w") as fh:
            json.dump(self._data, fh, indent=4)
        LOGGER.info(f"[{self.name}] Saved to {self.file_path}")
