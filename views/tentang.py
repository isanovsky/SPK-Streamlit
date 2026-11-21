import pandas as pd
import streamlit as st

from spk import metrics
from spk import repository as repo
from spk import ui

ui.kepala("Tentang Sistem", "Metode, kriteria, dan cara data simulasi dibangkitkan.")

p = repo.parameter()
st.markdown("""
**Pertanyaan keputusan.** Dari seluruh armada bus AKAP, unit mana yang paling mendesak diremajakan
pada periode anggaran berikutnya?

**Metode.** AHP menentukan bobot kriteria dari perbandingan berpasangan (eigenvector utama, uji
konsistensi CR ≤ 0,10). TOPSIS meranking unit berdasarkan jarak ke solusi ideal positif dan negatif.
Unit yang melewati batas usia regulasi didahulukan dalam rekomendasi, terlepas dari skornya.
""")

st.subheader("Kriteria")
st.dataframe(pd.DataFrame([{"Kode": k["kode"], "Kriteria": k["nama"], "Satuan": k["satuan"],
                            "Tipe TOPSIS": "Benefit" if k["benefit"] else "Cost"} for k in metrics.KRITERIA]),
             hide_index=True, width="stretch")

st.subheader("Data simulasi")
st.markdown(f"""
Seluruh data operasional adalah **simulasi** dari generator ber-seed (seed {p['seed']}), untuk periode
{p['periode']['mulai']} sampai {p['periode']['selesai']}. Generator yang sama dengan parameter yang sama
selalu menghasilkan data yang identik.

- Kerusakan: Poisson dengan laju λ₀ · e^(k · umur) per 10.000 km.
- Biaya perawatan per km: b₀ · e^(k · umur) · ε, dengan ε berdistribusi log-normal.
- Efisiensi BBM: e₀ − d · umur + noise normal.
- Ketersediaan: turunan dari hari rusak dan hari servis (berkorelasi dengan C3).
- Anomali yang sengaja ditanam: unit muda yang rawan rusak, unit tua yang baru di-overhaul, dan unit
  yang melewati batas usia.

Keterbatasan: C1 berkorelasi dengan C2–C5, sehingga aspek penuaan efektif berbobot lebih besar dari bobot
nominal C1. TOPSIS tidak mengoreksi korelasi antarkriteria.
""")

baris = []
for kunci, isi in p.items():
    if isinstance(isi, dict) and "status" in isi:
        baris.append({"Parameter": kunci, "Status": isi["status"], "Sumber": isi.get("sumber") or "-",
                      "Catatan": isi.get("catatan", "")})
for kelas, isi in p["kelas"].items():
    baris.append({"Parameter": f"kelas.{kelas}", "Status": isi["status"], "Sumber": isi.get("sumber") or "-",
                  "Catatan": "kapasitas dan biaya peremajaan"})
st.markdown("**Status parameter** (asumsi = belum bersumber)")
st.dataframe(pd.DataFrame(baris), hide_index=True, width="stretch")

ui.kaki()
