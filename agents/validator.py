"""
Agent 3: Validator
Runs Gradle tests, parses results, and decides whether to retry or finish.
No LLM involved — purely deterministic.
"""
from config import MAX_RETRIES
from graph.state import AgentState
from skills.gradle_skills import run_gradle_test
from utils.ascii_art import SUCCESS_ART, FAILURE_ART
from utils.console import console


def run_validator(state: AgentState) -> dict:
    """
    LangGraph node: Validator agent.
    Runs the generated test class via Gradle and returns updated state.
    The routing decision (retry vs end) is made by route_after_validation().
    """
    console.rule("[bold magenta]Agent 3: Validator[/bold magenta]")

    fqcn = f"{state['package_name']}.{state['test_class_name']}"
    console.print(f"  Running: [dim]./gradlew test --tests \"{fqcn}\"[/dim]")

    result = run_gradle_test.invoke({
        "project_path": state["project_path"],
        "test_class_fqcn": fqcn,
    })

    retry_count = state.get("retry_count", 0)

    if result["success"]:
        console.print(SUCCESS_ART, style="bold green")
        console.print(f"  [bold green]All tests passed![/bold green]")
        return {
            "validation_passed": True,
            "last_error_output": "",
            "final_message": (
                f"Tests for [bold]{state['test_class_name']}[/bold] passed successfully!\n"
                f"Test file: {state['test_file_path']}"
            ),
        }
    else:
        next_attempt = retry_count + 1
        if next_attempt >= MAX_RETRIES:
            console.print(FAILURE_ART, style="bold red")
            console.print(f"  [bold red]Max retries ({MAX_RETRIES}) reached. Tests still failing.[/bold red]")
        else:
            console.print(f"  [yellow]Tests failed. Will retry ({next_attempt}/{MAX_RETRIES - 1})...[/yellow]")

        console.print("\n[dim]Error summary:[/dim]")
        console.print(result["error_summary"] or result["output"][:500], style="dim red")

        return {
            "validation_passed": False,
            "last_error_output": result["error_summary"] or result["output"][:2000],
            "retry_count": 1,   # Annotated[int, operator.add] — this ADDS 1 to current count
            "final_message": (
                f"Tests failed after {next_attempt} attempt(s).\n"
                f"Last error:\n{(result['error_summary'] or '')[:300]}"
            ),
        }


def route_after_validation(state: AgentState) -> str:
    """
    Conditional edge function: determines the next node after validation.
    Returns the node name to route to.
    """
    if state.get("validation_passed", False):
        return "end"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "end"
    return "generator"  # retry loop
