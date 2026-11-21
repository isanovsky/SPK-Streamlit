"""AHP (eigenvector utama) dan TOPSIS sebagai fungsi murni."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

RI_SAATY = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


@dataclass(frozen=True)
class HasilAHP:
    bobot: np.ndarray
    lambda_max: float
    ci: float
    ri: float
    cr: float
    konsisten: bool
    pasangan_terburuk: tuple[int, int] | None
    iterasi: int


@dataclass(frozen=True)
class HasilTOPSIS:
    normal: np.ndarray
    terbobot: np.ndarray
    ideal_pos: np.ndarray
    ideal_neg: np.ndarray
    d_pos: np.ndarray
    d_neg: np.ndarray
    skor: np.ndarray
    peringkat: np.ndarray


def validasi_matriks(a: np.ndarray, tol: float = 1e-9) -> None:
    a = np.asarray(a, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("Matriks perbandingan harus persegi.")
    if not np.allclose(np.diag(a), 1.0, atol=tol):
        raise ValueError("Diagonal matriks perbandingan harus bernilai 1.")
    if np.any(a <= 0):
        raise ValueError("Semua elemen harus positif.")
    if not np.allclose(a * a.T, 1.0, atol=tol):
        raise ValueError("Matriks tidak resiprokal: a_ji harus sama dengan 1/a_ij.")
    if np.any(a > 9 + tol) or np.any(a < 1 / 9 - tol):
        raise ValueError("Nilai harus berada dalam skala Saaty 1/9 sampai 9.")


def ahp(a: np.ndarray, tol: float = 1e-10, maks_iterasi: int = 1000) -> HasilAHP:
    a = np.asarray(a, dtype=float)
    validasi_matriks(a)
    n = a.shape[0]
    w = np.full(n, 1.0 / n)
    iterasi = 0
    for iterasi in range(1, maks_iterasi + 1):
        baru = a @ w
        baru /= baru.sum()
        if np.max(np.abs(baru - w)) < tol:
            w = baru
            break
        w = baru
    lambda_max = float(np.mean((a @ w) / w))
    ri = RI_SAATY.get(n, 1.49)
    ci = (lambda_max - n) / (n - 1) if n > 2 else 0.0
    cr = ci / ri if ri > 0 else 0.0
    terburuk = None
    if n > 2:
        rasio = w[:, None] / w[None, :]
        deviasi = np.abs(np.log(a) - np.log(rasio))
        np.fill_diagonal(deviasi, -1)
        i, j = np.unravel_index(np.argmax(np.triu(deviasi, 1)), deviasi.shape)
        terburuk = (int(i), int(j))
    return HasilAHP(w, lambda_max, ci, ri, cr, cr <= 0.10, terburuk, iterasi)


def matriks_dari_segitiga_atas(n: int, nilai: dict[tuple[int, int], float]) -> np.ndarray:
    a = np.ones((n, n))
    for (i, j), v in nilai.items():
        a[i, j] = v
        a[j, i] = 1.0 / v
    return a


def topsis(x: np.ndarray, bobot: np.ndarray, benefit: np.ndarray) -> HasilTOPSIS:
    x = np.asarray(x, dtype=float)
    bobot = np.asarray(bobot, dtype=float)
    benefit = np.asarray(benefit, dtype=bool)
    if x.ndim != 2 or x.shape[1] != bobot.size or bobot.size != benefit.size:
        raise ValueError("Dimensi matriks keputusan, bobot, dan tipe kriteria tidak cocok.")
    pembagi = np.sqrt((x ** 2).sum(axis=0))
    if np.any(pembagi == 0):
        kolom = [int(k) + 1 for k in np.where(pembagi == 0)[0]]
        raise ValueError(f"Kriteria ke-{kolom} bernilai nol untuk semua alternatif.")
    r = x / pembagi
    v = r * bobot
    a_pos = np.where(benefit, v.max(axis=0), v.min(axis=0))
    a_neg = np.where(benefit, v.min(axis=0), v.max(axis=0))
    d_pos = np.sqrt(((v - a_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((v - a_neg) ** 2).sum(axis=1))
    total = d_pos + d_neg
    skor = np.divide(d_neg, total, out=np.zeros_like(d_neg), where=total > 0)
    urutan = np.argsort(-skor, kind="stable")
    peringkat = np.empty_like(urutan)
    peringkat[urutan] = np.arange(1, len(skor) + 1)
    return HasilTOPSIS(r, v, a_pos, a_neg, d_pos, d_neg, skor, peringkat)

