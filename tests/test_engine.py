import numpy as np
import pytest

from spk.engine import ahp, matriks_dari_segitiga_atas, topsis

A = np.array([[1, 1/2, 1/3, 2, 1], [2, 1, 1/2, 3, 2], [3, 2, 1, 4, 3],
              [1/2, 1/3, 1/4, 1, 1/2], [1, 1/2, 1/3, 2, 1]])
X = np.array([[18, 1450, 2.6, 3.0, 84], [7, 620, 0.6, 3.6, 96], [12, 980, 1.3, 3.2, 92],
              [21, 1700, 2.1, 2.7, 91], [15, 1100, 1.9, 3.1, 90]], float)
BEN = np.array([1, 1, 1, 0, 0], bool)


def test_ahp_contoh_rencana():
    h = ahp(A)
    np.testing.assert_allclose(h.bobot, [0.1367, 0.2444, 0.4030, 0.0791, 0.1367], atol=1e-4)
    assert h.lambda_max == pytest.approx(5.0331, abs=1e-4)
    assert h.ci == pytest.approx(0.0083, abs=1e-4)
    assert h.cr == pytest.approx(0.0074, abs=1e-4)
    assert h.konsisten


def test_ahp_sama_dengan_numpy_eig():
    vals, vecs = np.linalg.eig(A)
    w = np.abs(vecs[:, np.argmax(vals.real)].real)
    np.testing.assert_allclose(ahp(A).bobot, w / w.sum(), atol=1e-8)


def test_ahp_konsisten_sempurna():
    w = np.array([0.5, 0.3, 0.2])
    h = ahp(w[:, None] / w[None, :])
    np.testing.assert_allclose(h.bobot, w, atol=1e-9)
    assert h.cr == pytest.approx(0.0, abs=1e-9)


def test_ahp_tolak_tidak_resiprokal():
    B = A.copy()
    B[0, 1] = 3
    with pytest.raises(ValueError):
        ahp(B)


def test_segitiga_atas():
    m = matriks_dari_segitiga_atas(3, {(0, 1): 3, (0, 2): 5, (1, 2): 2})
    assert m[1, 0] == pytest.approx(1 / 3) and m[2, 1] == pytest.approx(0.5)


def test_topsis_contoh_rencana():
    h = topsis(X, ahp(A).bobot, BEN)
    np.testing.assert_allclose(h.d_pos, [0.0255, 0.2261, 0.1475, 0.0493, 0.0905], atol=1e-4)
    np.testing.assert_allclose(h.d_neg, [0.2147, 0.0, 0.0786, 0.1848, 0.1385], atol=1e-4)
    np.testing.assert_allclose(h.skor, [0.8940, 0.0, 0.3476, 0.7893, 0.6050], atol=1e-4)
    assert h.peringkat.tolist() == [1, 5, 4, 2, 3]


def test_topsis_urutan_alternatif_tidak_berpengaruh():
    w = ahp(A).bobot
    perm = np.array([3, 0, 4, 2, 1])
    np.testing.assert_allclose(topsis(X[perm], w, BEN).skor, topsis(X, w, BEN).skor[perm], atol=1e-12)


def test_topsis_kenaikan_merata_tidak_mengubah_skor():
    w = ahp(A).bobot
    Y = X.copy()
    Y[:, 1] *= 1.2
    np.testing.assert_allclose(topsis(Y, w, BEN).skor, topsis(X, w, BEN).skor, atol=1e-9)


def test_topsis_kolom_nol():
    Y = X.copy()
    Y[:, 2] = 0
    with pytest.raises(ValueError):
        topsis(Y, ahp(A).bobot, BEN)
