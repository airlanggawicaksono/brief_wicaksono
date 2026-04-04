"""Seed the database with sample data. Run once on startup."""
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.audience import Audience
from app.models.campaign import Campaign
from app.models.performance import Performance


def _expand_campaigns(
    campaigns: list[Campaign],
    products: list[Product],
    audiences: list[Audience],
    target_count: int = 120,
) -> list[Campaign]:
    """Expand to a larger, semantically meaningful campaign set."""
    if len(campaigns) >= target_count:
        return campaigns

    objective_budget = {
        "Awareness": 8_000_000,
        "Launch": 9_500_000,
        "Conversion": 6_500_000,
        "Retention": 4_500_000,
        "Upsell": 5_500_000,
        "Seasonal": 7_200_000,
    }
    objectives = list(objective_budget.keys())

    while len(campaigns) < target_count:
        campaign_id = len(campaigns) + 1
        product = products[(campaign_id * 5 + 1) % len(products)]
        audience = audiences[(campaign_id * 3 + 2) % len(audiences)]
        objective = objectives[(campaign_id - 1) % len(objectives)]
        quarter = f"Q{((campaign_id - 1) % 4) + 1}"

        campaign_name = f"{quarter} {objective}: {product.name} for {audience.name}"
        budget = objective_budget[objective] + ((campaign_id * 175_000) % 2_000_000)

        campaigns.append(
            Campaign(
                id=campaign_id,
                name=campaign_name,
                product_id=product.id,
                audience_id=audience.id,
                budget=budget,
            )
        )

    return campaigns


def _build_performance(campaigns: list[Campaign]) -> list[Performance]:
    """Create deterministic KPI rows so query demos have richer variety."""
    rows: list[Performance] = []
    for idx, campaign in enumerate(campaigns, start=1):
        base_impressions = max(80_000, int(campaign.budget * 0.06) + (idx % 7) * 15_000)
        ctr = 0.03 + (idx % 5) * 0.007  # 3.0% .. 5.8%
        clicks = int(base_impressions * ctr)
        cvr = 0.035 + (idx % 4) * 0.012  # 3.5% .. 7.1%
        conversions = int(clicks * cvr)

        rows.append(
            Performance(
                id=idx,
                campaign_id=campaign.id,
                impressions=base_impressions,
                clicks=clicks,
                conversions=conversions,
            )
        )

    return rows


def seed_data(db: Session) -> None:
    if db.query(Product).first():
        return  # already seeded

    # -- Products --
    products = [
        Product(id=1, name="Glow Serum", category="skincare", price=85000, brand="Wardah"),
        Product(id=2, name="Matte Lipstick", category="makeup", price=45000, brand="Emina"),
        Product(id=3, name="Sunscreen SPF50", category="skincare", price=120000, brand="Somethinc"),
        Product(id=4, name="Hair Vitamin Oil", category="haircare", price=60000, brand="Makarizo"),
        Product(id=5, name="Acne Spot Gel", category="skincare", price=35000, brand="Wardah"),
        Product(id=6, name="Cushion Foundation", category="makeup", price=150000, brand="Somethinc"),
        Product(id=7, name="Micellar Water", category="skincare", price=55000, brand="Garnier"),
        Product(id=8, name="Lip Tint", category="makeup", price=30000, brand="Emina"),
        Product(id=9, name="Body Lotion SPF", category="bodycare", price=40000, brand="Nivea"),
        Product(id=10, name="Clay Mask", category="skincare", price=75000, brand="Innisfree"),
        Product(id=11, name="Niacinamide Booster", category="skincare", price=99000, brand="Avoskin"),
        Product(id=12, name="Hydrating Toner", category="skincare", price=68000, brand="Skintific"),
        Product(id=13, name="Peptide Moisturizer", category="skincare", price=139000, brand="Somethinc"),
        Product(id=14, name="Retinol Night Cream", category="skincare", price=165000, brand="Avoskin"),
        Product(id=15, name="Brow Pencil", category="makeup", price=39000, brand="Implora"),
        Product(id=16, name="Volume Mascara", category="makeup", price=62000, brand="Maybelline"),
        Product(id=17, name="Blush On Peach", category="makeup", price=54000, brand="Emina"),
        Product(id=18, name="Hair Mist Sakura", category="haircare", price=79000, brand="Mise En Scene"),
        Product(id=19, name="Scalp Tonic", category="haircare", price=115000, brand="Lavojoy"),
        Product(id=20, name="Repair Hair Mask", category="haircare", price=97000, brand="Makarizo"),
        Product(id=21, name="Body Scrub Coffee", category="bodycare", price=58000, brand="Scarlett"),
        Product(id=22, name="Hand Cream Almond", category="bodycare", price=36000, brand="Vaseline"),
        Product(id=23, name="Eau de Parfum Fresh", category="fragrance", price=189000, brand="HMNS"),
        Product(id=24, name="Travel Perfume Citrus", category="fragrance", price=89000, brand="Carl & Claire"),
    ]

    # -- Audiences --
    audiences = [
        Audience(id=1, name="Gen Z", min_age=15, max_age=25, preferences="affordable, trendy, social media driven"),
        Audience(id=2, name="Millennials", min_age=26, max_age=40, preferences="quality, reviews, brand loyalty"),
        Audience(id=3, name="Gen X", min_age=41, max_age=56, preferences="anti-aging, premium, trusted brands"),
        Audience(id=4, name="Students", min_age=17, max_age=23, preferences="budget, multipurpose, minimal routine"),
        Audience(id=5, name="Young Professionals", min_age=22, max_age=34, preferences="daily essentials, practical, premium-lite"),
        Audience(id=6, name="Moms", min_age=28, max_age=45, preferences="safe ingredients, family value, trusted recommendations"),
        Audience(id=7, name="Beauty Enthusiasts", min_age=18, max_age=35, preferences="new launches, active ingredients, tutorials"),
        Audience(id=8, name="Sensitive Skin Segment", min_age=18, max_age=45, preferences="fragrance-free, gentle, dermatologist-tested"),
    ]

    # -- Campaigns --
    campaigns = [
        Campaign(id=1, name="Glow Up Summer", product_id=1, audience_id=1, budget=5000000),
        Campaign(id=2, name="Matte Look Launch", product_id=2, audience_id=1, budget=3000000),
        Campaign(id=3, name="Sun Protection Awareness", product_id=3, audience_id=2, budget=8000000),
        Campaign(id=4, name="Back to School Hair", product_id=4, audience_id=4, budget=2000000),
        Campaign(id=5, name="Acne Fighter Promo", product_id=5, audience_id=4, budget=1500000),
        Campaign(id=6, name="Premium Cushion Drop", product_id=6, audience_id=2, budget=10000000),
        Campaign(id=7, name="Clean Skin Essentials", product_id=7, audience_id=1, budget=4000000),
        Campaign(id=8, name="Lip Tint Viral", product_id=8, audience_id=1, budget=6000000),
        Campaign(id=9, name="Body SPF Daily", product_id=9, audience_id=5, budget=3200000),
        Campaign(id=10, name="Mask Weekend Glow", product_id=10, audience_id=7, budget=2800000),
        Campaign(id=11, name="Niacinamide Routine", product_id=11, audience_id=7, budget=7200000),
        Campaign(id=12, name="Hydration 7 Days", product_id=12, audience_id=8, budget=3600000),
        Campaign(id=13, name="Peptide Lift Story", product_id=13, audience_id=2, budget=8300000),
        Campaign(id=14, name="Retinol Smart Start", product_id=14, audience_id=3, budget=7600000),
        Campaign(id=15, name="Brow Everyday", product_id=15, audience_id=4, budget=2400000),
        Campaign(id=16, name="Mascara Office Look", product_id=16, audience_id=5, budget=3100000),
        Campaign(id=17, name="Peach Blush Weekend", product_id=17, audience_id=1, budget=2500000),
        Campaign(id=18, name="Hair Mist Refresh", product_id=18, audience_id=5, budget=3400000),
        Campaign(id=19, name="Scalp Health Month", product_id=19, audience_id=6, budget=4700000),
        Campaign(id=20, name="Mask Repair Hair", product_id=20, audience_id=2, budget=4200000),
        Campaign(id=21, name="Coffee Scrub Glow", product_id=21, audience_id=1, budget=3900000),
        Campaign(id=22, name="Hand Cream Office", product_id=22, audience_id=5, budget=2100000),
        Campaign(id=23, name="Fresh Perfume Launch", product_id=23, audience_id=7, budget=9400000),
        Campaign(id=24, name="Travel Perfume Ads", product_id=24, audience_id=1, budget=5300000),
        Campaign(id=25, name="Gen Z Skincare Bundle", product_id=12, audience_id=1, budget=5600000),
        Campaign(id=26, name="Sensitive Skin Starter", product_id=11, audience_id=8, budget=6100000),
        Campaign(id=27, name="Mom Hair Recovery", product_id=20, audience_id=6, budget=3800000),
        Campaign(id=28, name="Campus Makeup Pack", product_id=17, audience_id=4, budget=3300000),
        Campaign(id=29, name="Premium Anti Aging Push", product_id=14, audience_id=3, budget=9800000),
        Campaign(id=30, name="Office Fragrance Trial", product_id=24, audience_id=5, budget=3000000),
        Campaign(id=31, name="Weekend Acne Rescue", product_id=5, audience_id=1, budget=2700000),
        Campaign(id=32, name="Sunscreen Family Pack", product_id=3, audience_id=6, budget=6900000),
    ]
    campaigns = _expand_campaigns(campaigns, products, audiences, target_count=120)

    # -- Performance --
    performance = _build_performance(campaigns)

    db.add_all(products)
    db.add_all(audiences)
    db.flush()

    db.add_all(campaigns)
    db.flush()

    db.add_all(performance)
    db.commit()
