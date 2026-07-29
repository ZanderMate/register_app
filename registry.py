import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# ---------------------------------------------------
# Default path for the registry JSON file
# ---------------------------------------------------
DEFAULT_REGISTRY_FILE = "registry_data.json"


@dataclass
class ScriptEntry:
    """Represents a registered script."""
    name: str
    path: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    enabled: bool = True

class ScriptRegistry:
    """
    Manages registration and lookup of Python scripts.
    Persists the registry to a JSON file so scripts
    survive server restarts.
    """

    def __init__(self, registry_file: str = DEFAULT_REGISTRY_FILE):
        self._scripts: Dict[str, ScriptEntry] = {}
        self._registry_file = registry_file
        self._load()

    # ---------------------------------------------------
    # Persistence - Save & Load
    # ---------------------------------------------------

    def _save(self) -> None:
        """Serialize the reistry to JSON and write to disk."""
        try:
            data = {
                name: asdict(entry)
                for name, entry in self._scripts.items()
            }
            with open(self._registry_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ScriptRegistry] WARNING: Failed to save registry: {e}")

    def _load(self) -> None:
        """Load the registry from JSON file if it exists."""
        if not os.path.isfile(self._registry_file):
            return

        try:
            with open(self._registry_file, "r") as f:
                data = json.load(f)

            loaded = 0
            skipped = 0

            for name, entry_data in data.items():
                path = entry_data.get("path", "")

                # Validate the script file still exists on disk
                if not os.path.isfile(path):
                    print(
                        f"[ScriptRegistry] Skipping '{name} - "
                        f"file no longer found at: {path}"
                    )
                    skipped += 1
                    continue

                self._scripts[name] = ScriptEntry(
                    name=entry_data.get("name", name),
                    path=path,
                    description=entry_data.get("description", ""),
                    tags=entry_data.get("tags", []),
                    enabled=entry_data.get("enabled", True)
                )
                loaded += 1

        except(json.JSONDecodeError, KeyError) as e:
            print(f"[ScriptRegistry] WARNING: Failed to load registry - {e}")

    # ---------------------------------------------------
    # Registry Management
    # ---------------------------------------------------

    def register(
            self,
            name: str,
            path: str,
            description: str = "",
            tags: Optional[List[str]] = None,
            enabled: bool = True
    ) -> None:
        """Register a script by name and file path."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Script not found at path: {path}")
        if name in self._scripts:
            raise ValueError(f"A script named '{name}' is already registerd.")

        self._scripts[name] = ScriptEntry(
            name=name,
            path=path,
            description=description,
            tags=tags or [],
            enabled=enabled
        )
        self._save()  # Persist after every registration

    def unregister(self, name: str) -> None:
        """Remove a script from the registry."""
        if name not in self._scripts:
            raise KeyError(f"No script name '{name}' found.")
        del self._scripts[name]
        self._save()

    def get(self, name: str) -> ScriptEntry:
        """Retrieve a script entry by name"""
        if name not in self._scripts:
            raise KeyError(f"No script named '{name}' found.")
        return self._scripts[name]

    def list_scripts(self, tag_filter: Optional[str] = None) -> List[ScriptEntry]:
        """Return all registered scripts, optionally filtered by tag."""
        scripts = list(self._scripts.values())
        if tag_filter:
            scripts = [s for s in scripts if tag_filter in s.tags]
        return scripts

    def enable(self, name: str) -> None:
        """Enable a script and persist the change."""
        self.get(name).enable = True
        self._save()

    def disable(self, name: str) -> None:
        """Disable a script and persist the change."""
        self.get(name).enabled = False
        self._save()

    def update(
            self,
            name: str,
            description: Optional[str] = None,
            tags: Optional[List[str]] = None,
            enabled: Optional[bool] = None
    ) -> ScriptEntry:
        """Update metadata for a registered script and persist."""
        entry = self.get(name)
        if description is not None:
            entry.description = description
        if tags is not None:
            entry.tags = tags
        if enabled is not None:
            entry.enabled = enabled
        self._save()
        return entry

    def clear_all(self) -> None:
        """Removal all registered scripts and clear the JSON file."""
        self._scripts.clear()
        self._save()