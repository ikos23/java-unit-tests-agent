"""
Java Unit Test Generator — CLI entry point.

Usage:
    python main.py --project /path/to/my-spring-app --class OrderService
    python main.py -p /path/to/my-spring-app -c OrderService
"""
import click
from rich.panel import Panel
from rich.text import Text

from graph.workflow import graph
from graph.state import AgentState
from utils.console import console


@click.command()
@click.option(
    "--project", "-p",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="Absolute or relative path to the Java/Spring Boot/Gradle project root.",
)
@click.option(
    "--class", "-c", "class_name",
    required=True,
    help="Simple name of the Java class to cover with tests (e.g. OrderService).",
)
def main(project: str, class_name: str):
    """
    Multi-agent tool that automatically generates JUnit 5 + Mockito tests
    for a Java class, runs them via Gradle, and fixes failures — up to 3 times.
    """
    console.print(Panel(
        Text.from_markup(
            f"[bold]Java Unit Test Generator[/bold]\n\n"
            f"  Project : [cyan]{project}[/cyan]\n"
            f"  Class   : [yellow]{class_name}[/yellow]\n\n"
            f"  Agents  : Analyzer → Generator → Validator (max 3 retries)\n"
            f"  LLM     : OpenAI GPT-4o via LangGraph"
        ),
        title="[bold blue] Multi-Agent Test System [/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))

    initial_state: AgentState = {
        "project_path": project,
        "target_class": class_name,
        "source_file_path": "",
        "source_code": "",
        "dependency_sources": {},
        "package_name": "",
        "analysis_text": "",
        "test_class_name": "",
        "test_file_path": "",
        "generated_test_code": "",
        "retry_count": 0,
        "last_error_output": "",
        "validation_passed": False,
        "final_message": "",
    }

    final_state = graph.invoke(initial_state)

    # Final summary panel
    passed = final_state.get("validation_passed", False)
    message = final_state.get("final_message", "Run complete.")
    test_file = final_state.get("test_file_path", "")

    console.print(Panel(
        Text.from_markup(message),
        title="[bold]Result[/bold]",
        border_style="green" if passed else "red",
        padding=(1, 2),
    ))

    if test_file:
        console.print(f"\nTest file: [link file://{test_file}]{test_file}[/link file://{test_file}]")


if __name__ == "__main__":
    main()
