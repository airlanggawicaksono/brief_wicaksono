"""Seed the database with sample data. Run once on startup."""
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.audience import Audience
from app.models.campaign import Campaign
from app.models.performance import Performance


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
    ]

    # -- Audiences --
    audiences = [
        Audience(id=1, name="Gen Z", age_range="15-25", preferences="affordable, trendy, social media driven"),
        Audience(id=2, name="Millennials", age_range="26-40", preferences="quality, reviews, brand loyalty"),
        Audience(id=3, name="Gen X", age_range="41-56", preferences="anti-aging, premium, trusted brands"),
        Audience(id=4, name="Students", age_range="17-23", preferences="budget, multipurpose, minimal routine"),
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
    ]

    # -- Performance --
    performance = [
        Performance(id=1, campaign_id=1, impressions=250000, clicks=18000, conversions=2200),
        Performance(id=2, campaign_id=2, impressions=180000, clicks=12000, conversions=1500),
        Performance(id=3, campaign_id=3, impressions=400000, clicks=30000, conversions=4500),
        Performance(id=4, campaign_id=4, impressions=90000, clicks=5000, conversions=800),
        Performance(id=5, campaign_id=5, impressions=120000, clicks=8000, conversions=1100),
        Performance(id=6, campaign_id=6, impressions=500000, clicks=45000, conversions=6000),
        Performance(id=7, campaign_id=7, impressions=200000, clicks=15000, conversions=1800),
        Performance(id=8, campaign_id=8, impressions=350000, clicks=28000, conversions=3500),
    ]

    db.add_all(products)
    db.add_all(audiences)
    db.flush()

    db.add_all(campaigns)
    db.flush()

    db.add_all(performance)
    db.commit()
