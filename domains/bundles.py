"""Aggregate domain bundle metadata from org-owned slices."""

from __future__ import annotations

from domains.bundle import DomainBundle
from domains.ebom.bundle import BUNDLE as EBOM_BUNDLE
from domains.registry import GraphId
from domains.routing.bundle import BUNDLE as ROUTING_BUNDLE
from domains.sourcing.bundle import BUNDLE as SOURCING_BUNDLE

DOMAIN_BUNDLES: dict[GraphId, DomainBundle] = {
    "ebom": EBOM_BUNDLE,
    "routing": ROUTING_BUNDLE,
    "sourcing": SOURCING_BUNDLE,
}


def get_domain_bundle(graph_id: GraphId) -> DomainBundle:
    return DOMAIN_BUNDLES[graph_id]


__all__ = ["DOMAIN_BUNDLES", "get_domain_bundle"]
