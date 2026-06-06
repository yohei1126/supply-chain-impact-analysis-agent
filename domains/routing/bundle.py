from domains.bundle import DomainBundle

BUNDLE = DomainBundle(
    graph_id="routing",
    name="Manufacturing routing",
    owner_team="manufacturing",
    source_systems=("MES", "ERP_PP"),
    nodes=frozenset({"Component", "Process", "Product"}),
    edges=frozenset({"INPUT_OF", "PRODUCED_BY"}),
    description="How products are built — processes, work centers, material at operations.",
)

__all__ = ["BUNDLE"]
