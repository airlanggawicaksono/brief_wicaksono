INTENT_DETECTION_PROMPT = """Extract the user's intent and entities from natural language input.

Context:
This system handles marketing and product data including products, audiences, campaigns, and performance metrics.

Intent labels (pick exactly one):
- data_query: any question that mentions or asks about products, audiences, campaigns, performance, prices, brands, categories, or any data in the system — even if vague (e.g. "what products do you have?", "produknya apa aja?", "show me campaigns")
- general: casual greetings, small talk, or questions clearly unrelated to the data domain (e.g. "hello", "how are you", "what's the weather")
- clarification: user objective is genuinely ambiguous — you cannot tell if they want data or are just chatting

When in doubt between data_query and general, prefer data_query.

Entity extraction rules:
- Only extract entities when intent is data_query.
- For general or clarification, set entities to null.

Entities (extract when intent is data_query):
- target: audience segment (for example: gen z, millennials, students)
- category: product category (for example: skincare, makeup, haircare)
- price_max: maximum price in IDR

Always output valid JSON for the target schema.
"""
