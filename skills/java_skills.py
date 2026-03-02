"""
Java project structure navigation skills.
Skills for understanding Maven/Gradle layouts, package conventions, and import parsing.
"""
import re
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# Well-known external package prefixes to exclude from "internal" imports
EXTERNAL_PREFIXES = (
    "java.", "javax.", "jakarta.",
    "org.springframework.", "org.junit.", "org.mockito.",
    "com.fasterxml.", "org.apache.", "org.slf4j.",
    "org.hibernate.", "lombok.", "io.micrometer.", "io.swagger.",
    "reactor.", "kotlin.", "scala.", "groovy.",
    "com.google.", "org.mapstruct.", "org.aspectj.",
)


class ParsePackageInput(BaseModel):
    source_code: str = Field(description="Full Java source code content")


@tool(args_schema=ParsePackageInput)
def parse_java_package(source_code: str) -> str:
    """
    Extract the package declaration from Java source code.
    Returns the package name (e.g. 'com.example.service') or empty string if none found.
    """
    match = re.search(r"^\s*package\s+([\w.]+)\s*;", source_code, re.MULTILINE)
    return match.group(1) if match else ""


class ParseImportsInput(BaseModel):
    source_code: str = Field(description="Full Java source code content")
    project_base_package: str = Field(
        description="Base package prefix of this project, e.g. 'com.example'. "
                    "Only imports starting with this prefix are considered internal."
    )


@tool(args_schema=ParseImportsInput)
def parse_project_imports(source_code: str, project_base_package: str) -> list:
    """
    Parse import statements from Java source code and return only the simple class names
    that belong to this project (not external libraries, frameworks, or JDK classes).
    Returns a list of simple class names that are candidates for mocking in tests.
    Capped at 5 classes to avoid reading too many files.
    """
    import_pattern = re.findall(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", source_code, re.MULTILINE)
    internal_classes = []

    for fqcn in import_pattern:
        # Skip well-known external packages
        if any(fqcn.startswith(prefix) for prefix in EXTERNAL_PREFIXES):
            continue
        # Keep only imports that match the project's own base package
        if project_base_package and not fqcn.startswith(project_base_package):
            continue
        # Extract simple class name (last segment)
        simple_name = fqcn.rsplit(".", 1)[-1]
        # Java class names start with uppercase (skip lowercase = probably static field)
        if simple_name and simple_name[0].isupper():
            internal_classes.append(simple_name)

    # Deduplicate preserving order, cap at 5
    seen = set()
    unique = []
    for name in internal_classes:
        if name not in seen:
            seen.add(name)
            unique.append(name)

    return unique[:5]


class ResolveTestPathInput(BaseModel):
    source_file_path: str = Field(description="Absolute path to the source .java file")
    project_path: str = Field(description="Absolute path to the Gradle project root")


@tool(args_schema=ResolveTestPathInput)
def resolve_test_file_path(source_file_path: str, project_path: str) -> str:
    """
    Given a source file path, compute the corresponding test file path following
    Maven/Gradle standard layout: src/main/java/... -> src/test/java/...Test.java
    Returns the absolute path where the test file should be written.
    """
    source_path = Path(source_file_path)
    project_root = Path(project_path)

    try:
        rel = source_path.relative_to(project_root)
        parts = list(rel.parts)

        # Replace 'main' segment with 'test'
        new_parts = ["test" if p == "main" else p for p in parts]

        # Rename ClassName.java -> ClassNameTest.java
        new_parts[-1] = source_path.stem + "Test.java"

        return str(project_root / Path(*new_parts))
    except ValueError:
        # source file is not under project root — best effort
        return str(source_path.parent / (source_path.stem + "Test.java"))
