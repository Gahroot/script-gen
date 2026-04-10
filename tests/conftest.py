import pytest

from app.schemas import GeneratedScripts, IntakeData, PainPointSolution


@pytest.fixture
def sample_intake() -> IntakeData:
    return IntakeData(
        business_name="Acme Roofing",
        target_audience="Homeowners aged 30-55 in the Greater Toronto Area",
        pain_points_solutions=[
            PainPointSolution(
                pain_point="Leaking roof causing water damage",
                solution="Same-day emergency roof repair",
            ),
            PainPointSolution(
                pain_point="Overpriced quotes from other contractors",
                solution="Transparent flat-rate pricing with no hidden fees",
            ),
        ],
        offer="Free roof inspection plus 15% off any repair booked this month",
        risk_reversal="Full refund if not satisfied",
        guarantees="10-year workmanship warranty",
        limited_availability="Only 20 inspection slots available this month",
        discounts="15% off for first-time customers",
        lead_magnet="Free Roof Maintenance Checklist PDF",
        top_stats=[
            "Over five hundred roofs repaired in the GTA",
            "Four point nine star rating on Google with two hundred reviews",
        ],
        landing_page_url="https://acmeroofing.ca/offer",
        city="Toronto",
        service_area="Greater Toronto Area",
        contact_name="John Smith",
        contact_email="john@acmeroofing.ca",
        contact_phone="416-555-1234",
    )


@pytest.fixture
def sample_scripts() -> GeneratedScripts:
    return GeneratedScripts(
        hooks=[f"Hook number {i}" for i in range(50)],
        meats=[
            "Meat one: Your roof is leaking and it is getting worse every day...",
            "Meat two: Most homeowners in the Greater Toronto Area overpay...",
            "Meat three: Here is what five hundred happy customers already know...",
        ],
        ctas=[
            "Tap the link below to book your free inspection today.",
            "Click the button below before all twenty slots are gone.",
        ],
    )
