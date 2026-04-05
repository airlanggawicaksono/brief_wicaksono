EXTRACTION_PROMPT = """Extract the user's intent and entities from natural language input.

Context:
This system handles marketing and product data including products, audiences, campaigns, and performance metrics.

Intent labels (pick exactly one):
- data_query: any question about products, audiences, campaigns, or performance data
- general: casual greetings, small talk, or non-data questions
- clarification: user objective is ambiguous — you cannot confidently pick data_query or general

Entity extraction rules:
- Only extract entities when intent is data_query.
- For general or clarification, set entities to null.

Entities (extract when intent is data_query):
- target: audience segment (for example: gen z, millennials, students)
- category: product category (for example: skincare, makeup, haircare)
- price_max: maximum price in IDR

Always output valid JSON for the target schema.
"""
