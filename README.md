# SPK Peremajaan Armada PO Bus (AHP–TOPSIS) · versi Streamlit

Data seluruhnya **simulasi** (seed 42). Lihat halaman *Tentang Sistem* di aplikasi dan `data/parameter.json`.

## Menjalankan

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Buka http://localhost:8501. Uji perhitungan: `python -m pytest -q`.

## Mengganti banner

Taruh gambar Anda di `assets/` dengan nama `banner.png` (atau `.jpg`, `.jpeg`, `.webp`) dan timpa
file contoh. Ukuran yang disarankan: rasio sekitar 6:1 hingga 8:1, misalnya 1800 × 300 px. Di desktop
banner dipotong (crop) setinggi 150 px dari sisi kiri-tengah, jadi taruh teks/logo di bagian kiri.
Tinggi bisa diubah lewat `BANNER_TINGGI_PX` di `spk/ui.py`. Hapus semua file banner jika tidak ingin
menampilkan banner.

## Struktur

| Lokasi | Isi |
|---|---|
| `spk/engine.py` | AHP (eigenvector utama, power iteration, CR) dan TOPSIS. Fungsi murni. |
| `spk/generator.py` | Generator data ber-seed. Setiap unit punya aliran acak sendiri dan mengambil jumlah angka acak yang sama tiap hari. |
| `spk/scenario.py` | Event bertanggal → modifier per unit → unit terdampak disimulasikan ulang. Data aktual tidak diubah. |
| `spk/metrics.py` | Agregasi log harian menjadi C1–C5, KPI, data bulanan. |
| `spk/keputusan.py` | Ranking, faktor dominan (porsi dalam D⁻²), pemilihan berdasarkan anggaran. |
| `spk/repository.py` | Satu-satunya pintu akses data dan state untuk halaman. |
| `views/` | Halaman Streamlit. |
| `data/parameter.json` | Parameter generator; nilai berstatus `asumsi` perlu diganti dengan nilai bersumber. |
| `data/state.json` | Dibuat otomatis: matriks AHP, skenario, riwayat. Hapus untuk kembali ke awal. |

## Catatan

- Ganti parameter di `data/parameter.json`, lalu jalankan ulang aplikasi; data dibangkitkan ulang otomatis.
  Setelah parameter diubah, angka berubah dan screenshot lama tidak lagi cocok.
- Angka versi ini **tidak sama** dengan versi React/Vite, karena generatornya berbeda (PRNG dan urutan
  pengambilan angka acak). Pakai salah satu sebagai acuan laporan.
- Streamlit membutuhkan server Python, jadi tidak bisa di-host di InfinityFree (PHP) atau Vercel.
  Untuk online, gunakan layanan yang menjalankan Python (misalnya Streamlit Community Cloud; periksa
  ketentuannya). Di layanan seperti itu `data/state.json` bisa hilang saat aplikasi dimulai ulang.
