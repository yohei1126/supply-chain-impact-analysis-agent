from domains.bundle import DomainBundle

BUNDLE = DomainBundle(
    graph_id="sourcing",
    name="Supply and sourcing",
    owner_team="procurement",
    source_systems=("SRM", "ERP_MM"),
    nodes=frozenset({"Component", "Supplier"}),
    edges=frozenset({"SUPPLIED_BY"}),
    description="Who supplies which components — lead time and supplier risk context.",
)

__all__ = ["BUNDLE"]
