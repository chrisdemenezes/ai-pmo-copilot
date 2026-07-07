# AI Agent Prompts

## Purpose
Define standards for AI agent behavior.

## Prompt Structure

Each prompt should contain:

- Role definition
- Context
- Input information
- Rules
- Expected output format

## Example

Role:
You are a PMO Project Analyst.

Task:
Analyze project health and identify critical deviations.

Output:
Executive summary, risks and recommendations.

## Placeholder Syntax

Prompt files (`src/agents/*/prompts/*.md`) use `$placeholder` syntax (Python `string.Template`,
substituted via `safe_substitute`), not `{placeholder}`/`str.format()`. This avoids `KeyError`
crashes when a prompt's own instructional text contains literal braces (e.g. a JSON example such
as `{"decisions": [...]}`), which `str.format()` would otherwise try to parse as a field reference.

## Governance

Prompts must be version controlled and validated.
