"""
Agent 2: Generator
A single LLM call that produces the JUnit 5 + Mockito test class.
Handles both first-time generation and retry-with-error-fix attempts.
Writes the generated test file to disk.
"""
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import OPENAI_MODEL
from graph.state import AgentState
from prompts.generator_prompts import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_HUMAN_PROMPT,
    build_dependency_sources_block,
    build_error_section,
    build_existing_tests_section,
)
from skills.file_skills import write_file
from skills.java_skills import resolve_test_file_path
from utils.console import console


def run_generator(state: AgentState) -> dict:
    """
    LangGraph node: Generator agent.
    Produces test code via LLM and writes it to the correct test file location.
    """
    retry_count = state.get("retry_count", 0)
    attempt_label = f"Retry #{retry_count}" if retry_count > 0 else "First attempt"
    console.rule(f"[bold yellow]Agent 2: Generator ({attempt_label})[/bold yellow]")

    # Determine where to write the test file
    test_file_path = resolve_test_file_path.invoke({
        "source_file_path": state["source_file_path"],
        "project_path": state["project_path"],
    })
    test_class_name = state["target_class"] + "Test"

    console.print(f"  Test file: [blue]{test_file_path}[/blue]")

    # Check if a test file already exists — if so, preserve its content
    existing_test_code = ""
    test_path_obj = Path(test_file_path)
    if test_path_obj.exists():
        existing_test_code = test_path_obj.read_text(encoding="utf-8")
        console.print("  [dim]Existing test file found — will preserve existing tests[/dim]")

    # Build prompt sections
    dep_block = build_dependency_sources_block(state.get("dependency_sources", {}))
    error_section = build_error_section(
        last_error_output=state.get("last_error_output", ""),
        generated_test_code=state.get("generated_test_code", ""),
        retry_count=retry_count,
    )
    existing_section = build_existing_tests_section(existing_test_code)

    # Combine existing-tests section into analysis block so it lands near the top
    analysis_block = existing_section + state.get("analysis_text", "")

    human_content = GENERATOR_HUMAN_PROMPT.format(
        source_code=state["source_code"],
        dependency_sources_block=dep_block,
        analysis_text=analysis_block,
        error_section=error_section,
    )

    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.1)
    messages = [
        SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    test_code = response.content.strip()

    # Strip markdown code fences if model includes them despite instructions
    if test_code.startswith("```"):
        lines = test_code.splitlines()
        test_code = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    # Write test to disk
    write_result = write_file.invoke({"file_path": test_file_path, "content": test_code})
    console.print(f"  [green]{write_result}[/green]")

    return {
        "test_class_name": test_class_name,
        "test_file_path": test_file_path,
        "generated_test_code": test_code,
        "last_error_output": "",  # reset — fresh attempt
    }
