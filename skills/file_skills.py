"""
File system skills for Java file operations.
These are LangChain @tool-decorated functions ("skills") that agents can call.
"""
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FindJavaFileInput(BaseModel):
    project_path: str = Field(description="Absolute path to the Java/Gradle project root")
    class_name: str = Field(description="Simple Java class name without .java extension")


@tool(args_schema=FindJavaFileInput)
def find_java_file(project_path: str, class_name: str) -> str:
    """
    Recursively search the project for a Java source file matching the class name.
    Searches src/main/java first, then the whole project.
    Returns the absolute file path, or an error message prefixed with ERROR: if not found.
    """
    search_root = Path(project_path)
    preferred_root = search_root / "src" / "main" / "java"
    search_dirs = [preferred_root, search_root] if preferred_root.exists() else [search_root]

    for search_dir in search_dirs:
        matches = list(search_dir.rglob(f"{class_name}.java"))
        if matches:
            # Prefer files not in test directories
            non_test = [m for m in matches if "test" not in str(m).lower()]
            return str(non_test[0] if non_test else matches[0])

    return f"ERROR: Could not find {class_name}.java in {project_path}"


class ReadFileInput(BaseModel):
    file_path: str = Field(description="Absolute path to the file to read")


@tool(args_schema=ReadFileInput)
def read_file(file_path: str) -> str:
    """
    Read and return the full contents of a file.
    Returns the file content as a string, or an error message prefixed with ERROR:.
    """
    lines_threshold = 1500
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        # Cap at lines_threshold to avoid flooding the LLM context with huge files
        # TODO - we can still have big files and in that case LLM might not get the full context. But for now I keep it to save some tokens xD
        lines = content.splitlines()
        if len(lines) > lines_threshold:
            truncated = "\n".join(lines[:lines_threshold])
            return truncated + f"\n\n... [TRUNCATED: file has {len(lines)} lines, showing first {lines_threshold}]"
        return content
    except FileNotFoundError:
        return f"ERROR: File not found: {file_path}"
    except PermissionError:
        return f"ERROR: Permission denied reading: {file_path}"
    except Exception as e:
        return f"ERROR: Could not read {file_path}: {e}"


class WriteFileInput(BaseModel):
    file_path: str = Field(description="Absolute path where the file should be written")
    content: str = Field(description="Complete file content to write")


@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file, creating parent directories as needed.
    Overwrites the file if it already exists.
    Returns a success or error message.
    """
    try:
        path = Path(file_path)
        already_exists = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        action = "Updated" if already_exists else "Created"
        return f"SUCCESS: {action} {file_path}"
    except Exception as e:
        return f"ERROR: Failed to write {file_path}: {e}"
