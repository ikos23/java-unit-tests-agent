GENERATOR_SYSTEM_PROMPT = """You are an expert Java test engineer. You write production-quality JUnit 5 + Mockito tests.

## Mandatory Rules
1. Class annotation: @ExtendWith(MockitoExtension.class) — NEVER use MockitoAnnotations.openMocks()
2. Use @Mock for all dependencies, @InjectMocks for the class under test
3. Do not use @BeforeEach
4. Test method naming: methodNameShouldDoSmthWhenY()
5. Use assertThrows() for exception testing — NEVER try/catch in tests
6. Use verify() for void methods to assert side effects
7. Use ArgumentCaptor when you need to inspect what was passed to a mock
8. Use JUnit Jupiter Assertions.*
9. No wildcard imports except for Mockito static imports
10. The test class MUST have the EXACT same package declaration as the source class
11. Output ONLY the raw Java source code — no markdown, no explanation, no code fences

## Standard Imports to Include
```java
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
```

Here we have an example of how to wirte a unit test.

```java
// the code of the class we want to test
class UserService {
    private UserRepository userRepository;    

    public String getUserDisplayName(User user) {
        return userRepository.findDisplayNameById(user.getId());
    }
}

// the test
class UserServiceTest {
    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @Test
    void getUserDisplayNameShouldReturnDisplayName() {
        // Given
        User user = new User(1L);
        when(userRepository.findDisplayNameById(1L)).thenReturn("John Doe");

        // When
        String displayName = userService.getUserDisplayName(user);

        // Then
        assertEquals("John Doe", displayName);
        verify(userRepository).findDisplayNameById(1L);
    }
}
```

Remember, we always test only public methods. When we create a test for some method, we check what
dependencies it uses, and we mock those dependencies. 

To be able to accurately mock dependencies, you need to check the actual return types of the methods 
in the source code of the dependencies if available.

Then we write our expectations like "when(someDependency.someMethod(any())).thenReturn(someValue)" 
based on the actual return types and behavior of the dependencies.

If we work with void method we can use doNothing() or doThrow() for stubbing, 
and then verify() to check if the method was called with expected arguments.

Then we call the actual method and we run assertions on the result and verify interactions with mocks.

Only include imports that are actually used in the test class.
"""

GENERATOR_HUMAN_PROMPT = """Generate a complete JUnit 5 + Mockito test class.

## Source Class to Test
```java
{source_code}
```

## Dependency Source Files (for accurate mock setup and correct return types)
{dependency_sources_block}

## Analysis and Test Plan
{analysis_text}

{error_section}

Output only the raw Java test class starting with the package declaration.
"""

GENERATOR_EXISTING_TESTS_SECTION = """## Existing Test File (PRESERVE ALL EXISTING TESTS)
The following test file already exists. You MUST keep all existing test methods.
Only add new test methods — do NOT remove or modify existing ones.

```java
{existing_test_code}
```

"""

GENERATOR_ERROR_SECTION = """## IMPORTANT: Fix These Errors from Previous Attempt
The previous test class you generated failed to compile or had test failures.
Gradle error output:

```
{last_error_output}
```

Your previous generated code that failed:
```java
{generated_test_code}
```

Carefully analyze every error and fix ALL of them. Common causes:
- Wrong import paths (check dependency sources above for correct package names)
- Mocking final classes or methods (use @MockitoSettings(strictness = LENIENT) or avoid)
- Wrong constructor arguments for @InjectMocks
- Incorrect mock return types (check the actual return type in the source)
- Calling Mockito setup (when/doReturn) outside of @Test or @BeforeEach context
- Missing required stub for a method that is called but not stubbed
"""


def build_dependency_sources_block(dependency_sources: dict) -> str:
    """Format the dependency_sources dict into a readable prompt block."""
    if not dependency_sources:
        return "_No internal dependencies found or needed._"
    blocks = []
    for class_name, source in dependency_sources.items():
        blocks.append(f"### {class_name}.java\n```java\n{source}\n```")
    return "\n\n".join(blocks)


def build_error_section(last_error_output: str, generated_test_code: str, retry_count: int) -> str:
    """Build the error context section for retry attempts. Empty string on first attempt."""
    if retry_count == 0 or not last_error_output:
        return ""
    return GENERATOR_ERROR_SECTION.format(
        last_error_output=last_error_output,
        generated_test_code=generated_test_code,
    )


def build_existing_tests_section(existing_code: str) -> str:
    """Build the 'preserve existing tests' section. Empty string if no existing tests."""
    if not existing_code.strip():
        return ""
    return GENERATOR_EXISTING_TESTS_SECTION.format(existing_test_code=existing_code)
