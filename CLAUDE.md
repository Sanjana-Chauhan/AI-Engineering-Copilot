# Engineering Guidelines

## 1. Understand Before Changing

- Always inspect the existing codebase before making changes.
- Understand the current architecture, data flow, dependencies, and responsibilities of relevant components.
- Search for existing functionality before creating anything new.
- Do not assume that a required function, utility, service, component, or configuration does not already exist.

## 2. Reuse Existing Functionality

- Prefer reusing existing functions, classes, services, utilities, components, and modules.
- If existing functionality is similar but needs a small variation, extend or generalize it instead of creating a completely new implementation.
- Avoid duplicate logic.
- Follow the DRY principle.
- Create generic, reusable functions when designing new functionality.
- Keep reusable business logic separate from application-specific code.

## 3. Fix Root Causes

- Always identify and fix the root cause of a problem rather than treating only the symptom.
- Do not keep adding patches or workarounds on top of problematic code.
- If the current design is causing repeated problems, improve the design instead of adding another conditional or workaround.
- Avoid accumulating technical debt through temporary fixes unless explicitly requested.

## 4. Keep Code Modular

- Follow separation of concerns.
- Each module, class, function, and component should have a clear responsibility.
- Keep functions focused and reasonably small.
- Avoid putting unrelated responsibilities into the same function or module.
- Design components so they can be independently tested, reused, and extended.
- Prefer composition and reusable abstractions over duplicated implementations.

## 5. Design for Extension

- Write code that can accommodate reasonable future changes.
- When functionality may have multiple variations, design the abstraction so additional variations can be added without rewriting existing logic.
- Prefer extending existing functionality over creating parallel implementations.
- Do not over-engineer simple requirements. Introduce abstractions when they provide real reuse or maintainability.

## 6. Avoid Hardcoded Values

- Do not hardcode values that may change between environments, deployments, users, or configurations.
- Keep configurable values in appropriate configuration files, environment variables, constants, or configuration objects.
- Separate configuration from business logic.
- Do not hardcode URLs, credentials, API keys, ports, file paths, limits, feature flags, or environment-specific values.
- Never commit secrets or credentials into source code.

## 7. Configuration Management

- Keep configuration separate from application logic.
- Use environment-specific configuration where appropriate.
- Provide sensible defaults only when they are genuinely appropriate.
- Avoid scattering configuration values throughout the codebase.
- Centralize related configuration so it can be changed without modifying business logic.

## 8. Error Handling

- Handle errors at the appropriate layer.
- Do not silently ignore errors.
- Provide meaningful error messages.
- Do not use broad exception handling unless there is a clear reason.
- Do not hide errors simply to make the application appear functional.
- Validate inputs at appropriate boundaries.

## 9. Naming and Readability

- Use clear and descriptive names.
- Names should communicate intent rather than implementation details.
- Avoid unnecessary abbreviations.
- Follow the naming conventions already established by the project.
- Prefer readable code over clever or unnecessarily complex code.

## 10. Maintainability

- Write code that another developer can understand and modify easily.
- Avoid unnecessary complexity.
- Avoid deeply nested conditions when simpler structures are possible.
- Avoid duplicated constants, logic, and validation.
- Keep related functionality together and unrelated functionality separated.
- Preserve consistency with the existing architecture.

## 11. Changes Should Be Focused

- Make the smallest clean change that properly solves the problem.
- Do not modify unrelated files or functionality.
- Do not rewrite working code without a clear reason.
- Before introducing a new abstraction, determine whether an existing abstraction can be extended.
- Avoid unnecessary refactoring while implementing unrelated features.

## 12. Dependency Awareness

- Before adding a dependency, check whether the project already has something that solves the problem.
- Avoid introducing libraries for simple functionality that can be implemented cleanly with existing tools.
- When adding a dependency, consider its maintenance, security, compatibility, and long-term impact.

## 13. Testing

- Consider how every change can be tested.
- Do not modify existing behavior without considering its impact on existing tests.
- Add or update tests when introducing meaningful functionality.
- Prefer testing behavior and outcomes rather than implementation details.
- When fixing a bug, consider adding a regression test when appropriate.

## 14. Security

- Never expose secrets, credentials, tokens, or sensitive configuration.
- Validate and sanitize external input where appropriate.
- Follow least-privilege principles.
- Consider authentication, authorization, data exposure, injection risks, and unsafe dependencies when relevant.
- Do not introduce insecure shortcuts just to make functionality work.

## 15. Before Creating New Code

Before creating a new function, class, component, service, utility, or module:

1. Search for existing related functionality.
2. Determine whether it can be reused.
3. Determine whether it can be generalized or extended.
4. Check whether the new code would duplicate existing behavior.
5. Only create new functionality if existing code cannot reasonably support the requirement.

## 16. Before Finalizing Changes

Verify that:

- Existing functionality has not unnecessarily been duplicated.
- The root cause has been addressed.
- No unnecessary patches or workarounds were introduced.
- Configuration is separated from business logic.
- No values that should be configurable are hardcoded.
- The implementation follows the existing architecture.
- Functions and modules have clear responsibilities.
- The change is reusable where appropriate.
- Error handling is appropriate.
- Existing tests and functionality are not unnecessarily broken.

## 17. Development Approach

When implementing a feature or fixing a problem, follow this general process:

Understand
    ↓
Inspect existing code
    ↓
Identify reusable functionality
    ↓
Understand dependencies and impact
    ↓
Design the cleanest solution
    ↓
Extend existing functionality where appropriate
    ↓
Implement the smallest correct change
    ↓
Test
    ↓
Review for duplication, hardcoding, patches, and architectural issues

## Core Principle

Do not optimize for "making the code work" alone.

Optimize for:

Correctness
+ Reusability
+ Maintainability
+ Modularity
+ Extensibility
+ Testability
+ Security
+ Simplicity

The goal is to produce production-quality code, not just a working patch.