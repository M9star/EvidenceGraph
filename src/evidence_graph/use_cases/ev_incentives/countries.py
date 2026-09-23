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
    # Hand-verified official pages, used when no search API key is configured.
    seed_urls: tuple[str, ...] = ()


EV_COUNTRIES: Mapping[CountryCode, CountryProfile] = {
    CountryCode.FR: CountryProfile(
        code=CountryCode.FR,
        name="France",
        allowed_domains=frozenset(
            {"service-public.gouv.fr", "economie.gouv.fr", "ecologie.gouv.fr"}
        ),
        search_hint="coup de pouce véhicules particuliers électriques",
        seed_urls=(
            "https://www.service-public.gouv.fr/particuliers/vosdroits/F39188",
            "https://www.service-public.gouv.fr/particuliers/actualites/A16990",
        ),
    ),
    CountryCode.DE: CountryProfile(
        code=CountryCode.DE,
        name="Germany",
        allowed_domains=frozenset({"bafa.de", "bundesregierung.de", "bundesfinanzministerium.de"}),
        search_hint="E-Auto-Förderung",
        seed_urls=(
            "https://www.bafa.de/DE/Energie/Energieeffizienz/E-Auto_Foerderung_2026/Haeufige_Fragen/Haeufige_Fragen_node.html",
            "https://www.bafa.de/DE/Energie/Energieeffizienz/E-Auto_Foerderung_2026/Antrag_Stellen/Antrag_Stellen_node.html",
        ),
    ),
    CountryCode.UK: CountryProfile(
        code=CountryCode.UK,
        name="United Kingdom",
        allowed_domains=frozenset({"gov.uk"}),
        search_hint="electric car grant",
        seed_urls=(
            "https://www.gov.uk/zero-emission-vehicle-grants/cars",
            "https://find-government-grants.service.gov.uk/grants/electric-car-grant-1",
        ),
    ),
    CountryCode.IN: CountryProfile(
        code=CountryCode.IN,
        name="India",
        allowed_domains=frozenset({"heavyindustries.gov.in", "pib.gov.in", "cea.nic.in"}),
        search_hint="PM E-DRIVE scheme electric vehicle incentive",
        seed_urls=(
            "https://pmedrive.heavyindustries.gov.in/",
            "https://pmedrive.heavyindustries.gov.in/about-us",
        ),
    ),
}


def allowlists(
    profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES,
) -> dict[CountryCode, frozenset[str]]:
    return {code: profile.allowed_domains for code, profile in profiles.items()}


def seed_urls(
    profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES,
) -> dict[CountryCode, tuple[str, ...]]:
    return {code: profile.seed_urls for code, profile in profiles.items()}
