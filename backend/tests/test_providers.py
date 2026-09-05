"""People-search provider behaviour that is easy to regress and impossible to see locally.

None of these touch the network: they exercise normalisation and configuration, which is
where the free-tier surprises live.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.integrations.people.base import SearchCriteria
from app.integrations.people.coresignal import CoresignalProvider
from app.integrations.people.pdl import PRODUCTION_URL, SANDBOX_URL, PdlProvider
from app.main import _build_providers


class TestPdlFreeTier:
    def test_boolean_contact_fields_do_not_become_the_string_true(self) -> None:
        """PDL's free tier returns contact fields as booleans, not values."""
        person = PdlProvider._normalize(
            {
                "id": "abc",
                "full_name": "ananya iyer",
                "job_title": "Senior Frontend Engineer",
                "mobile_phone": True,
                "work_email": True,
                "personal_emails": [],
            }
        )
        assert person.phone is None
        assert person.email is None
        assert person.name == "Ananya Iyer"

    def test_real_contact_values_still_come_through(self) -> None:
        person = PdlProvider._normalize(
            {
                "id": "abc",
                "full_name": "rohan mehta",
                "mobile_phone": "+919876500001",
                "work_email": "rohan@example.com",
            }
        )
        assert person.phone == "+919876500001"
        assert person.email == "rohan@example.com"

    def test_blank_strings_are_treated_as_absent(self) -> None:
        person = PdlProvider._normalize({"id": "x", "full_name": "a b", "mobile_phone": "   "})
        assert person.phone is None


class TestPdlSandbox:
    @pytest.mark.parametrize(
        ("sandbox", "expected"), [(True, SANDBOX_URL), (False, PRODUCTION_URL)]
    )
    def test_sandbox_flag_picks_the_base_url(self, sandbox: bool, expected: str) -> None:
        provider = PdlProvider("key", sandbox=sandbox)
        assert str(provider._http.base_url).rstrip("/") == expected
        assert provider.sandbox is sandbox


class TestCoresignal:
    def test_collect_is_capped_so_one_search_cannot_drain_the_trial(self) -> None:
        """Every collected profile costs 20 credits, so the cap is the spend limit."""
        provider = CoresignalProvider("key", max_collect=3)
        assert provider._max_collect == 3
        assert min(SearchCriteria(limit=50).limit, provider._max_collect) == 3

    def test_query_targets_the_documented_employee_fields(self) -> None:
        query = CoresignalProvider.build_query(
            SearchCriteria(titles=["Backend Engineer"], locations=["Bengaluru"], skills=["python"])
        )
        rendered = repr(query)
        assert "active_experience_title" in rendered
        assert "location_full" in rendered
        assert "inferred_skills" in rendered

    def test_empty_criteria_still_produce_a_valid_query(self) -> None:
        query = CoresignalProvider.build_query(SearchCriteria())
        assert query["query"]["bool"]["must"] == [{"match_all": {}}]

    def test_record_normalises_without_a_flat_company_name(self) -> None:
        person = CoresignalProvider._normalize(
            {
                "id": 4021,
                "full_name": "Priya Nair",
                "active_experience_title": "Full Stack Engineer",
                "experience": [{"company_name": "Freshworks"}],
                "location_full": "Chennai, Tamil Nadu, India",
                "inferred_skills": ["node.js", "react"],
                "total_experience_duration_months": 66,
            }
        )
        assert person.source == "coresignal"
        assert person.source_ref == "4021"
        assert person.current_company == "Freshworks"
        assert person.years_experience == 5.5
        assert person.phone is None  # Coresignal sells firmographics, not dialable numbers


class TestProviderRegistry:
    def test_only_the_demo_dataset_is_on_without_keys(self) -> None:
        assert list(_build_providers(Settings(env="test")).keys()) == ["mock"]

    def test_providers_are_ordered_cheapest_real_source_first(self) -> None:
        settings = Settings(env="test", pdl_api_key="a", coresignal_api_key="b", apollo_api_key="c")
        assert list(_build_providers(settings).keys()) == ["mock", "pdl", "coresignal", "apollo"]

    def test_pdl_defaults_to_the_free_sandbox(self) -> None:
        provider = _build_providers(Settings(env="test", pdl_api_key="a"))["pdl"]
        assert isinstance(provider, PdlProvider)
        assert provider.sandbox is True
