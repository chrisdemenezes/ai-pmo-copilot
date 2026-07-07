# Database Model

## Main Entities

### User
- id
- name
- role
- permissions

### Project
- id
- name
- status
- health indicators

### Document
- id
- project_id
- content
- metadata

### AI Analysis
- id
- project_id
- agent_type
- result
- created_at

## Vector Knowledge Store

Used for semantic search and contextual retrieval of project knowledge.

## Current MVP Implementation

The entities above describe the target data model. What is actually implemented today
(`src/database/repository.py`) is a single table:

### analysis_records
- `id` (int, primary key)
- `kind` (string — `"meeting"` or `"risk"`)
- `project_name` (string, nullable, indexed)
- `payload` (JSON — the full agent result)
- `created_at` (datetime, UTC)

No `User`, `Project`, or `Document` tables exist yet; `project_name` is a free-text field, not a
foreign key to a `Project` entity.
