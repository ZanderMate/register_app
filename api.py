#FastAPI backend for the register app

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import os

from app import ScriptPlatform
from registry import ScriptEntry
from execution_engine import ExecutionResult

# ============================================
# App Initialization
#=============================================

app = FastAPI(
    title="Registry Application",
    description="API for registerying and executing automation scripts",
    version="1.0.0",
)

# CORS - adjust origins for your environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logger = logging.getLogger("ScriptPlatformAPI")
logging.basicConfig(level=logging.INFO)

# Platform instance
platform = ScriptPlatform(timeout=30, log_dir="logs")

# ============================================
# Pydantic Models
#=============================================

class RegisterScriptRequest(BaseModel):
    name: str
    path: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []
    enable: Optional[bool] = True

class RunScriptRequest(BaseModel):
    args: Optional[List[str]] = []

class ScriptEntryResponse(BaseModel):
    name: str
    path: str
    description: str
    tags: List[str]
    enabled: bool

class ExecutionResultResponse(BaseModel):
    script_name: str
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration_seconds: float
    error_message: Optional[str] = None
    output_files: List[str] = []

class RunAllResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[ExecutionResultResponse]

# ============================================
# Helper - Convert ExecutionResult to Response
#=============================================

def format_result(result: ExecutionResult) -> ExecutionResultResponse:
    """Convert an ExecutionResult dataclass to a Pydantic response model"""
    return ExecutionResultResponse(
        script_name=result.script_name,
        success=result.success,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        return_code=result.return_code or 0,
        duration_seconds=result.duration_seconds or 0.0,
        error_message=result.error_message,
        output_files=result.output_files or [],
    )

# ============================================
# Health Check
#=============================================

@app.get("/health", tags=["System"])
def health_check():
    """Confirm the API is running."""
    return {"status": "ok", "service": "Register App"}

# ============================================
# Script Registration Endpoints
#=============================================

@app.get("/scripts/register", response_model=ScriptEntryResponse, tags=["Registry"])
def register_script(payload: RegisterScriptRequest):
    """Register a new script with the platform."""
    try:
        platform.register_script(
            name=payload.name,
            path=payload.path,
            description=payload.description,
            tags=payload.tags
        )
        logger.info(f"Script registered via API: '{payload.name}'")
        entry = platform.registry.get(payload.name)
        return ScriptEntryResponse(
            name=entry.name,
            path=entry.path,
            description=entry.description,
            tags=entry.tags,
            enabled=entry.enabled
        )
    except FileNotFoundError as e:
        logger.error(f"Registration failed - file not found: {e}")
    except ValueError as e:
        logger.error(f"Registration failed - duplicate name: {e}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed - unexpected error: {e}")

@app.delete("/scripts/{name}", tags=["Registry"])
def unregister_script(name: str):
    """Remove a script from the registry."""
    try:
        platform.unregister_script(name)
        logger.info(f"Script unregistered via API: '{name}'")
        return {"message": f"Script '{name}' successfully unregistered."}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/script/{name}/enable", tags=["Registry"])
def enable_script(name: str):
    """Enable a registered script."""
    try:
        platform.registry.enable(name)
        logger.info(f"Script enable: '{name}'")
        return {"message": f"Script '{name}' enabled."}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@app.patch("/script/{name}/disable", tags=["Registry"])
def disable_script(name: str):
    """Disable a registered script without removing it."""
    try:
        platform.registry.disable(name)
        logger.info(f"Script disabled: '{name}'")
        return {"message": f"Script '{name}' disabled."}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    

# ============================================
# Script Listing Endpoints
#=============================================

@app.get("/scripts", response_model=List[ScriptEntryResponse], tags=["Registry"])
def list_scripts(tag: Optional[str] = Query(None, description="Filter by tag")):
    """Return all registered scripts, optionally filtered by tag."""
    try:
        scripts = platform.registry.list_scripts(tag_filter=tag)
        logger.info(f"Listed {len(scripts)} script(s) - tag filter: '{tag}'")
        return [
            ScriptEntryResponse(
                name=s.name,
                path=s.path,
                description=s.description,
                tags=s.tags,
                enabled=s.enabled
            )
            for s in scripts
        ]
    except Exception as e:
        logger.error(f"Failed to list scripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================
# ✅FIXED: /scripts/run-all Endpoint
#=============================================

@app.post("/script/run-all", response_model=RunAllResponse, tags=["Execution"])
def run_all_scripts(
    tag: Optional[str] = Query(None, description="Only run scripts matching this tag")
):
    """Run all registered and enable scripts.
    
    - Fetches scripts via platform,registry.list_scripts(tag_filter=tag)
    - Skips disable scripts
    - Runs each via platform.engine.run(entry=script)
    - Returns aggregated results with success/failure counts
    """
    results: List[ExecutionResultResponse] = []
    successful = 0
    failed = 0

    try:
        # Step 1 - Get all scripts (optionally filtered by tag)
        scripts: List[ScriptEntry] = platform.registry.list_scripts(tag_filter=tag)
        logger.info(
            f"run-all triggered - found {len(scripts)} script(s)"
            f"{f' with tag: {tag}' if tag else ''}"
        )

        if not scripts:
            logger.warning("run-all called but no matching scripts were found.")
            return RunAllResponse(total=0, successful=0, failed=0, results=[])
    
        # Step 2 - Iterate and run each script individually
        for script in scripts:

            # Skip disable scripts - log and continue
            if not script.enabled:
                logger.info(f"Skipping diable script: '{script.name}'")
                results.append(ExecutionResultResponse(
                    script_name=script.name,
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    duration_seconds=0.0,
                    error_message=f"Script '{script.name}' is disabled - skipped."
                ))
                failed += 1
                continue

            #Step 3 - Run the script using the execution engine
            logger.info(f"Running script: '{script.name}' at path: {script.path}")
            try:
                raw_result: ExecutionResult = platform.engine.run(entry=script)

                # Step 4 - Store result
                formatted = format_result(raw_result)
                results.append(formatted)

                # Track success/failure counts
                if raw_result.success:
                    successful += 1
                    logger.info(
                        f"[SUCCESS] '{script.name}' completed in "
                        f"{raw_result.duration_seconds}s"
                    )
                else:
                    failed += 1
                    logger.warning(
                        f"[FAILED] '{script.name}' - "
                        f"return code: {raw_result.return_code} | "
                        f"error: {raw_result.error_message or raw_result.stderr}"
                    )
                
                # Append to platform's internal results history
                platform._results.append(raw_result)

            except Exception as script_error:
                # isolate per-script errors so one failure doesn't stop the run
                logger.error(
                    f"Unexpected error running '{script.name}': {script_error}"
                )
                results.append(ExecutionResultResponse(
                    script_name=script.name,
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    duration_seconds=0.0,
                    error_message=f"Unexpected error: {str(script_error)}"
                ))
                failed += 1

        logger.info(
            f"run-all complete - "
            f"Total: {len(results)}"
            f"Successful: {successful}"
            f"Failed: {failed}"
        )

        # Step 5 - Return aggregated response
        return RunAllResponse(
            total=len(results),
            successful=successful,
            failed=failed,
            results=results
        )

    except Exception as e:
        logger.error(f"run-all endpoint failed unexpectedly: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"run-all failed: {str(e)}"
        )
    
# ============================================
# Single Script Execution
#=============================================

@app.post("/scripts/{name}/run", response_model=ExecutionResultResponse, tags=["Execution"])
def run_script(name: str, payload: RunScriptRequest = RunScriptRequest()):
    """Run a single registered script by name."""
    try:
        entry = platform.registry.get(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No script named '{name}' found.")
    
    logger.info(f"Single run triggered for: '{name}'")

    try:
        raw_result: ExecutionResult = platform.engine.run(
            entry=entry,
            args=payload.args or []
        )
        platform._result.append(raw_result)

        if raw_result.success:
            logger.info(f"[SUCCESS] '{name}' completed in {raw_result.duration_seconds}s")
        else:
            logger.info(f"[FAILED] '{name}' - {raw_result.error_message or raw_result.stderr}")
        
        return format_result(raw_result)
    
    except Exception as e:
        logger.error(f"Unexpected error running '{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# ============================================
# Results History
#=============================================

@app.get("/results", response_model=List[ExecutionResultResponse], tags=["Results"])
def get_results():
    """Return all stored execution results from this session."""
    return [format_result(r) for r in platform._results]

@app.delete("/results", tags=["Results"])
def clear_results():
    """Clear all stored exectuion results and remove all files from the outputs folder."""

    # -- Step 1 - Clear in-memory results list --------------------------
    platform._results.clear()
    logger.info("Execution results cleared via API")

    # -- Step 2 - Remove all files from the outputs directory -----------
    removed_files = []
    failed_files = []

    if os.path.isdir(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    removed_files.append(filename)
                    logger.info(f"Deleted output file: '{filename}'")
            except Exception as e:
                failed_files.append(filename)
                logger.error(f"Failed to delete '{filename}': {e}")
    else:
        logger.warning(f"Output directory '{OUTPUT_DIR}' not found - skipping file cleanup.")

    # -- Step 3 - Build response summary --------------------------------
    response = {
        "message": "Results cleared.",
        "files_removed": removed_files,
        "files_renived_count": len(removed_files)
    }

    if failed_files:
        response["warning"] = f"Could not delete {len(failed_files)} file(s): {failed_files}"
        logger.warning(f"Output cleanup partial - failed files: {failed_files}")

    return response


# ============================================
# Static Frontend
#=============================================

FRONT_DIR = "static"

if os.path.isdir(FRONT_DIR):
    # Mount static assets (CSS, JS, images, etc.)
    app.mount("/static", StaticFiles(directory=FRONT_DIR), name="static")

    @app.get("/", tags=["Frontend"], include_in_schema=False)
    def serve_frontend():
        """Serve the frontend index.html when the frontend directory exists."""
        index_path = os.path.join(FRONT_DIR, "index.html")
        if not os.path.isfile(index_path):
            raise HTTPException(
                status_code=404,
                detail="Frontend index.html not found."
            )
        return FileResponse(index_path)
    
else:
    @app.get("/", tags=["System"])
    def root():
        """API status - shown when no frontend directory is present."""
        return {
            "message": "Script Platform API is running",
            "version": "1.0.0",
            "docs": "/docs"
        }
    
# ============================================
# Outputs
#=============================================

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount outputs as static files
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# Explicit download endpoint
@app.get("/outputs/{filename}", tags=["Results"])
def download_output_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )