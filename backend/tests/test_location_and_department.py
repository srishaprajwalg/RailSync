import pytest
from backend.db.models import Asset, MaintenanceRequest, TrainMovement

def test_location_radius_query(db_session):
    target_km = 76.5
    radius_km = 5.0
    km_min = target_km - radius_km # 71.5
    km_max = target_km + radius_km # 81.5

    # Query assets intersecting [71.5, 81.5]
    assets_in_range = (
        db_session.query(Asset)
        .filter(
            Asset.corridor_id == "SBC-JTJ",
            Asset.start_chainage <= km_max,
            Asset.end_chainage >= km_min,
        )
        .all()
    )
    assert len(assets_in_range) > 0
    for a in assets_in_range:
        assert not (a.end_chainage < km_min or a.start_chainage > km_max)

    # Query maintenance requests intersecting [71.5, 81.5]
    requests_in_range = (
        db_session.query(MaintenanceRequest)
        .filter(
            MaintenanceRequest.corridor_id == "SBC-JTJ",
            MaintenanceRequest.start_chainage <= km_max,
            MaintenanceRequest.end_chainage >= km_min,
        )
        .all()
    )
    for r in requests_in_range:
        assert not (r.end_chainage < km_min or r.start_chainage > km_max)

def test_department_filtering(db_session):
    # Engineering
    eng_requests = db_session.query(MaintenanceRequest).filter_by(department="ENGINEERING").all()
    assert len(eng_requests) > 0
    for r in eng_requests:
        assert r.department == "ENGINEERING"

    # S&T
    st_requests = db_session.query(MaintenanceRequest).filter_by(department="S&T").all()
    assert len(st_requests) > 0
    for r in st_requests:
        assert r.department == "S&T"

    # Traction
    trac_requests = db_session.query(MaintenanceRequest).filter_by(department="TRACTION").all()
    assert len(trac_requests) > 0
    for r in trac_requests:
        assert r.department == "TRACTION"
