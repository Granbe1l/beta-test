# Project Delivery Monitor — PRD Addendum
## Engineering Governance, Quality Assurance & Token Efficiency

**Tanggal:** 26 November 2026 (WIB)  
**Revisi:** GOV-1.1  
**Cakupan:** Ketentuan permanen proses pengembangan, integrasi, QA, pemeliharaan, dan handover.  
**Status:** Disusun atas permintaan pemilik proyek untuk ditambahkan ke PRD aktif; belum direkonsiliasi dengan salinan PRD lokal terbaru. Tidak merupakan izin implementasi produk, instalasi alat, perubahan gate, push, merge, atau deployment.

## 1. Tujuan dan kedudukan

Hasil harus profesional bagi HR nonteknis, berguna bagi Data Analyst, dapat ditelusuri oleh pengguna teknis, dan sesuai dengan PRD yang disetujui. Efisiensi token adalah sasaran proses, bukan alasan menurunkan kualitas, akurasi data, keamanan, aksesibilitas, atau cakupan pengujian. Ketentuan ini bersifat aditif: seluruh persyaratan produk, ADR, kontrak data, acceptance criteria, dan gate yang berlaku tetap dipertahankan.

PRD aktif menetapkan tujuan, persyaratan dan batasan produk; `AGENTS.md` menerjemahkannya menjadi instruksi operasional agent dan merujuk lokasi PRD serta addendum ini. Baseline main yang dipin menjadi acuan kesetaraan perilaku dan data sesuai ruang lingkup integrasi yang disetujui. Jika terdapat konflik, jangan memilih atau mengubah definisi secara sepihak: catat konflik, bukti dan opsi, lalu minta keputusan pemilik. Addendum ini tidak mengesampingkan persyaratan yang lebih ketat.

## 2. Persyaratan permanen

| ID | Persyaratan wajib | Acceptance criteria / bukti minimum |
|---|---|---|
| GOV-01 | Kepatuhan PRD dan baseline. Sebelum perubahan, identifikasi PRD aktif, baseline SHA, branch/worktree, ADR dan gate relevan; petakan ruang lingkup terhadap requirement yang berlaku. | Pemetaan requirement → perubahan → tes/bukti; diff terhadap baseline yang tepat; konflik dilaporkan, bukan diselesaikan diam-diam. |
| GOV-02 | Efisiensi konteks. Baca dokumen sumber, bagian kode dan dependensi yang relevan terlebih dahulu; perluas pembacaan jika bukti kurang. Gunakan pencarian terarah, filter bawaan terminal, ringkasan keluaran rutin dan simpan bukti mentah; tidak memerlukan hook atau alat kompresi tambahan. | Tidak ada pengulangan pembacaan/audit tanpa alasan; bukti penting tetap dapat ditelusuri. Jangan mengklaim persentase hemat token tanpa pengukuran yang relevan. |
| GOV-03 | Penggunaan alat selektif. Pilih tool/skill sesuai tugas, cek ketersediaan, kompatibilitas, izin dan risiko konflik. Fallback manual yang ekuivalen diperbolehkan. | Alat yang dipakai dan alasan tercatat; tidak ada instalasi, pengiriman data ke provider baru atau dependency runtime tanpa otorisasi yang sesuai. |
| GOV-04 | Audit berbasis risiko. Prioritaskan kebenaran data, keamanan, kontrak, fungsi dan regresi sebelum polish visual; selesaikan gate sesuai aturan aktif. | Daftar temuan, severity, bukti, tindakan dan status. Audit ulang jika baseline/area terdampak, ada risiko baru, atau bukti tidak lagi valid. Jumlah putaran bukan indikator kelulusan. |
| GOV-05 | Kualitas desain dan kode. Hindari AI slop, dekorasi berlebih, duplikasi, abstraksi prematur dan perubahan kosmetik tanpa manfaat; pertahankan desain yang disetujui. | Diff terarah; review keterbacaan, hierarki, konsistensi, responsivitas, aksesibilitas dan performa yang relevan; tidak menambah fitur di luar scope. |
| GOV-06 | Integritas data dan perilaku. Pertahankan cohort tetap 50 repository, definisi Verified, KPI, denominator, periode, aturan temuan, freshness, kontrak data, pipeline dan logika bisnis yang berlaku. | Uji kesetaraan dengan sumber Python/main yang disetujui, termasuk cakupan parsial, data kosong, stale dan error; tidak ada perubahan semantik atau dataset tanpa izin. |
| GOV-07 | QA dan regresi. Jalankan pengujian existing yang diwajibkan gate serta tes terarah untuk perubahan. TDD untuk perubahan logika/fungsi bila relevan. | Perintah, exit status, jumlah pass/fail/skip, SHA/lingkungan dan bukti. Pengujian UI mencakup halaman, state, tema, bahasa, viewport, keyboard dan interaksi terdampak sesuai PRD; simulasi bukan bukti runtime produksi. |
| GOV-08 | Checkpoint dan kelanjutan. Catat pekerjaan yang selesai, pending, konflik, dan bukti valid sebelum pergantian agent/sesi atau batas kuota. | Catatan checkpoint berisi ref/SHA, status worktree, requirement/gate, perubahan, pengujian, risiko dan langkah berikutnya. Jangan membuat commit/push otomatis bila belum diizinkan. |
| GOV-09 | Kejujuran bukti. Jangan mengarang atau memanipulasi angka, timestamp, status Verified, hasil tes, skor UX, screenshot maupun status gate. | Status PASS/FAIL/NOT TESTED (atau status resmi yang berlaku) dapat ditelusuri; keterbatasan, skip dan kegagalan dilaporkan. Fixture diberi label dan tidak disajikan sebagai data aktual. |
| GOV-10 | Kontrol perubahan. Jangan merge, push, deploy, mengubah scope, dataset, konfigurasi produksi, scheduler, Cloudflare atau resource berbayar di luar izin yang diberikan. | Daftar tindakan yang membutuhkan izin; tidak ada perubahan di luar scope. Gunakan branch/worktree yang sesuai dan jangan menjalankan dua agent penulis pada worktree sama secara bersamaan. |
| GOV-11 | Portabilitas. Persyaratan tidak bergantung pada satu model, vendor atau plugin. Handover harus dapat dipakai Codex, Antigravity atau agent lain. | PRD, ADR, kontrak, acceptance criteria dan bukti tersedia dalam format teks/artefak yang dapat diakses; pergantian alat tidak mengubah standar kelulusan. |
| GOV-12 | Keamanan dan privasi. Token, secrets, data privat, konfigurasi sensitif, dan credential tidak boleh masuk prompt, log, screenshot, commit, artefak publik atau provider eksternal tanpa otorisasi. | Review diff/artefak untuk secrets, izin minimal, validasi akses publik sesuai kontrak; log mentah sensitif diperiksa secara lokal dan disanitasi sebelum dibagikan. |

## 3. Matriks penggunaan alat (opsional, bukan dependency produk)

**Keputusan pemilik (GOV-1.1):** hanya Vercel yang dipilih sebagai tambahan alat pengembangan. Pertahankan alat yang sudah tersedia dan disetujui; jangan menginstal atau mengaktifkan RTK, OpenSpec, Playwright CLI tambahan, Serena, atau alat baru lain tanpa persetujuan baru. Jika integrasi RTK global telah terdaftar, penonaktifannya dilakukan terpisah oleh pemilik; addendum ini tidak mengubah konfigurasi lokal. Playwright/test suite existing tetap digunakan sesuai gate. Status instalasi dan kompatibilitas alat wajib diperiksa, bukan diasumsikan.

| Alat | Gunakan ketika | Batasan / fallback |
|---|---|---|
| Graphify | Pemetaan dependensi, impact analysis, penelusuran lintas modul | Verifikasi indeks sesuai ref/commit; cek kode sumber jika hasil tidak lengkap atau stale. |
| Superpowers | Perencanaan perubahan kompleks, debugging sistematis dan TDD | Gunakan workflow/gate yang ada; jangan menggandakan audit atau dokumen tanpa manfaat. |
| Ponytail | Menilai kesederhanaan implementasi dan mencegah overengineering | Jangan menghapus validasi, error handling, aksesibilitas, dokumentasi atau tes yang diperlukan. |
| UI/UX Pro Max | Desain dan konsistensi komponen | Ikuti desain, bahasa, dan ruang lingkup yang disetujui; jangan mengganti sistem desain secara sepihak. |
| Impeccable | Kritik visual, anti-AI-slop dan polish | Perubahan visual tetap harus sesuai PRD, terukur manfaatnya dan lolos regresi. |
| Playwright / test suite existing | QA browser dan bukti render/interaksi | Gunakan alat pengujian yang sudah tersedia; jangan memasang Playwright CLI tambahan. Tes wajib dan verifikasi deployment aktual tetap berlaku. |
| Vercel (plugin/skill resmi yang dipilih pemilik) | Evaluasi kompatibilitas dan kesiapan deployment Vercel | Gunakan jika tersedia; hindari duplikasi plugin. Sesuaikan dengan arsitektur/ADR aktual; tidak ada migrasi framework, perubahan runtime atau deploy otomatis. |

Tidak perlu mengaktifkan semua alat bersamaan. Alat yang tidak tersedia atau belum teruji tidak menghalangi penyelesaian jika metode ekuivalen memenuhi acceptance criteria. Jangan memasang plugin atau mengubah konfigurasi agent sebagai konsekuensi otomatis addendum ini. Agent pengembangan bukan fitur AI/LLM dalam aplikasi.

## 4. Prosedur operasional dan efisiensi token

1. **Preflight:** baca PRD aktif, `AGENTS.md`, checkpoint terbaru, ADR dan aturan gate terkait; verifikasi branch/worktree dan baseline. Identifikasi persyaratan terdampak dan bukti existing.
2. **Rencana terarah:** tentukan perubahan minimal yang memenuhi requirement, risiko, tes wajib dan tindakan yang perlu persetujuan. Gunakan pencarian simbol/dependensi sebelum membaca file besar. Gunakan Git diff, pencarian bawaan atau Graphify jika tersedia; pelihara pemetaan requirement dan tes dalam PRD/ledger existing tanpa OpenSpec.
3. **Implementasi:** hanya kerjakan scope yang disetujui. Aktifkan skill berdasarkan kebutuhan; hindari redesign, refactor atau perubahan data yang tidak diminta.
4. **Verifikasi:** jalankan tes terarah dan seluruh gate wajib; periksa output mentah untuk kegagalan atau temuan kritis. Bukti lama boleh dirujuk hanya bila masih relevan terhadap kandidat, baseline, konfigurasi, lingkungan dan area terdampak; tidak menggantikan tes yang diwajibkan gate pada commit kandidat.
5. **Review:** cek diff dan kontrak terhadap baseline, traceability requirement, hasil QA, risiko dan keterbatasan. Perbaiki penyebab, bukan sekadar skor atau gejala. Jangan menyatakan gate lulus apabila belum ada bukti yang dipersyaratkan.
6. **Checkpoint:** simpan ringkasan ringkas dan lokasi bukti; jangan menyalin seluruh log atau transkrip ke konteks baru. Lanjutkan gate yang belum selesai tanpa mengulang gate lulus yang masih valid; ikuti aturan revalidasi gate aktif.

### Format laporan minimum

- Ref/commit baseline dan kandidat, branch/worktree, gate dan requirement ID.
- File yang berubah, tujuan, ringkasan diff dan hasil pemeriksaan batas scope.
- Tes: perintah, exit status, pass/fail/skip, lingkungan, lokasi bukti, batas cakupan.
- Temuan, risiko, konflik, status acceptance criteria, keputusan/izin yang masih diperlukan.
- Checkpoint dan langkah selanjutnya. Tidak ada klaim penghematan token atau kualitas tanpa dasar.

## 5. Penerapan pada PRD dan AGENTS.md

Tambahkan bagian ini secara aditif ke PRD aktif (atau simpan sebagai lampiran normatif yang dirujuk eksplisit oleh PRD). Pertahankan nomor/ID requirement lama, hindari duplikasi aturan, dan jangan mengubah persyaratan produk maupun status gate. Tambahkan referensi operasional singkat pada `AGENTS.md` sesuai cakupan yang benar. Jika salinan PRD aktif tidak dapat diidentifikasi atau ketentuan bertentangan, jangan menimpa dokumen: laporkan blocker untuk rekonsiliasi.

**Acceptance criteria perubahan dokumentasi:** diff hanya memuat PRD/lampiran dan instruksi agent yang diizinkan; seluruh GOV-01–GOV-12 tersedia; persyaratan lama, ADR, gate, baseline, dataset dan kode tetap utuh; rujukan dapat ditemukan; tidak ada instalasi, push, merge atau deploy. Verifikasi ini harus dilakukan pada worktree aktual sebelum menyatakan pembaruan PRD terintegrasi.

## 6. Riwayat revisi

- GOV-1.0: menetapkan GOV-01–GOV-12 dan matriks alat opsional.
- GOV-1.1: hanya Vercel sebagai alat tambahan pilihan pemilik; menghapus RTK, OpenSpec, Serena dan Playwright CLI tambahan dari matriks penggunaan; menegaskan fallback tanpa alat baru dan mempertahankan Playwright/test suite existing. Seluruh GOV-01–GOV-12, prosedur QA, kontrol perubahan, dan batasan produk tetap berlaku.
