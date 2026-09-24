from evidence_graph.auth.jwt import Principal, Role

CAN_READ = frozenset({Role.VIEWER, Role.RESEARCHER, Role.ADMIN})
CAN_RUN = frozenset({Role.RESEARCHER, Role.ADMIN})


def can_read(principal: Principal) -> bool:
    return principal.role in CAN_READ


def can_run(principal: Principal) -> bool:
    return principal.role in CAN_RUN
