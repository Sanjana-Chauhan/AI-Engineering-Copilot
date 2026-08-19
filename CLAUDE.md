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



I am building this project to **learn while building**, so I want the implementation process to teach me the concepts and real-world engineering decisions involved.

### Quick checklist — apply this to every significant task

For every non-trivial change, cover all of these, in this order, before/while implementing:

1. **Limitation** — what's the actual constraint we hit, and why does it exist (our code, the framework, the architecture, or the underlying tech)?
2. **How to overcome it** — the real options, and why one is chosen over the others.
3. **What we're implementing** — what's being added/changed, and what it's responsible for.
4. **Why designed this way** — the reasoning, not just the result.
5. **Production-grade approach** — what a production system would use instead/in addition.
6. **Current learning implementation → Production-grade implementation** — named explicitly as a pair, e.g. `SQLite, one file → managed DB, connection pooling`.
7. **Trade-offs, explicitly** — simpler-but-less-scalable, faster-but-less-reliable, etc. Never present a choice as universally correct.

Shape: **Problem → Limitation → Options → Chosen solution → Why → Implementation → Production considerations.**
Keep it simple and practical — grounded in this actual codebase, not generic textbook theory.

The detailed breakdown of each point follows below.

For every limitation or architectural problem we encounter, clearly explain:

### 1. Limitation / Problem

* What is the limitation?
* Why does it exist?
* Is it a limitation of the current implementation, the framework/library, the architecture, or the underlying technology?
* What problems will it cause as the application scales?

### 2. How We Overcome It

Explain the solution before implementing it.

* What approach are we taking?
* Why does this approach solve the limitation?
* What trade-offs does it introduce?
* Are there alternative approaches?
* Why are we choosing this particular solution?

### 3. What We Are Implementing

For every new change, clearly explain:

* What component/system are we adding or modifying?
* What responsibility does it have?
* How does it fit into the existing architecture?
* How does data/state flow through it?
* What existing code will be affected?

Do not treat implementation as a black box.

### 4. Why Are We Designing It This Way?

Explain the engineering reasoning behind the design.

For example:

* Why use a dropdown instead of permanently showing repository history?
* Why keep repository state separate from the input field?
* Why show only the current AI processing step?
* Why use a particular state-management pattern?
* Why use a particular component or abstraction?

I want to understand the **"why" behind the code**, not just the final code.

### 5. Production-Grade Approach

For every major feature, explain what a **production-grade implementation** would normally use.

Include relevant:

* Libraries/frameworks
* Architecture patterns
* State-management approaches
* Caching strategies
* Error handling
* Logging/observability
* Performance considerations
* Security considerations
* Scalability considerations

If the current implementation is intentionally simpler for learning, explicitly distinguish:

**Current learning implementation → Production-grade implementation**

For example:

`Simple in-memory repository history → Persistent repository metadata/storage`

Explain when and why we would make that transition.

### 6. Teach While Implementing

Do not dump a large implementation without context.

Follow this flow for each significant change:

**Problem → Limitation → Options → Chosen solution → Why → Implementation → Production considerations**

Keep explanations practical and connected to the actual Engineering Copilot codebase.

When introducing a new technology, library, pattern, or architectural concept, briefly explain:

* What it is
* Why we need it
* Why it is appropriate here
* What problem it solves
* What alternatives exist

### 7. Be Explicit About Trade-offs

Do not present design decisions as universally correct.

Clearly mention when a decision is:

* Simpler but less scalable
* More scalable but more complex
* Better for development but not production
* Faster but less reliable
* Easier to maintain but less flexible

The goal is for me to understand **real-world engineering trade-offs**.

### Most Important Requirement

I am not just asking you to modify the UI/code.

**I want to learn software engineering by building this project.**

Therefore, explain the limitations we encounter, why they happen, how we solve them, what we are introducing, why we are introducing it, and what a production-grade system would use instead or in addition.

Do not make assumptions about what I already understand. Explain new architectural concepts clearly, but keep the explanation focused on the actual project rather than giving generic textbook theory.
