from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainProfile:
    code: str
    title: str
    description: str
    suggested_modules: tuple[str, ...] = ()


DOMAIN_PROFILES: tuple[DomainProfile, ...] = (
    DomainProfile("GENERAL_SERVICES", "General Services", "General service businesses and mixed service operations."),
    DomainProfile("SOFTWARE_SAAS", "Software / SaaS", "Software licensing, SaaS, subscriptions and digital services."),
    DomainProfile("RETAIL", "Retail", "Retail, stores, omnichannel and consumer sales.", ("Selling", "Stock")),
    DomainProfile("WHOLESALE_DISTRIBUTION", "Wholesale / Distribution", "Wholesale, distribution and trade operations.", ("Selling", "Buying", "Stock")),
    DomainProfile("MANUFACTURING", "Manufacturing", "Discrete or process manufacturing operations.", ("Manufacturing", "Stock", "Buying")),
    DomainProfile("REAL_ESTATE", "Real Estate", "Property development, brokerage, leasing and property operations.", ("Projects", "Selling")),
    DomainProfile("HOSPITALITY", "Hospitality", "Hotels, resorts, serviced stays and hospitality operations."),
    DomainProfile("HEALTHCARE", "Healthcare", "Clinics, hospitals, laboratories, rehabilitation and care facilities."),
    DomainProfile("EDUCATION", "Education", "Schools, training providers and education organizations."),
    DomainProfile("AGRICULTURE", "Agriculture", "Agriculture, livestock, aquaculture and related operations."),
    DomainProfile("LOGISTICS", "Logistics", "Warehousing, delivery, transport and logistics operations.", ("Stock",)),
    DomainProfile("CONSTRUCTION", "Construction", "Construction contractors and project-based operations.", ("Projects", "Buying")),
    DomainProfile("PROFESSIONAL_SERVICES", "Professional Services", "Consulting, agencies and professional service firms.", ("Projects",)),
    DomainProfile("NONPROFIT", "Nonprofit", "Associations, foundations and nonprofit organizations."),
    DomainProfile("OTHER", "Other / Custom", "Start from a neutral profile and configure manually."),
)


def get_domain_profile(code: str) -> DomainProfile:
    for profile in DOMAIN_PROFILES:
        if profile.code == code:
            return profile
    raise ValueError(f"Unknown Vietnam business profile: {code}")


def get_domain_profile_options() -> list[dict[str, object]]:
    return [
        {
            "code": p.code,
            "title": p.title,
            "description": p.description,
            "suggested_modules": list(p.suggested_modules),
        }
        for p in DOMAIN_PROFILES
    ]
