# Fullstack Developer (AI Engineer) Exercise Test

**Date:** 00/00/2025

## Objective

Build a simple AI-powered system that can interpret natural language input and transform it into structured information, and optionally use that information to retrieve meaningful data.

Focus on:
- clear system design
- useful output
- ability to extend beyond basic functionality

## Functional Requirements

### Level 1 (Required): Text → Structured Output

#### Description
Build a system that converts natural language into structured data.

#### Expected Flow
`user input → structured output (intent + entities)`

#### Requirements
- Provide an API endpoint (e.g., `POST /predict`)
- Output must be consistent, structured JSON
- Use an AI model (or equivalent approach)
- Handle unreliable outputs (e.g., invalid format)

#### Example

**Input:**

`"show me skincare products for gen z under 100k"`

**Output:**

```json
{
  "intent": "product_search",
  "entities": {
    "category": "skincare",
    "target": "gen z",
    "price_max": 100000
  }
}
```

### Level 2 (Expected): Usable Output (Frontend)

#### Description
Extend your system so users can interact with it and understand the results easily.

#### Expected Flow
`user input → API → structured output → UI display`

#### Requirements
- Input field
- Submit button
- Display results in a clear, user-friendly format (not raw JSON)

#### Notes
- Keep the UI simple; focus on clarity, not design

### Level 3 (Optional): Structured Output → Usage

#### Description
Show how structured output is used to drive logic in your system.

#### Expected Flow
`user input → structured output → logic/processing → result`

#### Requirements
- Use extracted entities in your application logic
- Produce output that is more useful than raw structured data

#### Examples
- filtering in-memory data
- enriching results with computed values
- generating simple insights

### Level 4 (Optional – Advanced): Natural Language → Data Query

#### Description
Extend your system so structured output is used to retrieve data from a dataset or database.

#### Expected Flow
`user input → structured output → query/filter → data → result`

#### Requirements
- Map entities into query conditions (filters, joins, etc.)
- Avoid hardcoded or single-case queries
- Show a clear connection between:
  - input
  - structured data
  - data retrieval

#### Notes
- You should use a relational database (e.g., PostgreSQL, SQLite)
- In-memory data or CSV-only solutions are not sufficient for this level
- Focus on how natural language is translated into query logic, not on database complexity

## Sample Data Schema (Only for Level 4)

You may use or adapt this schema.

### `products`
- `id`
- `name`
- `category`
- `price`
- `brand`

### `audiences`
- `id`
- `name`
- `age_range`
- `preferences`

### `campaigns`
- `id`
- `name`
- `product_id`
- `audience_id`
- `budget`

### `performance`
- `id`
- `campaign_id`
- `impressions`
- `clicks`
- `conversions`

## Technical Expectations
- Backend: any language/framework
- Frontend: simple and functional
- API: clear and usable
- Code: modular and readable

## Design Considerations

Your system should:
- separate responsibilities clearly
- be adaptable (e.g., model or schema changes)
- produce output usable by other components

Think about:
- mapping natural language → structured data
- how output is used downstream
- handling unreliable AI behavior

## Deliverables
- Repository (GitHub or zip)
- Separate frontend and backend

## README

Include:
- setup instructions
- how to run
- assumptions
- limitations

## Short Write-up (1–2 pages)

Explain:
- system design
- structure
- handling of AI output
- trade-offs

## Evaluation Criteria
- code clarity
- usefulness of output
- extensibility
- handling of AI uncertainty
- end-to-end functionality

## Notes

Not all levels are required.

Level 1 and Level 2 represent the minimum expected scope. Higher levels are optional and intended to demonstrate deeper thinking and system design.

The levels help us understand how far you can extend your solution.

Good luck!

---

**Contact**
- Phone: +62 899-9067-517
- Email: harry.setyono@wppmedia.com
- Website: www.wppmedia.com
