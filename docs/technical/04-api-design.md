# API Design

## Purpose
Define communication contracts between application components.

## Core APIs

### Project Analysis API

POST /api/projects/analyze

Input:
- Project data
- Documents
- Context

Output:
- Analysis
- Recommendations

### Meeting Intelligence API

POST /api/meetings/process

Output:
- Summary
- Decisions
- Actions

### Risk Analysis API

POST /api/risks/analyze

Output:
- Risk assessment
- Mitigation plan
