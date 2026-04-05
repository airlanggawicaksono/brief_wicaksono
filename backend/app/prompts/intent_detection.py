INTENT_DETECTION_PROMPT = """Extract the user's intent and entities from natural language input.

Context:
This system handles marketing and product data including products, audiences, campaigns, and performance metrics.

Intent labels (pick exactly one):
- data_query: any question that mentions or asks about products, audiences, campaigns, performance, prices, brands, categories, or any data in the system — even if vague (e.g. "what products do you have?", "produknya apa aja?", "show me campaigns")
- general: casual greetings, small talk, or questions clearly unrelated to the data domain (e.g. "hello", "how are you", "what's the weather")
- clarification: user objective is genuinely ambiguous — you cannot tell if they want data or are just chatting

When in doubt between data_query and general, prefer data_query.

Entity extraction rules:
- Only extract entities when intent is data_query. For general or clarification, set entities to null.
- Entities are freeform key-value pairs that summarise what the user is looking for.
- Extract any keys that are useful for filtering or scoping a data query.
- Common keys: target (audience segment), category (product category), price_max (IDR), brand, metric (e.g. conversions, clicks), date_range, campaign_name, etc.
- Only extract keys that are actually present or implied in the user's message. Do not guess or fill in defaults.
- Values should be concise strings or numbers. Null values are not useful — omit the key entirely.

Examples:
  "produk skincare untuk gen z di bawah 100rb" → {"target": "gen z", "category": "skincare", "price_max": 100000}
  "kampanye wardah bulan ini" → {"brand": "Wardah", "date_range": "current month"}
  "siapa yang paling banyak konversi?" → {"metric": "conversions"}
  "tampilkan semua produk" → {}

Always output valid JSON for the target schema.
"""
