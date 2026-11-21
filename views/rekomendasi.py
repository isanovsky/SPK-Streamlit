import numpy as np
import streamlit as st

from spk import charts, keputusan, metrics
from spk import repository as repo
from spk import ui
from spk.engine import ahp

ui.kepala("Rekomendasi Peremajaan", "Unit dipilih menurut ranking TOPSIS sampai anggaran habis. "
          "Unit yang melewati batas usia regulasi didahulukan.")

p = repo.parameter()
batas = repo.batas_usia()
w_ahp = ahp(repo.matriks_ahp()).bobot
K = metrics.KRITERIA
nama = [f'{k["kode"]} {k["nama"]}' for k in K]

ringkas = st.container()
kiri, kanan = st.columns([1, 2], gap="large")
with kiri:
    with st.container(border=True):
        st.markdown("**Anggaran**")
        anggaran = st.number_input("Anggaran peremajaan (Rp)", min_value=0, value=8_000_000_000,
                                   step=500_000_000, format="%d")
        st.caption(f"= {ui.rp(anggaran)}")
        biaya_kelas = {}
        for kelas, d in p["kelas"].items():
            biaya_kelas[kelas] = st.number_input(f"Estimasi biaya unit {kelas} (Rp)", min_value=0,
                                                 value=int(d["biaya_peremajaan"]), step=100_000_000,
                                                 format="%d", key=f"biaya_{kelas}")
        st.caption("Nilai awal dari parameter.json (asumsi).")

    with st.container(border=True):
        st.markdown("**What-if bobot**")
        pakai_whatif = st.toggle("Ubah bobot sementara", value=False,
                                 help="Tidak mengubah matriks AHP yang tersimpan.")
        w = w_ahp
        if pakai_whatif:
            mentah = np.array([st.slider(nama[i], 0.0, 1.0, float(round(w_ahp[i], 3)), 0.01, key=f"wi_{i}")
                               for i in range(len(K))])
            if mentah.sum() == 0:
                st.warning("Semua bobot nol; memakai bobot AHP.")
            else:
                w = mentah / mentah.sum()
                st.caption("Bobot dinormalisasi otomatis sehingga jumlahnya 1.")

rank, _ = keputusan.ranking(repo.ringkasan(), w)
hasil = keputusan.pilih_berdasarkan_anggaran(rank, anggaran, biaya_kelas, batas)
terpilih = hasil[hasil.terpilih]

with ringkas:
    a, b, c = st.columns(3)
    a.metric("Unit terpilih", ui.angka(len(terpilih)))
    b.metric("Total biaya", ui.rp_singkat(terpilih.biaya_peremajaan.sum()))
    c.metric("Sisa anggaran", ui.rp_singkat(anggaran - terpilih.biaya_peremajaan.sum()))

with kanan:
    wajib_tak_terdanai = hasil[hasil.wajib & ~hasil.terpilih]
    if len(wajib_tak_terdanai):
        st.error(f"{len(wajib_tak_terdanai)} unit wajib diremajakan (lewat batas usia) tidak tercakup "
                 "anggaran: " + ", ".join(wajib_tak_terdanai.id), icon=":material/error:")

    tampil = hasil[hasil.terpilih | (hasil.index < len(terpilih) + 5)].copy()
    tampil["keterangan"] = np.where(tampil.wajib, "Wajib (lewat batas usia)",
                                    np.where(tampil.terpilih, "Terpilih", "Di luar anggaran"))
    ui.tabel(tampil[["peringkat", "id", "kelas", "umur", "skor", "biaya_peremajaan", "keterangan", "alasan"]],
             {"skor": ui.fmt(4), "biaya_peremajaan": ui.fmt(0)},
             hide_index=True, width="stretch", column_config={
                     "peringkat": st.column_config.NumberColumn("Peringkat", format="%d", width="small"),
                     "id": st.column_config.TextColumn("Unit", width="small"),
                     "kelas": "Kelas",
                     "umur": st.column_config.NumberColumn("Umur (th)", format="%d"),
                     "skor": "Skor Cᵢ",
                     "biaya_peremajaan": "Estimasi biaya (Rp)",
                     "keterangan": st.column_config.TextColumn("Keterangan", width="medium"),
                     "alasan": st.column_config.TextColumn("Faktor dominan", width="medium"),
                 })
    st.caption("Ditampilkan: unit terpilih dan 5 unit berikutnya.")

    if pakai_whatif:
        st.plotly_chart(charts.bobot(nama, w, w_ahp), width="stretch", config={"displayModeBar": False})
        rank_ahp, _ = keputusan.ranking(repo.ringkasan(), w_ahp)
        bd = keputusan.bandingkan(rank_ahp, rank)
        geser = bd[bd.gerak != 0]
        st.markdown(f"**Perubahan peringkat akibat bobot what-if:** {len(geser)} unit bergeser.")
        if len(geser):
            ui.tabel(geser[["id", "peringkat_aktual", "peringkat_skenario", "gerak"]].head(10),
                     {"gerak": ui.fmt_gerak}, hide_index=True, width="stretch", column_config={
                             "id": "Unit", "peringkat_aktual": st.column_config.NumberColumn("Dengan bobot AHP", format="%d"),
                             "peringkat_skenario": st.column_config.NumberColumn("Dengan bobot what-if", format="%d"),
                             "gerak": "Gerak"})

    catatan = st.text_input("Catatan keputusan (opsional)", placeholder="mis. Pengajuan anggaran 2027")
    if st.button("Simpan keputusan ke riwayat", type="primary", disabled=len(terpilih) == 0):
        s = repo.skenario_aktif()
        repo.simpan_keputusan({
            "catatan": catatan, "anggaran": anggaran, "bobot": [round(float(x), 6) for x in w],
            "bobot_whatif": bool(pakai_whatif), "skenario": s["nama"] if s else None,
            "unit_terpilih": terpilih.id.tolist(), "total_biaya": float(terpilih.biaya_peremajaan.sum()),
        })
        st.toast("Keputusan disimpan ke riwayat.")

ui.kaki()
