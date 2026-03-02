"""
Agent 1: Analyzer
A manual ReAct loop that reads the Java project, identifies dependencies,
and calls the LLM to produce a detailed test plan.

Why manual ReAct instead of create_react_agent?
  The prebuilt agent returns only {"messages": [...]} - we cannot extract structured
  fields like dependency_sources or package_name without parsing message history.
  A manual loop lets the node return a clean dict that directly populates AgentState.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from config import OPENAI_MODEL, MAX_ANALYZER_TOOL_LOOPS
from graph.state import AgentState
from prompts.analyzer_prompts import ANALYZER_SYSTEM_PROMPT, ANALYZER_HUMAN_PROMPT
from skills.file_skills import find_java_file, read_file
from skills.java_skills import parse_java_package, parse_project_imports
from utils.console import console

# Skills available to the Analyzer's ReAct loop
ANALYZER_SKILLS = [
    find_java_file,
    read_file,
    parse_java_package,
    parse_project_imports,
]

_skills_by_name = {s.name: s for s in ANALYZER_SKILLS}


def run_analyzer(state: AgentState) -> dict:
    """
    LangGraph node: Analyzer agent.
    Reads the target class + dependencies, then produces analysis_text.
    """
    console.rule("[bold cyan]Agent 1: Analyzer[/bold cyan]")

    project_path = state["project_path"]
    target_class = state["target_class"]

    # Read source file upfront (before the LLM loop)
    source_path_result = find_java_file.invoke({
        "project_path": project_path,
        "class_name": target_class,
    })

    if source_path_result.startswith("ERROR"):
        console.print(f"[red]{source_path_result}[/red]")
        return {
            "source_file_path": "",
            "source_code": "",
            "package_name": "",
            "dependency_sources": {},
            "analysis_text": f"FAILED: {source_path_result}",
        }

    source_code = read_file.invoke({"file_path": source_path_result})
    package_name = parse_java_package.invoke({"source_code": source_code})

    # Derive project base package from first two segments (e.g. "com.example")
    segments = package_name.split(".")
    base_package = ".".join(segments[:2]) if len(segments) >= 2 else package_name

    console.print(f"  Source : [green]{source_path_result}[/green]")
    console.print(f"  Package: [blue]{package_name}[/blue]")
    console.print(f"  Base   : [blue]{base_package}[/blue]")

    # Build initial messages for the ReAct loop
    human_content = ANALYZER_HUMAN_PROMPT.format(
        project_path=project_path,
        target_class=target_class,
        base_package=base_package,
        source_code=source_code,
    )
    messages = [
        SystemMessage(content=ANALYZER_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    llm_with_skills = llm.bind_tools(ANALYZER_SKILLS)

    # ReAct loop
    dependency_sources: dict = {}
    loop_count = 0
    last_response = None

    while loop_count < MAX_ANALYZER_TOOL_LOOPS:
        loop_count += 1
        response = llm_with_skills.invoke(messages)
        messages.append(response)
        last_response = response

        if not response.tool_calls:
            # LLM has finished using tools — final answer ready
            break

        # Execute each skill the LLM requested
        for tool_call in response.tool_calls:
            skill_name = tool_call["name"]
            skill_args = tool_call["args"]
            console.print(f"  [dim]-> {skill_name}({skill_args})[/dim]")

            skill_fn = _skills_by_name.get(skill_name)
            if skill_fn is None:
                skill_result = f"ERROR: Unknown skill '{skill_name}'"
            else:
                skill_result = skill_fn.invoke(skill_args)

            # Track dependency source files the LLM reads
            if skill_name == "read_file" and not str(skill_result).startswith("ERROR"):
                file_path_arg = skill_args.get("file_path", "")
                dep_class_name = file_path_arg.rsplit("/", 1)[-1].replace(".java", "")
                if dep_class_name and dep_class_name != target_class:
                    dependency_sources[dep_class_name] = skill_result
                    console.print(f"  [green]Collected dependency: {dep_class_name}[/green]")

            # Serialize result for the ToolMessage
            if isinstance(skill_result, (dict, list)):
                result_content = json.dumps(skill_result)
            else:
                result_content = str(skill_result)

            messages.append(ToolMessage(
                content=result_content,
                tool_call_id=tool_call["id"],
                name=skill_name,
            ))

    analysis_text = (
        last_response.content
        if last_response and isinstance(last_response.content, str)
        else "Analysis unavailable."
    )

    console.print(
        f"  [green]Analysis done. "
        f"{len(dependency_sources)} dep(s) collected. "
        f"{loop_count} loop(s).[/green]"
    )

    return {
        "source_file_path": source_path_result,
        "source_code": source_code,
        "package_name": package_name,
        "dependency_sources": dependency_sources,
        "analysis_text": analysis_text,
    }
