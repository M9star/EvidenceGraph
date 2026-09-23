from collections.abc import Mapping
from dataclasses import dataclass

from evidence_graph.state.models import CountryCode

DEFAULT_QUERY = (
    "Compare the latest EV incentives available in France, Germany, the UK, and India. "
    "Extract eligibility rules and benefits from official sources, with citations."
)


@dataclass(frozen=True)
class CountryProfile:
    code: CountryCode
    name: str
    allowed_domains: frozenset[str]
    search_hint: str


EV_COUNTRIES: Mapping[CountryCode, CountryProfile] = {
    CountryCode.FR: CountryProfile(
        code=CountryCode.FR,
        name="France",
        allowed_domains=frozenset(
            {"service-public.gouv.fr", "economie.gouv.fr", "ecologie.gouv.fr"}
        ),
        search_hint="coup de pouce véhicules particuliers électriques",
    ),
    CountryCode.DE: CountryProfile(
        code=CountryCode.DE,
        name="Germany",
        allowed_domains=frozenset({"bafa.de", "bundesregierung.de", "bundesfinanzministerium.de"}),
        search_hint="E-Auto-Förderung",
    ),
    CountryCode.UK: CountryProfile(
        code=CountryCode.UK,
        name="United Kingdom",
        allowed_domains=frozenset({"gov.uk"}),
        search_hint="electric car grant",
    ),
    CountryCode.IN: CountryProfile(
        code=CountryCode.IN,
        name="India",
        allowed_domains=frozenset({"heavyindustries.gov.in", "pib.gov.in", "cea.nic.in"}),
        search_hint="PM E-DRIVE scheme electric vehicle incentive",
    ),
}


def allowlists(
    profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES,
) -> dict[CountryCode, frozenset[str]]:
    return {code: profile.allowed_domains for code, profile in profiles.items()}
