from domains.bundle import DomainBundle

BUNDLE = DomainBundle(
    graph_id="ebom",
    name="Product structure (EBOM)",
    owner_team="engineering",
    source_systems=("PLM",),
    nodes=frozenset({"Component", "Product"}),
    edges=frozenset({"USED_IN"}),
    description="Design intent — which components are used in which products.",
)

__all__ = ["BUNDLE"]
