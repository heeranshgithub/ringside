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


def settings(**overrides: object) -> Settings:
    """Settings with the local .env ignored, so a real key on disk cannot leak in."""
    return Settings(_env_file=None, env="test", **overrides)  # type: ignore[arg-type]


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

    def test_gated_location_falls_back_to_country(self) -> None:
        """`location_name` is a granular field, so it arrives as a boolean flag too."""
        person = PdlProvider._normalize(
            {
                "id": "x",
                "full_name": "amanda herrera",
                "location_name": True,
                "location_country": "canada",
            }
        )
        assert person.location == "canada"

    def test_boolean_list_fields_do_not_raise(self) -> None:
        """Gated collections arrive as booleans, and `iter(True)` raises TypeError."""
        person = PdlProvider._normalize(
            {
                "id": "x",
                "full_name": "a b",
                "phone_numbers": True,
                "personal_emails": True,
                "skills": False,
            }
        )
        assert person.phone is None
        assert person.email is None
        assert person.skills == []

    def test_a_real_sandbox_record_normalises(self) -> None:
        """Shape copied from a live sandbox response."""
        person = PdlProvider._normalize(
            {
                "id": "qEnOZ5Oh0poWnQ1luFBfVw_0000",
                "full_name": "amanda amanda herrera",
                "job_title": "software engineer",
                "job_company_name": "wade inc",
                "mobile_phone": True,
                "work_email": True,
                "personal_emails": False,
                "location_name": True,
                "location_country": "canada",
                "linkedin_url": "linkedin.com/in/amanda_herrera",
                "skills": ["answer", "wide"],
                "inferred_years_experience": None,
            }
        )
        assert person.name == "Amanda Amanda Herrera"
        assert person.current_title == "software engineer"
        assert person.location == "canada"
        assert person.phone is None and person.email is None
        assert person.linkedin_url == "https://linkedin.com/in/amanda_herrera"
        assert person.years_experience is None


class TestPdlQuery:
    def test_query_omits_minimum_should_match(self) -> None:
        """PDL's Elasticsearch subset rejects it outright: 400 invalid_request_error."""
        query = PdlProvider.build_query(
            SearchCriteria(titles=["Software Engineer"], locations=["Bengaluru"], skills=["python"])
        )
        assert "minimum_should_match" not in repr(query)

    def test_a_location_becomes_a_city_term_not_a_composite_match(self) -> None:
        """PDL keyword fields hold a bare city, so "Gurugram, India" must not be sent whole.

        This clause is a `must`: when it matched nothing, every search returned zero. The
        live API scored the composite string at 0 hits and `location_locality = gurugram`
        at 777,632 on 2026-09-06.
        """
        clause = PdlProvider.build_query(SearchCriteria(locations=["Gurugram, India"]))["bool"][
            "must"
        ][0]
        assert clause["bool"]["should"] == [
            {"term": {"location_locality": "gurugram"}},
            {"term": {"location_region": "gurugram"}},
        ]

    def test_a_location_with_no_comma_still_produces_a_term(self) -> None:
        clause = PdlProvider.build_query(SearchCriteria(locations=["Bengaluru"]))["bool"]["must"][0]
        assert {"term": {"location_locality": "bengaluru"}} in clause["bool"]["should"]

    def test_a_blank_location_is_dropped_rather_than_zeroing_the_search(self) -> None:
        assert PdlProvider.build_query(SearchCriteria(locations=[" ", ","]))["bool"]["must"] == []

    def test_a_bare_should_still_requires_one_match(self) -> None:
        """Dropping the parameter is safe: a bool with only `should` defaults to one match."""
        inner = PdlProvider.build_query(SearchCriteria(titles=["a", "b"]))["bool"]["must"][0]
        assert set(inner["bool"]) == {"should"}
        assert len(inner["bool"]["should"]) == 2


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
        assert list(_build_providers(settings()).keys()) == ["mock"]

    def test_providers_are_ordered_cheapest_real_source_first(self) -> None:
        configured = settings(pdl_api_key="a", coresignal_api_key="b", apollo_api_key="c")
        assert list(_build_providers(configured).keys()) == ["mock", "pdl", "coresignal", "apollo"]

    def test_pdl_defaults_to_the_free_sandbox(self) -> None:
        provider = _build_providers(settings(pdl_api_key="a"))["pdl"]
        assert isinstance(provider, PdlProvider)
        assert provider.sandbox is True


class TestCallingWindow:
    """Hunar rejects a window outside 08:00-21:00 before it even looks up the agent.

    Bounds measured against the live API on 2026-09-06; they are not in its OpenAPI schema.
    """

    def test_defaults_are_inside_the_platform_window(self) -> None:
        from app.modules.calls.schemas import GuardrailsInput

        g = GuardrailsInput()
        assert g.earliest_call_time == "08:00"
        assert g.last_call_time == "21:00"

    @pytest.mark.parametrize(
        ("earliest", "last"),
        [("00:00", "23:59"), ("07:59", "20:00"), ("08:00", "23:59"), ("08:00", "21:01")],
    )
    def test_a_window_hunar_would_reject_never_leaves_this_app(
        self, earliest: str, last: str
    ) -> None:
        from pydantic import ValidationError

        from app.modules.calls.schemas import GuardrailsInput

        with pytest.raises(ValidationError):
            GuardrailsInput(earliest_call_time=earliest, last_call_time=last)

    def test_an_inverted_window_is_rejected(self) -> None:
        from pydantic import ValidationError

        from app.modules.calls.schemas import GuardrailsInput

        with pytest.raises(ValidationError):
            GuardrailsInput(earliest_call_time="20:00", last_call_time="09:00")

    def test_the_verification_call_uses_the_widest_legal_window(self) -> None:
        from app.integrations.hunar.schemas import EARLIEST_CALL_TIME, LATEST_CALL_TIME
        from app.modules.dial.service import WIDEST_WINDOW

        assert WIDEST_WINDOW.earliest_call_time == EARLIEST_CALL_TIME
        assert WIDEST_WINDOW.last_call_time == LATEST_CALL_TIME
