"""
Gradle build tool skills.
Run Gradle tasks and parse output for success/failure signals.
"""
import subprocess
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class RunGradleTestInput(BaseModel):
    project_path: str = Field(description="Absolute path to the Gradle project root")
    test_class_fqcn: str = Field(
        description="Fully qualified test class name, e.g. 'com.example.service.OrderServiceTest'"
    )


@tool(args_schema=RunGradleTestInput)
def run_gradle_test(project_path: str, test_class_fqcn: str) -> dict:
    """
    Run Gradle tests for a specific test class using './gradlew test --tests'.
    Returns a dict with keys:
      - success (bool): True if build and all tests passed
      - output (str): combined stdout + stderr
      - error_summary (str): extracted relevant error lines if failed
    Times out after 180 seconds.
    """
    gradlew = Path(project_path) / "gradlew"
    if not gradlew.exists():
        return {
            "success": False,
            "output": "",
            "error_summary": f"ERROR: gradlew not found at {project_path}. Is this a Gradle project?",
        }

    cmd = [
        str(gradlew),
        "test",
        f"--tests={test_class_fqcn}",
        "--info",
        "--no-daemon",
        "--rerun-tasks",  # force re-run even if UP-TO-DATE
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=180,
        )
        combined = result.stdout + "\n" + result.stderr
        success = result.returncode == 0
        error_summary = _extract_errors(combined) if not success else ""

        return {
            "success": success,
            "output": combined,
            "error_summary": error_summary,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error_summary": "ERROR: Gradle test execution timed out after 180 seconds.",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error_summary": f"ERROR: Failed to invoke gradle: {e}",
        }


def _extract_errors(output: str) -> str:
    """
    Extract the most relevant error lines from Gradle output.
    Focuses on compilation errors, test failures, and stack traces.
    """
    lines = output.splitlines()
    collected = []

    for i, line in enumerate(lines):
        line_lower = line.lower()
        # Compilation errors
        if "error:" in line_lower or "cannot find symbol" in line_lower:
            collected.extend(lines[max(0, i - 1): i + 5])
        # Test failures
        elif "FAILED" in line or "AssertionError" in line or "NullPointerException" in line:
            collected.extend(lines[max(0, i - 2): i + 7])
        # Stack trace lines
        elif line.strip().startswith("at ") and ("Test" in line or "Exception" in line):
            collected.append(line)
        # Build failure block
        elif "BUILD FAILED" in line:
            collected.extend(lines[max(0, i - 2): i + 3])
        # Gradle error output block
        elif line.startswith("> ") and ("error" in line_lower or "exception" in line_lower):
            collected.extend(lines[max(0, i): i + 5])

    # Deduplicate preserving order
    seen: set = set()
    unique = []
    for line in collected:
        if line not in seen:
            seen.add(line)
            unique.append(line)

    return "\n".join(unique[:100])  # cap at 100 lines
