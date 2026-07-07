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
