DOMAIN_CLARIFICATION_PROMPT = """The previous extraction returned "unknown" intent.
Try again with these domain-specific hints:

This system handles marketing/product data. The user is likely asking about one of:
- product_search: finding products by category (skincare, makeup, haircare), brand, or price
- audience_lookup: info about target audiences (gen z, millennials, students)
- campaign_lookup: marketing campaigns, budgets, which product targets which audience
- performance_report: campaign metrics like impressions, clicks, conversions, CTR
- greeting: the user is just saying hello

If the input truly doesn't match any of these, return "unknown".

User input: "{text}" """
