# TASKGEMIUS — Chatbot SOP (Conversational Command Facade)

## Operating Model (Mandatory)
**Interpret → Validate → Disambiguate → Execute**

### 1) Interpret (chatbot-service)
- Identify user intent (create/update/delete/query/summary)
- Extract entities (title, deadline, priority, category, estimate, target identifiers)
- Produce a structured action proposal

### 2) Validate (core-api)
- Validate enums against shared/contracts/enums.json
- Validate dates, formats, and required fields
- Apply authorization rules (user scope)
- Compute derived urgency (time-based) if relevant
- Check duplicates/overlaps policy and generate candidates if needed

### 3) Disambiguate (chatbot-service + core-api)
Triggered when:
- Required fields are missing
- Update/delete target is unclear
- Candidate duplicates/overlaps exist

Rules:
- Ask **one** targeted clarification question at a time
- Provide candidate choices when available
- Do not proceed to execution until ambiguity is resolved

### 4) Execute (core-api)
Execution conditions:
- `ready=true`
- Required fields are present
- Target is unambiguous (update/delete)
- Delete has explicit confirmation

Mutations must only occur in core-api.

## Mandatory Safety Rules
- **Delete requires explicit confirmation**
- **Update/Delete requires unambiguous target**
- **No DB access from chatbot-service**
- **No direct mutation from chatbot-service**
- Chatbot outputs are proposals; core-api is authoritative

## Duplicate/Overlap Handling Policy
- core-api returns candidate tasks when potential duplicates/overlaps are detected
- chatbot-service asks the user to:
  - update an existing task
  - create a new task anyway
  - (optional) merge/ignore if implemented as a custom feature
No mutation occurs until the user chooses.
