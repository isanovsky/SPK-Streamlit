from datetime import datetime

import streamlit as st

from spk import metrics
from spk import repository as repo
from spk import ui

ui.kepala("Riwayat Keputusan", "Keputusan yang disimpan dari halaman Rekomendasi.")

data = repo.riwayat()
if not data:
    st.info("Belum ada keputusan tersimpan. Simpan keputusan dari halaman Rekomendasi.", icon=":material/history:")
    st.page_link("views/rekomendasi.py", label="Buka Rekomendasi", icon=":material/arrow_forward:")
for k in data:
    with st.container(border=True):
        a, b = st.columns([5, 1], vertical_alignment="top")
        waktu = datetime.fromisoformat(k["waktu"])
        a.markdown(f"**{k.get('catatan') or 'Keputusan tanpa catatan'}**  \n"
                   f":gray[{ui.tanggal(waktu)} {waktu:%H:%M} · anggaran {ui.rp_singkat(k['anggaran'])} · "
                   f"total {ui.rp_singkat(k['total_biaya'])} · {len(k['unit_terpilih'])} unit"
                   f"{' · skenario: ' + k['skenario'] if k.get('skenario') else ''}"
                   f"{' · bobot what-if' if k.get('bobot_whatif') else ''}]")
        a.markdown("Unit: " + ", ".join(k["unit_terpilih"]))
        a.caption("Bobot: " + " · ".join(f'{kr["kode"]} {ui.angka(v, 4)}'
                                          for kr, v in zip(metrics.KRITERIA, k["bobot"])))
        if b.button("Hapus", key=f"hapus_{k['id']}", width="stretch"):
            repo.hapus_keputusan(k["id"])
            st.rerun()

st.divider()
st.subheader("Data aplikasi")
st.caption("Penilaian AHP, skenario, dan riwayat disimpan di data/state.json pada komputer ini. "
           "Ekspor sebelum presentasi di komputer lain.")
a, b, c = st.columns(3)
a.download_button("Ekspor JSON", repo.ekspor_state(), file_name="spk_state.json", mime="application/json",
                  width="stretch")
with b:
    berkas = st.file_uploader("Impor JSON", type="json", label_visibility="collapsed")
    if berkas is not None and st.button("Terapkan impor", width="stretch"):
        try:
            repo.impor_state(berkas.read().decode("utf-8"))
            st.session_state.pop("sk_kerja", None)
            st.session_state.pop("ahp_kerja", None)
            st.toast("Data diimpor.")
            st.rerun()
        except (ValueError, UnicodeDecodeError) as e:
            st.error(f"Impor gagal: {e}")
with c:
    if st.button("Reset ke kondisi awal", width="stretch"):
        st.session_state["konfirmasi_reset"] = True
    if st.session_state.get("konfirmasi_reset"):
        st.warning("Semua skenario, matriks AHP yang diubah, dan riwayat akan dihapus. Data simulasi dasar tetap.")
        y, n = st.columns(2)
        if y.button("Ya, reset", type="primary", width="stretch"):
            repo.reset_state()
            for kunci in ("sk_kerja", "ahp_kerja", "konfirmasi_reset"):
                st.session_state.pop(kunci, None)
            st.rerun()
        if n.button("Batal", width="stretch"):
            st.session_state.pop("konfirmasi_reset")
            st.rerun()

ui.kaki()
