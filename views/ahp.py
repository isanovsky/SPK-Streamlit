import numpy as np
import pandas as pd
import streamlit as st

from spk import charts, metrics
from spk import repository as repo
from spk import ui
from spk.engine import ahp

ui.kepala("Pembobotan AHP", "Bandingkan kepentingan setiap pasangan kriteria. Bobot dihitung dari "
          "eigenvector utama matriks perbandingan.")

K = metrics.KRITERIA
n = len(K)
nama = [f'{k["kode"]} {k["nama"]}' for k in K]
SKALA = {1: "Sama penting", 2: "Antara sama dan sedikit lebih", 3: "Sedikit lebih penting",
         4: "Antara sedikit dan lebih", 5: "Lebih penting", 6: "Antara lebih dan sangat",
         7: "Sangat lebih penting", 8: "Antara sangat dan mutlak", 9: "Mutlak lebih penting"}
opsi = list(range(8, -9, -1))  # ujung kiri: kriteria kiri lebih penting; 0: sama


def ke_nilai(o: int) -> float:
    return 1.0 if o == 0 else (o + 1 if o > 0 else 1.0 / (-o + 1))


def dari_nilai(v: float) -> int:
    return 0 if abs(v - 1) < 1e-9 else (int(round(v)) - 1 if v > 1 else -(int(round(1 / v)) - 1))


tersimpan = repo.matriks_ahp()
if "ahp_kerja" not in st.session_state:
    st.session_state["ahp_kerja"] = tersimpan.copy()
kerja = st.session_state["ahp_kerja"]

kiri, kanan = st.columns([3, 2], gap="large")
with kiri:
    st.markdown("**Perbandingan berpasangan** · geser ke arah kriteria yang lebih penting")
    baru = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            awal = dari_nilai(kerja[i, j])

            def label(o, i=i, j=j):
                if o == 0:
                    return "Sama penting (1)"
                lebih = K[i]["kode"] if o > 0 else K[j]["kode"]
                v = abs(o) + 1
                return f"{lebih}: {SKALA[v].lower()} ({v})"

            o = st.select_slider(f"{nama[i]}  vs  {nama[j]}", options=opsi, value=awal,
                                 format_func=label, key=f"ahp_{i}_{j}")
            baru[i, j], baru[j, i] = ke_nilai(o), 1 / ke_nilai(o)
    st.session_state["ahp_kerja"] = baru

h = ahp(baru)
with kanan:
    st.plotly_chart(charts.bobot(nama, h.bobot), width="stretch", config={"displayModeBar": False})
    st.markdown(f"| λ maks | CI | CR |\n|---:|---:|---:|\n| {ui.angka(h.lambda_max, 4)} | "
                f"{ui.angka(h.ci, 4)} | {ui.angka(h.cr, 4)} |")
    if h.konsisten:
        st.success(f"Konsisten: CR {ui.angka(h.cr, 4)} ≤ 0,10.", icon=":material/check_circle:")
    else:
        i, j = h.pasangan_terburuk
        saran = h.bobot[i] / h.bobot[j]
        st.error(f"Tidak konsisten: CR {ui.angka(h.cr, 4)} > 0,10. Pasangan paling menyimpang: "
                 f"{K[i]['kode']} vs {K[j]['kode']} (diisi {ui.angka(baru[i, j], 2)}, "
                 f"bobot menyiratkan sekitar {ui.angka(saran, 2)}).", icon=":material/error:")
    berubah = not np.allclose(baru, tersimpan)
    s1, s2 = st.columns(2)
    if s1.button("Simpan bobot", type="primary", disabled=not (berubah and h.konsisten), width="stretch"):
        repo.simpan_matriks_ahp(baru)
        st.toast("Matriks AHP disimpan.")
        st.rerun()
    if s2.button("Kembalikan ke awal", width="stretch"):
        st.session_state["ahp_kerja"] = np.array(repo.MATRIKS_AWAL, dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                st.session_state.pop(f"ahp_{i}_{j}", None)
        st.rerun()
    if berubah:
        st.caption("Ada perubahan yang belum disimpan. Halaman TOPSIS memakai bobot yang tersimpan.")
    if not h.konsisten:
        st.caption("Bobot hanya bisa disimpan jika matriks konsisten.")

with st.expander("Langkah perhitungan"):
    kode = [k["kode"] for k in K]
    st.markdown("**1. Matriks perbandingan A**")
    st.dataframe(pd.DataFrame(baru, index=kode, columns=kode).style.format(ui.fmt(4)), width="stretch")
    aw = baru @ h.bobot
    st.markdown(f"**2. Eigenvector utama** (power iteration, {h.iterasi} iterasi): w dinormalisasi "
                "sehingga jumlahnya 1.")
    st.markdown("**3. Konsistensi**: λmax = rata-rata (A·w)ᵢ / wᵢ; CI = (λmax − n)/(n − 1); CR = CI/RI, "
                f"dengan RI(n={n}) = {ui.angka(h.ri, 2)}.")
    st.dataframe(pd.DataFrame({"w": h.bobot, "(A·w)": aw, "(A·w)/w": aw / h.bobot}, index=kode)
                 .style.format(ui.fmt(4)), width="stretch")

ui.kaki()
