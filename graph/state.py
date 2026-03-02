import operator
from typing import Annotated
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Input
    project_path: str
    target_class: str

    # Analyzer outputs
    source_file_path: str
    source_code: str
    dependency_sources: dict        # {ClassName: source_code}
    package_name: str
    analysis_text: str

    # Generator outputs
    test_class_name: str
    test_file_path: str
    generated_test_code: str

    # Validator + retry loop
    # Annotated[int, operator.add] means: when the node returns {"retry_count": 1},
    # LangGraph ADDS 1 to the existing value instead of overwriting it.
    retry_count: Annotated[int, operator.add]
    last_error_output: str
    validation_passed: bool

    # Terminal
    final_message: str
