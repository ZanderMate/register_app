import subprocess
import sys
import time
import os
import glob
from dataclasses import dataclass, field
from typing import Optional, List
from registry import ScriptEntry


@dataclass
class ExecutionResult:
    """Holds the outcome of a script execution."""
    script_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    output_files: List[str] = field(default_factory=list)


class ExecutionEngine:
    """Handles running script and capturing their output."""

    def __init__(self, timeout: int = 60, output_dir: str = "outputs"):
        self.timeout = timeout
        self.output_dir = output_dir

    def _scan_output_files(self, script_name: str, scan_dir: str) -> List[str]:
        """
        Step 2 - Scan for output files.
        Looks in the output_dir for any files created or modified
        after the scrpt ran. Returns a list of file paths.
        """
        found_files = []

        if not os.path.isdir(scan_dir):
            return found_files
        
        # Match common output file types
        patterns = ["*.csv", "*.xlsx", "*.json", "*.txt", "*.pdf", "*.png", "*.jpg"]

        for pattern in patterns:
            matches = glob.glob(os.path.join(scan_dir, "**", pattern), recursive=True)
            found_files.extend(matches)

        return (os.path.abspath(f) for f in found_files)
    
    def run(self, entry: ScriptEntry, args: Optional[list] = None) -> ExectuionResult:
        """
        Execute a registered script.

        Args:
            entry: The ScriptEntry to execute.
            args: Optional list of arguments to pass to the script.

            Returns:
                An ExecutionResult with output, errors, timeing and output files.
        """
        if not entry.enabled:
            return ExecutionResult(
                script_name=entry.name,
                success=False,
                error_message=f"Script '{entry.name}' is disabled."
            )
        
        command = [sys.executable, entry.path] + (args or [])
        start_time = time.time()

        # --- Step 1: Snapshot output dir BEFORE running ----------------
        os.makedirs(self.output_dir, exist_ok=True)
        files_before = set(
            os.path.abspath(f)
            for f in glob.glob(os.path.join(self.output_dir, "**", "*"), recursive=True)
            if os.path.isfile(f)
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            duration = time.time() - start_time
        
            # --- Step 2: Scan for NEW output files AFTER running -------
            files_after = set(
                os.path.abspath(f)
                for f in glob.glob(os.path.join(self.output_dir, "**", "*"), recursive=True)
                if os.path.isfile(f)
            )
            new_output_files = sorted(files_after - files_before)

            return ExecutionResult(
                script_name=entry.name,
                success=(result.returncode == 0),
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
                duration_seconds=round(duration, 3),
                output_files=new_output_files
            )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                script_name=entry.name  ,
                success=False,
                error_message=f"Script timed out after {self.timeout}s.",
                duration_seconds=round(time.time() - start_time, 3)
            )
        
        except Exception as e:
            return ExecutionResult(
                script_name=entry.name,
                success=False,
                error_message=str(e),
                duration_seconds=round(time.time() - start_time, 3)
            )