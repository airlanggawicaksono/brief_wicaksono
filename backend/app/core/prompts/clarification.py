DOMAIN_CLARIFICATION_PROMPT = """The previous extraction did not match a data intent.
Classify again using this domain guidance:

If user asks about any of these, use intent "data_query":
- products: category, brand, price
- audiences: segments and age ranges
- campaigns: budget, mappings, performance context
- performance: impressions, clicks, conversions, CTR

If user is just greeting, use "greeting".
If intent is still unclear, use "unknown".

Respond in the same language as the user.
User input: "{text}"
"""
