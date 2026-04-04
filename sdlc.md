
---

# lifecycle of software artifact
## AI-Powered Natural Language Query System

## 1. Planning

### 1.1 Problem Definition

Organizations often require data retrieval from relational databases, but many end users cannot write SQL queries directly. This creates dependency on technical staff, slows down access to information, and increases the risk of miscommunication in data requests. Therefore, a system is needed that can accept natural language input, interpret user intent, transform it into a structured query plan, and retrieve data safely from a database.

### 1.2 Project Background

The proposed system is an AI-powered chatbot application that performs Natural Language Understanding (NLU) to interpret user requests and translate them into structured query instructions. These instructions are validated and then executed against a relational database in read-only mode. To improve modularity and extensibility, the system may also use subprocess-based tools for isolated execution tasks, such as query transformation, temporary result processing, or result formatting. Query results may be temporarily stored in memory or in a temporary subprocess file to support preview, reuse, and tabular display, including through pandas-based processing.

### 1.3 Business Goal

The business goals of this project are:

1. To reduce dependence on manual SQL writing.
2. To enable non-technical users to retrieve data through natural language.
3. To improve the speed and accessibility of data retrieval.
4. To reduce the risk of invalid, unsafe, or misunderstood query requests.

### 1.4 Project Objective

This project aims to build a minimum viable product that:

1. Accepts natural language user input.
2. Detects user intent and extracts relevant entities.
3. Produces a structured query plan.
4. Validates the plan against technical and business policies.
5. Executes safe read-only database queries.
6. Returns results in a readable and user-friendly format.
7. Supports temporary result storage for further formatting, subprocess access, or frontend display.

### 1.5 Scope

#### 1.5.1 In Scope

The project includes:

1. Natural language input processing.
2. Intent detection and entity extraction.
3. Structured query plan generation.
4. Schema-aware database querying.
5. Read-only data retrieval.
6. Validation of unsafe or unsupported requests.
7. Unknown and invalid query handling.
8. Use of subprocess tools for isolated supporting tasks.
9. Temporary result storage in memory or temp files for display and transformation.
10. Simple frontend interface for user interaction.
11. Backend API for prediction and search.

#### 1.5.2 Out of Scope

The project does not include:

1. Insert, update, delete, or schema-altering queries.
2. Advanced role-based access control.
3. Multi-database distributed querying.
4. Full enterprise-scale schema coverage.
5. Permanent file-based analytical storage.
6. Autonomous multi-agent orchestration.
7. Heavy BI/dashboarding features.

### 1.6 Constraints

The project must operate under the following constraints:

1. The solution is limited to MVP scope.
2. Database access must remain read-only.
3. AI output may be unreliable and therefore must be validated.
4. Schema complexity must remain manageable.
5. Unsafe operations must be blocked at both technical and business levels.
6. Temporary storage must not replace the primary database.
7. Subprocess execution must remain controlled and limited to safe internal tools.

### 1.7 Assumptions

The project assumes that:

1. The database schema is known in advance.
2. A fixed set of supported intents can be defined for the MVP.
3. Users mainly request retrieval-based queries.
4. Temporary result storage is short-lived and non-authoritative.
5. The frontend only needs simple, functional visualization.

---

## 2. Requirements Analysis

### 2.1 Functional Requirements

The system shall:

1. Accept natural language input from the user.
2. Detect the user’s intent.
3. Extract entities relevant to query construction.
4. Convert intent and entities into a structured query plan.
5. Validate the query plan against output schema rules.
6. Validate the query plan against safety and business rules.
7. Reject unsupported or unsafe requests.
8. Map the validated query plan into SQL or ORM-based query logic.
9. Execute read-only queries against a relational database.
10. Return results in a readable response format.
11. Handle unknown or invalid requests using fallback responses.
12. Provide an API endpoint for prediction.
13. Provide an API endpoint for search/query execution.
14. Support subprocess-based internal tools for isolated processing tasks.
15. Support temporary result persistence in memory or temporary files.
16. Allow temporary result display in tabular form, such as through pandas dataframes or equivalent formatting tools.

### 2.2 Non-Functional Requirements

The system should:

1. Produce consistent structured output.
2. Be modular and easy to extend.
3. Remain maintainable and testable.
4. Respond within acceptable time for simple requests.
5. Ensure safe degradation when AI output is invalid.
6. Keep database access strictly read-only.
7. Log query planning and execution behavior for debugging.
8. Prevent subprocess tools from executing arbitrary unsafe operations.
9. Ensure temporary results are isolated and disposable.

### 2.3 User Requirements

Users need to:

1. Enter plain-language questions.
2. View parsed intent and extracted filters.
3. Receive useful query results without writing SQL.
4. Be informed clearly when a request is unsupported or unsafe.
5. View result data in an understandable table or card-based layout.

---

## 3. System Design

### 3.1 High-Level Architecture

The overall system flow is as follows:

`User Input -> Frontend -> API -> NLU Parser -> Structured Query Plan -> Validation/Policy Layer -> Query Builder -> Database -> Result Store -> Formatter -> UI`

### 3.2 Main Components

#### 3.2.1 Frontend

The frontend is responsible for:

1. Receiving user input.
2. Sending requests to the backend API.
3. Displaying interpreted intent and entities.
4. Displaying results in a readable format.

#### 3.2.2 API Layer

The API layer is responsible for:

1. Receiving HTTP requests.
2. Calling the correct application use case.
3. Returning structured responses.

#### 3.2.3 NLU / AI Parser

The parser is responsible for:

1. Interpreting natural language.
2. Extracting intent and entities.
3. Producing structured output in a predefined schema.

#### 3.2.4 Validation Layer

The validation layer is responsible for:

1. Checking whether AI output matches the expected schema.
2. Repairing or rejecting malformed output.
3. Normalizing fields such as price or category.

#### 3.2.5 Policy Layer

The policy layer is responsible for:

1. Enforcing read-only behavior.
2. Blocking disallowed operations.
3. Checking business-level safety constraints.
4. Restricting unsupported query patterns.

#### 3.2.6 Query Builder

The query builder is responsible for:

1. Mapping entities into SQL or ORM filters.
2. Generating safe query conditions.
3. Avoiding raw unsafe query concatenation.

#### 3.2.7 Repository / Data Access Layer

The repository is responsible for:

1. Executing the query against the database.
2. Returning structured raw records.
3. Keeping database logic separate from business logic.

#### 3.2.8 Subprocess Tool Layer

The subprocess tool layer is optional and is responsible for isolated secondary tasks, such as:

1. Temporary result transformation.
2. Dataframe generation for preview.
3. Temporary export to a subprocess file.
4. Controlled post-processing tasks.

This layer must not be used for direct unrestricted code execution. It should only run predefined internal tools.

#### 3.2.9 Temporary Result Store

The temporary result store is responsible for short-lived result persistence. It may use:

1. In-memory storage for fast preview and session-bound use.
2. Temporary files for subprocess interoperability or temporary display/export workflows.

This storage is not the source of truth. It only stores execution results.

#### 3.2.10 Response Formatter

The formatter is responsible for:

1. Converting records into readable output.
2. Preparing frontend-friendly response payloads.
3. Optionally preparing tabular views.

---

## 4. Sequential Development Process

### 4.1 Phase 1: Planning

At this phase, the project problem, business goals, constraints, and scope are defined. Supported intents, database schema boundaries, and read-only rules are identified.

**Outputs:**

* Problem statement
* Scope statement
* Business goals
* Initial requirements list

### 4.2 Phase 2: Requirements Analysis

At this phase, functional and non-functional requirements are documented. The expected user flow, API behavior, and safety constraints are specified.

**Outputs:**

* Functional requirements
* Non-functional requirements
* User requirements
* Initial use case list

### 4.3 Phase 3: System Design

At this phase, the architecture is designed. Responsibilities are separated across frontend, backend, parser, validator, policy layer, query builder, repository, subprocess tool layer, and temporary result store.

**Outputs:**

* High-level architecture diagram
* API contract
* Data flow design
* Component responsibilities

### 4.4 Phase 4: Implementation

Implementation is performed in the following order:

#### 4.4.1 Backend Foundation

* Create project structure
* Set up database connection
* Define schema models
* Create seed data

#### 4.4.2 Structured Output Module

* Implement natural language parsing
* Define structured output schema
* Add validation and fallback behavior

#### 4.4.3 Query Planning Module

* Convert structured entities into query filters
* Add query planning logic
* Restrict operations to read-only mode

#### 4.4.4 Data Access Module

* Implement repositories
* Execute safe ORM or SQL queries
* Return records in structured form

#### 4.4.5 Temporary Result Storage

* Store result snapshots in memory or temp files
* Assign short-lived identifiers if needed
* Support access for preview or subprocess formatting

#### 4.4.6 Subprocess Tool Integration

* Add predefined subprocess tools for result transformation
* Allow tools to read temporary result snapshots
* Limit subprocess scope to internal approved commands only

#### 4.4.7 Frontend Integration

* Build input form
* Display parsed intent and entities
* Display query results in readable form
* Optionally display dataframe-like preview

### 4.5 Phase 5: Testing

Testing ensures that parsing, planning, validation, data retrieval, temporary storage, and display all work correctly.

### 4.6 Phase 6: Deployment

The system is deployed with:

* separate frontend
* separate backend
* read-only database credentials
* configuration through environment variables

### 4.7 Phase 7: Maintenance

Future work includes:

* adding new intents
* supporting more entities
* improving result ranking
* extending schema coverage
* improving cache/result lifecycle management

---

## 5. Detailed Process Flow

### 5.1 Query Processing Flow

1. The user enters a natural language request.
2. The frontend sends the request to the backend.
3. The parser extracts intent and entities.
4. The validator checks schema correctness.
5. The policy layer checks safety and business rules.
6. The query builder creates a structured query plan.
7. The repository executes the query in read-only mode.
8. The results are returned.
9. The results may be stored temporarily in memory or a temp file.
10. The formatter or subprocess tool may transform the result for preview.
11. The frontend displays the final result.

### 5.2 Temporary Result Handling Flow

1. Query results are received from the repository.
2. Results are serialized into a temporary representation.
3. Results are stored either:

   * in memory for short-lived use, or
   * in a temp file for subprocess access.
4. A temporary reference ID may be generated.
5. A formatter or subprocess may read the stored result.
6. The result is rendered as table output or exported preview.
7. The temporary data is deleted after expiration or session completion.

---

## 6. Data Design

### 6.1 Primary Data Source

The primary data source is the relational database. All official query results must originate from this source.

### 6.2 Temporary Data Representation

Temporary result storage may use:

* JSON
* CSV
* dataframe-compatible structures

### 6.3 Temporary Storage Rules

1. Temporary results must be read-only.
2. Temporary files must be deleted after expiry.
3. Temporary storage must not be treated as permanent persistence.
4. Sensitive data should not be left in temp storage longer than necessary.

---

## 7. Testing Plan

### 7.1 Unit Testing

Unit tests shall cover:

1. Intent detection
2. Entity extraction
3. Schema validation
4. Policy validation
5. Query builder logic
6. Temporary result store logic
7. Subprocess tool wrapper logic

### 7.2 Integration Testing

Integration tests shall cover:

1. API to parser integration
2. Parser to validator integration
3. Validator to query builder integration
4. Query builder to repository integration
5. Repository to temporary result store integration
6. Temporary result store to formatter integration

### 7.3 End-to-End Testing

End-to-end tests shall verify:

1. User enters request
2. System interprets request
3. System validates request
4. System queries database
5. System stores temporary result
6. System displays formatted output

### 7.4 Negative Testing

Negative tests shall include:

1. Invalid JSON output from AI
2. Unknown intent
3. Missing entities
4. Unsafe query attempt
5. Unsupported schema field
6. Expired temp result access
7. Invalid subprocess tool request

---

## 8. Risk Analysis

### 8.1 Risk: Invalid AI Output

The AI may return malformed or inconsistent data.

**Mitigation:**
Use strict schema validation and fallback behavior.

### 8.2 Risk: Unsafe Query Generation

Natural language may produce dangerous or unsupported query forms.

**Mitigation:**
Enforce policy validation and read-only restrictions.

### 8.3 Risk: Excessive Complexity from Subprocess Tools

Subprocess use may complicate the system if used everywhere.

**Mitigation:**
Limit subprocess tools to isolated supporting tasks only.

### 8.4 Risk: Temporary Storage Misuse

Temporary files may become a hidden persistent layer.

**Mitigation:**
Use expiry, cleanup, and clear lifecycle rules.

---

## 9. Recommended Technical Interpretation

### 9.1 Suggested Use of Subprocess Tools

A subprocess tool is reasonable only for:

* isolated formatting
* controlled export generation
* dataframe preview generation
* safe side-process analytics

A subprocess tool is **not** a good idea for:

* normal ORM querying
* business logic
* direct unrestricted code execution

### 9.2 Suggested Use of Pandas

Pandas is fine for:

* result preview
* transformation for UI
* temporary analytical formatting

Pandas is **not** the primary backend query engine in this architecture.

### 9.3 Better Storage Rule

Use this priority:

1. database as source of truth
2. in-memory result cache for active session
3. temp file only when cross-process access is needed

That order is cleaner.

---

## 10. Conclusion

This system is designed as a modular AI-powered natural language query platform that separates parsing, validation, policy enforcement, query construction, and data access. The addition of a controlled subprocess tool layer and temporary result storage supports extensibility without turning the architecture into a mess. The database remains the primary data source, while temporary memory or file-based storage is used only for short-lived processing and presentation purposes.

---

## Appendix A. Short Version of Sequential Workflow

1. Define problem and scope
2. Analyze requirements
3. Design architecture
4. Build parser and validator
5. Build query planner and policy layer
6. Build repository and DB retrieval
7. Add temp result storage
8. Add subprocess tool support if needed
9. Integrate frontend
10. Test and deploy

---

## Appendix B. Cleaner Requirement List for Your Report

### Functional

* Convert user input into structured query plan
* Validate plan
* Enforce safe read-only policy
* Retrieve data from database
* Return readable output
* Handle unsupported requests
* Support temporary result viewing

### Non-Functional

* Modular
* extensible
* safe
* testable
* readable
* maintainable

---

