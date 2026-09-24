from evidence_graph.auth import CAN_READ, CAN_RUN, Principal, Role
from evidence_graph.auth.rbac import can_read, can_run


def test_viewer_reads_but_does_not_run():
    viewer = Principal(user_id="v", role=Role.VIEWER)

    assert can_read(viewer)
    assert not can_run(viewer)


def test_researcher_and_admin_can_run():
    assert can_run(Principal(user_id="r", role=Role.RESEARCHER))
    assert can_run(Principal(user_id="a", role=Role.ADMIN))
    assert Role.VIEWER not in CAN_RUN
    assert CAN_READ == frozenset(Role)
