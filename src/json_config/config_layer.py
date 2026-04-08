import dataclasses
import json
import logging
import pathlib
from typing import Any

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

    # ------------------------------------------------------------------
    # Public data access
    # ------------------------------------------------------------------

    def set(self, **kwargs: Any) -> None:
        """Update this layer's values."""
        self._data.update(kwargs)

    def get_data(self) -> dict[str, Any]:
        """Return a shallow copy of this layer's raw data."""
        return dict(self._data)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

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

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w") as fh:
            json.dump(self._data, fh, indent=4)
        LOGGER.info(f"[{self.name}] Saved to {self.file_path}")
