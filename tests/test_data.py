import hashlib

import numpy as np
import pandas as pd
import pytest

from spk import metrics, scenario
from spk.engine import ahp, topsis
from spk.generator import bangkitkan_semua, muat_parameter

P = muat_parameter()


@pytest.fixture(scope="module")
def data():
    return bangkitkan_semua(P)


def _hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()


def test_generator_deterministik(data):
    a2, _, l2 = bangkitkan_semua(P)
    assert _hash(data[0]) == _hash(a2) and _hash(data[2]) == _hash(l2)


def test_korelasi_umur(data):
    r = metrics.ringkasan_armada(data[0], data[2])
    normal = r[r["anomali"] == ""]
    assert normal["umur"].corr(normal["biaya_per_km"]) > 0.5
    assert normal["umur"].corr(normal["kerusakan_per_10rb"]) > 0.3


def test_anomali_ada(data):
    assert set(data[0]["anomali"]) >= {"Melewati batas usia regulasi", "Unit muda rawan rusak",
                                       "Unit tua baru di-overhaul"}


def test_skenario_kosong_identik(data):
    armada, _, log = data
    assert scenario.terapkan([], armada, log, P) is log


def test_skenario_tidak_mutasi_dan_deterministik(data):
    armada, _, log = data
    sebelum = _hash(log)
    ev = [{"id": "e1", "jenis": "lonjakan_kerusakan", "target": ["B05"],
           "parameter": {"pengali": 3}, "mulai": "2026-06-01"}]
    h1 = scenario.terapkan(ev, armada, log, P)
    h2 = scenario.terapkan(ev, armada, log, P)
    assert _hash(log) == sebelum
    assert _hash(h1) == _hash(h2)


def test_hari_sebelum_event_identik(data):
    armada, _, log = data
    ev = [{"id": "e1", "jenis": "lonjakan_kerusakan", "target": ["B05"],
           "parameter": {"pengali": 3}, "mulai": "2026-06-01"}]
    h = scenario.terapkan(ev, armada, log, P)
    batas = pd.Timestamp("2026-06-01")
    a = log[(log.unit_id == "B05") & (log.tanggal < batas)].reset_index(drop=True)
    b = h[(h.unit_id == "B05") & (h.tanggal < batas)].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    assert h[h.unit_id == "B05"].kerusakan.sum() > log[log.unit_id == "B05"].kerusakan.sum()


def test_event_di_luar_periode_tanpa_efek(data):
    armada, _, log = data
    ev = [{"id": "e1", "jenis": "lonjakan_kerusakan", "target": ["B05"],
           "parameter": {"pengali": 3}, "mulai": "2027-01-01"}]
    h = scenario.terapkan(ev, armada, log, P)
    pd.testing.assert_frame_equal(
        h.sort_values(["unit_id", "tanggal"]).reset_index(drop=True),
        log.sort_values(["unit_id", "tanggal"]).reset_index(drop=True))


def test_kenaikan_merata_skor_identik(data):
    armada, _, log = data
    w = np.array([0.1367, 0.2444, 0.4030, 0.0791, 0.1367])
    ev = [{"id": "e1", "jenis": "kenaikan_merata", "target": [], "parameter": {"persen": 20},
           "mulai": P["periode"]["mulai"]}]
    r0 = metrics.ringkasan_armada(armada, log)
    r1 = metrics.ringkasan_armada(armada, scenario.terapkan(ev, armada, log, P))
    s0 = topsis(metrics.matriks_keputusan(r0)[1], w, metrics.BENEFIT).skor
    s1 = topsis(metrics.matriks_keputusan(r1)[1], w, metrics.BENEFIT).skor
    np.testing.assert_allclose(s0, s1, atol=1e-9)


def test_unit_keluar(data):
    armada, _, log = data
    ev = [{"id": "e1", "jenis": "unit_keluar", "target": ["B03"], "mulai": "2026-03-01"}]
    h = scenario.terapkan(ev, armada, log, P)
    r = metrics.ringkasan_armada(armada, h, scenario.unit_keluar(ev))
    alt, _ = metrics.matriks_keputusan(r)
    assert "B03" not in set(alt["id"])
    assert h[h.unit_id == "B03"].tanggal.max() < pd.Timestamp("2026-03-01")


def test_kpi_konsisten_dengan_c2(data):
    armada, _, log = data
    r = metrics.ringkasan_armada(armada, log)
    k = metrics.kpi(r, 25)
    assert k["biaya_per_km"] == pytest.approx((r.biaya_per_km * r.km).sum() / r.km.sum())
