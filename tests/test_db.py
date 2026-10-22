from smartcity import db


def test_ingest_is_idempotent(settings):
    first = db.ingest_csvs(settings)
    second = db.ingest_csvs(settings)
    assert first == second
    energy = db.read_frame(settings, "energy")
    assert not energy.duplicated(["zone", "timestamp"]).any()


def test_anomaly_scores_cover_every_usable_reading(settings):
    with db.session(settings) as conn:
        scored = conn.execute("SELECT COUNT(*), SUM(flagged) FROM energy_anomalies").fetchone()
    assert scored[0] > 5000 and 0 < scored[1] < scored[0] * 0.1
