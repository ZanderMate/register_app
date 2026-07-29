from typing import List, Optional
from registry import ScriptRegistry
from execution_engine import ExecutionEngine, ExecutionResult

class ScriptPlatform:
    """
    Central platform for registering and running Python scripts
    """

    def __init__(self, timeout: int = 60, log_dir: str = "logs"):
        self.registry = ScriptRegistry()
        self.engine = ExecutionEngine(timeout=timeout)
        self.logger = setup_logger(log_dir=log_dir)
        self._results: List[ExecutionResult] = []
        self.logger.info("ScriptPlatform initialized")

    # ------------------------------------------------------------
    # Registry management
    # ------------------------------------------------------------

    def register_script(self, name: str, path: str, description: str = "", tags=None):
        """Register a script with the paltform."""
        try:
            self.registry.register(name, path, description, tags)
            self.logger.info(f"Registered script: '{name}' - {path}")
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"Registeration failed for '{name}': {e}")
            raise

    def unregister_script(self, name: str):
        """Remove a script from the platform."""
        self.registry.unregister(name)
        self.logger.info(f"Unregister script: '{name}'")

    def list_scripts(self, tag_filter: Optional[str] = None):
        """Print all registered scripts."""
        scripts = self.registry.list_scripts(tag_filter=tag_filter)
        if not scripts:
            print("No scripts registered.")
            return
        
        print(f"\n{'Name':<20} {'Enabled':<10} {'Tags':<20} Description")
        print("-" * 70)
        for s in scripts:
            print(
                f"{s.name:<20} "
                f"{'✅' if s.enabled else '❌':<10} "
                f"{', '.join(s.tags) or 'none':<20} "
            )
    def clear_results(self) -> None:
        """Clear all stored execution results."""
        self._results.clear()
        self.logger.info("Results cleared.")

    # ------------------------------------------------------------
    # Execution