import json
from types import SimpleNamespace
from unittest.mock import patch

from app.services.digest_service import matching_opportunities


def test_profile_matches_reuses_keywords_categories_and_exclusions():
    profile = SimpleNamespace(
        include_keywords=json.dumps(["vet*"]), exclude_keywords=json.dumps(["vehículo"]),
        selected_categories=json.dumps(["50*"]), opportunity_type="all", region="",
        organization="", status="", minimum_amount=None, maximum_amount=None,
    )
    rows = [
        {"id": "1", "title": "Servicio veterinario", "description": "Clínica", "category_codes": ["5012"], "publish_date": "2026-08-01"},
        {"id": "2", "title": "Servicio veterinario", "description": "Incluye vehículo", "category_codes": ["5012"], "publish_date": "2026-08-01"},
        {"id": "3", "title": "Servicio veterinario", "description": "Clínica", "category_codes": ["6012"], "publish_date": "2026-08-01"},
    ]
    with patch("app.services.digest_service.list_opportunities", return_value=rows) as listing:
        matches = matching_opportunities(profile, limit=None, opportunity_type="licitacion")
    assert [row["id"] for row in matches] == ["1"]
    assert listing.call_args.kwargs["opportunity_type"] == "licitacion"


def test_profile_matches_sorts_amounts_and_leaves_unknown_amounts_last():
    profile = SimpleNamespace(
        include_keywords="[]", exclude_keywords="[]", selected_categories="[]",
        opportunity_type="licitacion", region="", organization="", status="",
        minimum_amount=None, maximum_amount=None,
    )
    rows = [
        {"id": "unknown", "title": "Sin monto", "description": "", "category_codes": [], "amount": None},
        {"id": "small", "title": "Monto menor", "description": "", "category_codes": [], "amount": 10},
        {"id": "large", "title": "Monto mayor", "description": "", "category_codes": [], "amount": 100},
    ]
    with patch("app.services.digest_service.list_opportunities", return_value=rows):
        matches = matching_opportunities(profile, limit=None, sort="amount_desc")
    assert [row["id"] for row in matches] == ["large", "small", "unknown"]
