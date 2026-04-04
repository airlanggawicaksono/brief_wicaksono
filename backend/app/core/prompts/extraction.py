EXTRACTION_PROMPT = """Extract the user's intent and entities from natural language input.

Context:
This system handles marketing and product data including products, audiences, campaigns, and performance metrics.

Intent labels:
- data_query: any question about products, audiences, campaigns, or performance data
- greeting: casual greetings, hellos, small talk
- unknown: user objective is unclear

Entities (extract when present):
- target: audience segment (for example: gen z, millennials, students)
- category: product category (for example: skincare, makeup, haircare)
- price_max: maximum price in IDR

Always output valid JSON for the target schema.
"""
