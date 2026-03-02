# Java Unit Tests Agent

A multi-agent CLI tool that automatically generates JUnit 5 + Mockito tests for Java/Spring Boot/Gradle projects using LangGraph and OpenAI GPT-4o.

## How It Works

```
START
  └─> [Agent 1: Analyzer]   — reads source code + dependency classes, plans test scenarios
        └─> [Agent 2: Generator] — generates the JUnit 5 + Mockito test class
              └─> [Agent 3: Validator] — runs ./gradlew test
                    ├─ PASS  →  prints success banner, done
                    └─ FAIL  →  sends errors back to Generator, retries (max 3×)
```

### Agent 1: Analyzer (ReAct loop with skills)
- Finds the Java source file in your project
- Parses imports to identify internal dependencies (your own classes, not Spring/JDK)
- Reads those dependency source files for accurate mock setup
- Asks GPT-4o to describe the class and list every scenario to test
- This pre-analysis step significantly improves test quality

### Agent 2: Generator
- Receives the full analysis + source + dependency sources
- Generates a complete JUnit 5 + Mockito test class
- On retry: also receives the Gradle error output to fix specific failures
- Preserves existing tests if a test file already exists

### Agent 3: Validator
- Runs `./gradlew test --tests "com.example.YourClassTest"`
- On success: prints a celebratory ASCII banner
- On failure: collects errors and sends back to Generator (up to 3 retries)
- After 3 failures: prints a sad banner and tells you to check manually

## About "Skills"

The `skills/` directory contains LangChain `@tool`-decorated functions — these are the **skills** agents can use:

- `skills/file_skills.py` — `find_java_file`, `read_file`, `write_file`
- `skills/java_skills.py` — `parse_java_package`, `parse_project_imports`, `resolve_test_file_path`
- `skills/gradle_skills.py` — `run_gradle_test`

Skills are registered with the LLM via `llm.bind_tools(ANALYZER_SKILLS)`, which converts them to OpenAI function-calling schemas automatically. The Analyzer agent uses them in a ReAct loop. The Generator and Validator call them as plain Python functions (deterministic, no LLM needed).

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Usage

```bash
python main.py --project /path/to/your/spring-project --class OrderService
# or short form:
python main.py -p /path/to/your/spring-project -c OrderService
```

## Project Structure

```
java-unit-tests-agent/
├── main.py                    # CLI entry point (Click)
├── config.py                  # Settings loaded from .env
├── graph/
│   ├── state.py               # AgentState TypedDict — shared data contract
│   └── workflow.py            # LangGraph StateGraph definition
├── agents/
│   ├── analyzer.py            # Agent 1: ReAct loop
│   ├── generator.py           # Agent 2: LLM test generation
│   └── validator.py           # Agent 3: Gradle runner + retry routing
├── skills/                    # LangChain @tool functions (agent capabilities)
│   ├── file_skills.py
│   ├── java_skills.py
│   └── gradle_skills.py
├── prompts/
│   ├── analyzer_prompts.py
│   └── generator_prompts.py
└── utils/
    ├── ascii_art.py
    └── console.py
```

## Requirements

- Python 3.11+
- OpenAI API key
- Java project using Gradle (`gradlew` present in project root)
- `./gradlew` must be executable (`chmod +x gradlew` if needed)
