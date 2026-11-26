# PRD & Runbook Integrasi Ulang — Project Delivery Monitor V9.5.52

**Versi:** 1.0 · 26 November 2026 WIB  
**Repository:** Granbe1l/beta-test  
**Branch kerja:** `codex/uiux-redesign`  
**Branch sumber kebenaran:** `main`  
**Status:** Rencana siap ditinjau; bukan bukti integrasi selesai, bukan izin merge atau deploy produksi.  
**Pemilik keputusan:** pemilik repository; pelaksana: engineering/Codex; reviewer: QA, Data Analyst, UI/UX, security. Peran dapat dijalankan orang yang sama tetapi tidak boleh diklaim sebagai review independen.

## 1. Ringkasan, tujuan, dan kriteria keberhasilan

Integrasi lama yang kurang memuaskan tidak dijadikan fondasi. Mulai dari kode main terbaru yang utuh, pertahankan pipeline dan metodologi, lalu port V9.5.52 sebagai acuan visual dan interaksi. Buat adapter yang tipis, dapat diuji, dan tidak memiliki definisi KPI kedua yang diam-diam berbeda. Hasil akhir harus profesional untuk HRD nonteknis, berguna bagi Data Analyst dan pengguna teknis, serta dapat dijelaskan saat interview.

| ID | Tujuan | Kriteria penerimaan |
|---|---|---|
| G01 | Baseline bersih | Main yang dibekukan merupakan ancestor kandidat; perubahan lokal lama dicadangkan; diff awal hanya PRD/dokumen yang disetujui. |
| G02 | Kesetiaan redesign | Enam rute, seluruh 14 perubahan wajib, C01/C02 dan AS02/03 sesuai keputusan audit; tidak ada fungsi desain yang hilang. |
| G03 | Integritas data | Model/domain, cohort, data aktual, denominator, waktu, CSV, temuan dan evidence sesuai main; semua beda dijelaskan, diuji dan disetujui bila menyangkut kontrak. |
| G04 | Keandalan | Suite existing dan seluruh regresi relevan lulus pada SHA kandidat yang tepat; tidak ada P0/P1 terbuka; failure dan rollback teruji. |
| G05 | UX | Target estimasi rata-rata >8,5/10; tidak ada dimensi inti <8,5 tanpa alasan/keputusan eksplisit. Nilai hanya pendukung, bukan pengganti tes atau bukti user study. |
| G06 | Keamanan | Read-only UI, tidak ada secret/private payload yang bocor, tidak ada writer kedua, tidak ada perubahan operasional tanpa izin. |
| G07 | Kesiapan serah terima | PR dengan diff terkontrol, CI hijau pada head/merge candidate terbaru, instruksi build dan rollback, approval eksplisit sebelum merge. |

**Bukan sasaran:** mengejar 10/10 atau 100 putaran tambahan tanpa hipotesis, membuat ulang backend, mengganti cohort, menambah chatbot, mengubah KPI untuk mempercantik grafik, menghapus batasan data, menambah metrik review approval yang tidak lengkap, mengubah refresh, membuat repo privat/deploy sekarang, mengganti token, atau rewrite framework demi tren.

## 2. Sumber, provenance dan keadaan saat PRD dibuat

- Referensi desain: `Project_Delivery_Monitor_V9_5_52_Audit_100.html`, 653.205 byte menurut metadata file, SHA-256 yang tercatat dalam laporan eksekusi: `c9f601eea42c318e97c8f10881a15572567e81e767e319175975b35dc8e1e2d2`. Verifikasi byte aktual sebelum digunakan.
- Referensi audit: `Laporan_Eksekusi_V9_5_52_100_Putaran.md`, khususnya §§6, 18–19, baseline V9.5.51 SHA-256 `ea35a8995e2e21354f55366b5c3e90e1bccdc884289c1613fd2d3cf46b0b173a`. Simpan arsip asli dan bukti mentah; jangan edit catatan tes lama.
- Sebelum commit PRD, pemeriksaan GitHub: main `8dd881b1fd6751d72af4929b0fc05278e8cc87ec`; head remote branch `cb4bc1ba1d566ed34483ee9235721f68d30130f3`; ahead 0 / behind 40. Angka dinamis karena main bisa menerima snapshot baru. Setelah PRD ditambahkan, branch memiliki commit dokumentasi unik; prosedur sinkronisasi tidak lagi mengasumsikan fast-forward main secara langsung.
- Referensi GitHub: https://github.com/Granbe1l/beta-test/compare/main...codex/uiux-redesign
- Sepuluh blob main dibaca ulang pada commit di atas dan sama dengan laporan:

| Path | Git blob SHA |
|---|---|
| streamlit_app.py | 6e5108a4ed9bda106c0e00bb17a4055f910bf04e |
| src/ui/dashboard_v2.py | 776d119d451d72a87ddca51d4439aba5698b9848 |
| src/ui/observed.py | 4d60dcbccc7d2b1b1d1393517808e62faca9bd34 |
| src/analytics/findings.py | fb4f4cbab68145a4f0d70f37fa9512a3afc59ebf |
| src/analytics/metrics.py | e2242cabfdef12cc228ff6d48798e964724a137a |
| src/analytics/case_studies.py | 662386f833b97788725df391c4dd7d6d5cdb4a93 |
| src/analytics/ci_workflow.py | 5620b030cee95c60bfb96207c27e2deee8b2d7cb |
| src/analytics/review_decisions.py | 416b0751abd4c2c6182e74c2dbed020c3da12048 |
| src/analytics/trends.py | c65472e567212791402f66e0d8bceb82ca7a1f18 |
| .github/workflows/public-snapshot.yml | 8c752d262c7a7ad161dc6e68b1b431e8d19ab7a0 |

SHA blob bukan hash SHA-256 file lokal. Saat execution mulai, fetch ulang, pin SHA baru, review delta terhadap daftar ini dan semua file terkait. Sepuluh file bukan keseluruhan cakupan audit.

**Bukti historis, bukan hasil baru:** audit 100 putaran/600 render baseline, 14 perubahan wajib diimplementasikan. Setelah implementasi: 17/17 targeted, 73/73 kalender, 37/37 edges, 56/56 display, 56/56 tooltip, 103/103 tren, 48/48 style, 24 fungsi/8 model HTML identik; build 28 bagian byte-identik. Suite penuh 50 putaran, kalender, display, edges sebagian dilakukan pada SHA sebelum patch keyboard akhir. Parity HTML–HTML bukan parity Python–JS. Fixture sintetis, Chromium, fixed clock, dan jaringan diblokir tidak mewakili seluruh kondisi produksi. Tidak menjumlahkan tes tumpang tindih. Belum ada verifikasi independen, Safari/perangkat fisik/screen reader nyata atau Vercel produksi. PRD tidak menyatakan pengujian ini diulang hari ini.

## 3. Persona, user stories dan alur

| Persona | Kebutuhan | Acceptance |
|---|---|---|
| HRD nonteknis | Memahami tujuan, kondisi, cakupan dan aksi berikutnya dengan cepat | Dari Dashboard dapat menjelaskan objek yang dipantau, periode, arti status Verified/freshness, satu insight dan bukti; tanpa perlu tahu GitHub API. |
| Data Analyst | Memahami formula, denominator, periode, sumber, keterbatasan | Dapat mereproduksi KPI/temuan dari snapshot yang sama dan mengekspor CSV dengan kontrak benar. |
| Pengguna teknis | Menelusuri repo, issue, PR dan CI | Dapat mencari, memfilter, membuka bukti publik, memahami unknown/partial serta kasus data gagal. |
| Maintainer | Menjalankan build/test, memeriksa refresh dan rollback | Satu instruksi reproduktif, log aman, tidak mengubah snapshot dari UI. |

Alur utama: Dashboard → temuan atau Eksplor → detail repositori → Issue/PR/CI → bukti sumber/kalender/ekspor sesuai kebutuhan; dapat kembali tanpa kehilangan konteks yang memang dipertahankan kandidat. Navigasi enam rute, back/forward, deep link dan reload harus diverifikasi sesuai kemampuan host; tidak menambah rute bisnis tanpa persetujuan.

## 4. Kontrak data dan arsitektur (wajib)

| Area | Sumber otoritatif / pagar |
|---|---|
| Cohort | Manifest main, tetap 50 ID/nama unik; jumlah Verified tidak dipaksa 50; identitas dan visibility fail-closed. Tidak mengganti repo, mengubah timestamp atau memperlonggar eligibility. |
| Scope | Verified joint 28→7→exploratory; selector otomatis pada redesign adalah perbedaan yang sebelumnya disetujui dari selector manual main. Scope per grafik, denominator aktual, status sumber dan alasan fallback harus terlihat; eksploratif memakai jumlah repo bukan rasio kelengkapan. |
| Waktu | Periode rolling 28×24 jam/7 hari sesuai definisi sumber; tren per tanggal UTC bukan kumulatif, WIB hanya presentasi yang diberi label. Partial day, UTC/WIB rollover, kalender dan batas min 2026-01-01 tidak disamakan dengan window rolling. |
| Issue | Inventori open issue, umur/backlog, opened/closed, kelengkapan inventori dan coverage dibedakan; nol teramati tidak berarti tidak ada aktivitas global. |
| PR | Open/draft dari snapshot; merged sesuai window; median hanya jika minimal 5 durasi valid; distribusi/bin, denominator dan batasan review tetap. Tidak menambah approval/review latency. |
| CI | Completed menurut created_at; known vs unknown, failure/timeout dan other known sesuai definisi main; rasio hanya known; unknown-only/zero denominator tidak berubah menjadi 0% palsu. |
| Temuan | Threshold, eligibility, urutan/tie-break, case studies, evidence dan keterbatasan berasal dari main; tidak memaksa tiga kartu atau rekomendasi tanpa dasar. |
| CSV | Filter kalender lokal hanya menyaring tabel; ekspor tetap seluruh catatan periode/sumber sesuai kontrak existing. Bandingkan header, urutan, row count, nilai dan encoding; jangan mengubah formula/arti kolom. Uji escaping nilai tak tepercaya. |
| Snapshot | Reader/validator existing dipertahankan. Freshness berdasarkan capture asli dan batas existing; reject schema invalid, duplicate, older, private/internal; last-good sesuai kebijakan main dengan status jujur, tanpa data dummy tersamar. |
| Collection | Workflow, DB, SQL, GitHub API, visibility, rescue, secrets dan cohort tidak diubah oleh redesign. Satu writer; UI tidak dapat dispatch. |
| Refresh | Workflow yang dibaca: cron `23 1,5,9,13,17,21 * * *` UTC (jadwal percobaan 4 jam, best-effort; bukan bukti keberhasilan aktual atau SLA). Rescue dapat menerima target 4/6 jam. Jangan mengubah cron/Cloudflare/threshold; verifikasi konfigurasi aktual secara read-only saat mulai. |

Arsitektur yang diusulkan: pipeline existing → snapshot valid/public → domain/model Python main → adapter read-only yang terdokumentasi → renderer/interaksi V9.5.52. Pilih mekanisme paling kecil yang sesuai host saat ini: model JSON yang divalidasi atau adapter ke komponen UI existing. Jika frontend tetap menghitung derivasi presentasi, definisi harus diuji dengan oracle Python. Jangan memindahkan formula tanpa traceability. Tentukan ADR yang mencatat kontrak input/output, versi schema, error state, timezone, nullability, cache, sumber kebenaran dan batas tanggung jawab. Jangan mengubah kontrak API publik atau menambah dependency/layanan berbayar tanpa justifikasi dan persetujuan. Tidak memaksa Next.js atau mengasumsikan Streamlit bisa berjalan langsung sebagai aplikasi Vercel; putuskan target deployment terpisah.

Empat rujukan teknis snapshot dalam JS beta-test tidak dihapus sebelum jalur pengganti teruji. Dalam integrasi sekarang inventaris lokasi dan klasifikasi public/internal, pastikan tidak berisi token atau payload privat, dan bungkus akses dalam adapter; sebelum repo privat/Vercel, pindahkan akses privat ke server read-only, verifikasi bundle/network/error tidak mengungkap identitas privat. Nama repo publik beta-test yang memang menjadi sumber bukan otomatis secret.

## 5. Requirement UI dan matriks keterlacakan

### 5.1 Enam rute

| ID | Rute | Requirement dan acceptance |
|---|---|---|
| R01 | Dashboard | Hero freshness/coverage, KPI label dan info nonteknis, trend 7/28, Sorotan dan CTA; tiap angka punya unit/periode/cakupan; count-up tidak mengubah nilai akhir. |
| R02 | Eksplor | Search/filter/reset, pagination, detail repositori, tautan sumber, empty state; scope dan denominator sesuai snapshot, label ringkas dan konsisten. |
| R03 | Issue | Inventori/backlog dan tren per scope, filter/search/pagination yang relevan, kategori umur, kalender/detail/bukti; batas inventori transparan. |
| R04 | Pull Request | Label pendek, median/durasi/distribusi dan open/draft/merged sesuai main; filter, pagination, kalender dan bukti; disclaimer review tetap. |
| R05 | CI | Known/unknown dan outcome tidak tertukar; label berdasarkan tanggal dibuat, denominator di catatan data, tren/kalender dan link yang valid; tidak ada 0% palsu. |
| R06 | Temuan Utama | Prioritas temuan, rekomendasi berbukti, case study, panel definisi stabil, detail repo/bukti; tidak memaksa temuan pada data kosong. |

### 5.2 Semua perubahan audit harus diwariskan (tidak cukup hanya tampak serupa)

| ID | Requirement | Tes penerimaan |
|---|---|---|
| AU01 | Freshness dan cakupan terlihat mobile | 320–1440; fresh/stale/missing; ID/EN, light/dark. |
| AU02 | Retry pada keenam rute hanya ketika gagal | Gagal→sukses/gagal→gagal, double click, fokus, loading, no dispatch. |
| AU03 | Tick adaptif tanpa buang titik; keyboard/touch | 3 chart × 7/28 × 5 viewport × 2 bahasa × 2 tema (120 kombinasi), tanggal pertama/terakhir, partial day, Arrow/Home/End/Escape/Tab, pilihan tanggal sempit, tooltip focus-scroll/mouse/touch dan semua nilai sama. |
| AU04 | Cakupan eksploratif berupa count, Verified rasio aktual | 50/49/0 eligible, hero/dialog/detail konsisten. |
| AU05 | Contoh lama 14 Nov dihapus hanya dari fallback Issue/PR/CI | Arsip dan baseline tetap; valid empty ≠ failed. |
| AU06 | Target chartDataTable stabil | aria-controls/expanded valid, hidden tanpa kontrol fokus, tabel/CSV tetap. |
| AU07 | Title tema sesuai aksi dan aria-label ID/EN | Empat kombinasi tema/bahasa, hover/fokus. |
| AU08 | State/fokus accordion definisi Temuan stabil | Rerender/tema/bahasa/snapshot; tidak mencuri fokus tombol lain. |
| AU09 | Picker tetap valid saat snapshot baru | Bulan/tahun/leap day, batas min/max, fokus, apply/cancel/Escape. |
| A00 | Hapus badge baca saja dan pengulangan footer/sidebar | Atribusi GitHub publik, status dan batasan data tetap. |
| UX01 | Label cakupan Verified dan CI selesai menurut tanggal dibuat | Semantik source dan waktu tidak berubah. |
| UX02 | Hilangkan helper search redundan | Label dan placeholder tetap. |
| UX03 | Lihat detail repositori / View repository details | CTA menuju rute yang benar. |
| UX04 | Ringkas catatan Sorotan | Rolling 28×24 jam, denominator, cakupan dan batasan tetap. |
| UX05 | Pull Request / Pull Requests | Disclaimer review tetap; tidak menambah metrik. |
| C01 | Drawer mobile modal; background inert | Fokus programatik dan Tab/Shift+Tab, Escape, tombol tutup, focus return, scroll lock dan pembaca layar. |
| C02 | Topbar wrap 320 dipertahankan | Kontrol tidak tertutup; ukuran target sentuh tidak dikorbankan. |
| AS02 | Pembersihan CSS/fungsi konservatif | 129 deklarasi dan 7 fungsi historis tidak dihidupkan lagi tanpa alasan; compare computed style, jangan hapus fallback/media spekulatif. |
| AS03 | Helper dan source modular | Scope count/retry/month shared; 28 bagian build referensi byte-identik; host build baru boleh berbeda byte jika perilaku setara dan dicatat. |

Catatan hitung: AU01–AU09 + A00 + UX01–UX04 = 14 wajib pada laporan; UX05, C01, C02, AS02/03 ditangani dalam eksekusi sesuai keputusan tercatat, bukan lima bug wajib tambahan. Jangan menafsirkan 14 sebagai jumlah keseluruhan acceptance.

### 5.3 Design system dan nonfunctional UX

Pertahankan Glass Glide, Refined Violet, spacing, hierarki tipografi, warna semantik status, layout sidebar, chart/table, icon info, copy ID/EN, skeleton/empty/error states. Pertahankan Echo Wave, count-up Sorotan 850 ms, transisi tema 350 ms dan bahasa 220 ms sebagai referensi kandidat; reduced motion harus menonaktifkan gerakan nonesensial dan tetap menampilkan data final. Tidak memperbesar bar/menambah kartu atau badge berulang tanpa bukti. Tidak memotong label/angka, memaksa lebar kolom, atau menyembunyikan denominator demi estetika. Fokus terlihat, keyboard dan pointer setara, chart memiliki alternatif tabel/teks. Visual diuji terhadap screenshot referensi yang memakai fixture/clock/viewport identik; perbedaan rendering font dan host yang sah dicatat, bukan mengejar pixel-perfect dengan CSS hack.

## 6. Runbook eksekusi berurutan dengan gerbang STOP/GO

**Aturan global:** jangan berpindah tahap ketika gerbang sebelumnya belum lulus. Catat SHA, perintah, exit code, evidence path, waktu, hasil aktual dan blocker; status PASS/FAIL/BLOCKED/N/A (N/A harus beralasan). Untuk setiap bug: reproduksi RED yang sah → patch minimal → GREEN → regresi. Tidak menghapus/melonggarkan assertion demi lulus. Simpan commit kecil dengan scope tunggal; tidak force-push, tidak reset --hard, tidak git clean -fdx, tidak mengedit main lokal/remote, tidak menjalankan job writer. Jangan menganggap persetujuan membuat PRD adalah izin eksekusi, penghapusan atau merge.

### Tahap 0 — Inventaris dan pembekuan pekerjaan lama
- [ ] Konfirmasi worktree benar, remote URL, branch aktif, semua worktree dan upstream. Jalankan read-only: `git status --short --branch`, `git remote -v` (redaksi credential jika URL sensitif), `git worktree list`, `git branch -vv`, `git log -5 --oneline`, `git diff --stat`, `git diff --cached --stat`, `git ls-files --others --exclude-standard`. Jangan mencetak isi .env/token.
- [ ] Inventaris tracked/staged/untracked/ignored penting, build lama, fixture, source 28 bagian, scripts, laporan dan evidence. Identifikasi hasil integrasi lama vs perubahan main vs dokumen yang harus dipertahankan. Jangan salin seluruh .git/venv/node_modules atau secret ke repo.
- [ ] Cadangkan SHA lokal/remote, perubahan tracked/staged melalui patch/bundle atau commit backup lokal setelah review, serta file untracked penting secara terpisah di storage lokal aman; ignored secret hanya ditangani pemilik dengan storage aman, tidak masuk bundle/commit/log. Jangan push backup tanpa persetujuan.
- [ ] Uji backup dapat dipulihkan di lokasi terisolasi; inventaris hash file, catat path privat lokal dalam log yang tidak di-push. Pastikan kandidat V9.5.52 dan seluruh bukti tidak hanya berada di worktree yang akan dibersihkan.
- [ ] Jika sumber modular/test harness hilang, cari artefak asli sebelum menyusun ulang. Jangan menebak 28 bagian atau mengklaim build identik tanpa verifikasi.
**Gate 0:** backup verified; pekerjaan lama dan artefak audit aman; scope penghapusan jelas. Jika ada file/commit unik yang tidak diketahui, STOP dan minta keputusan. Penghapusan permanen tidak diperlukan.

### Tahap 1 — Regresi kandidat referensi (sebelum port)
- [ ] Verifikasi SHA-256 HTML final vs §2 (PowerShell Get-FileHash atau sha256sum); hash manifest source, build, fixture dan evidence. Jalankan build 28 bagian sesuai tooling asli; byte-compare dengan kandidat final. Simpan baseline V9.5.51 read-only.
- [ ] Siapkan browser/versi, dependency lock, fixture deterministik, fixed UTC clock, jaringan diblokir untuk suite fixture; isolasi cache, session, data dan akun. Pastikan tes tidak memanggil writer.
- [ ] Ulang semua suite pada kandidat final yang sama: targeted 17, kalender 73, edges 37, display 56, tooltip 56, tren 103, styles 48, model 24 fungsi/8 skenario, 96 layout dasar, sweep 50 putaran/300 rute dan skenario interaksi kedua yang relevan (termasuk pagination dan Temuan dengan fixture yang memenuhi syarat). Periksa 120 kombinasi chart; jangan menjumlahkan suite tumpang tindih.
- [ ] Periksa patch keyboard terakhir secara spesifik: fokus programatik drawer, scroll akibat focus, tooltip keyboard tetap muncul, mouse/touch dismiss, Tab/Escape dan focus return; uji normal motion juga.
- [ ] Verifikasi setiap ID §5.2 tercatat, screenshot/trace dan hasil raw tersedia; patch hanya bila reproduksi gagal. Jika kandidat berubah, buat versi/hash baru, changelog dan ulang seluruh regresi pada hash baru.
**Gate 1:** seluruh suite wajib selesai pada hash yang akan dipakai. Hasil lama yang belum dijalankan ulang tidak berstatus PASS baru. Bila tools/artefak tidak tersedia, BLOCKED, jangan memalsukan.

### Tahap 2 — Sinkronisasi branch tujuan dengan main (tanpa menghapus riwayat)
- [ ] `git fetch origin`; catat `git rev-parse origin/main`, `git rev-parse origin/codex/uiux-redesign`, `git rev-list --left-right --count origin/main...origin/codex/uiux-redesign`, log/diff kedua arah dan status worktree.
- [ ] PRD ini sendiri menambah satu commit dokumentasi pada branch. Jangan menganggap branch masih ahead=0. Jika remote hanya mempunyai perubahan dokumen yang disetujui di atas main lama, siapkan worktree bersih dari remote branch pada path baru (gunakan branch temporer lokal bila branch sudah checked out), kemudian merge main yang dipin secara normal; jangan fast-forward main ke branch tanpa verifikasi atau reset branch. Jika lokal punya hasil integrasi lama, tinggalkan worktree lama sebagai arsip hingga migrasi sukses.
- [ ] Jika remote ternyata memiliki commit kode integrasi lama, inventaris commit dan file. Gunakan merge normal + revert/restore file kode lama secara terarah dari pinned main dalam commit tersendiri, atau prosedur non-destructive lain yang disetujui pemilik; pertahankan dokumen dan sejarah. Jangan gunakan checkout/restore seluruh tree tanpa daftar allowlist dan bukti backup. Konflik: pilih main untuk backend/data/pipeline; dokumentasi PRD dipertahankan; jangan pilih ours/theirs massal.
- [ ] Buktikan ancestor dengan `git merge-base --is-ancestor <PINNED_MAIN_SHA> HEAD`; bandingkan `git diff --name-status <PINNED_MAIN_SHA> HEAD`; baseline siap bila hanya PRD/dokumen allowlist, kode/dataset/workflow identik.
- [ ] Jalankan baseline tests yang ditemukan dari CI/config actual (Python, SQL, Node/Worker bila ada, AppTest enam rute, validator, reproducible CI) sebelum perubahan UI. Catat kegagalan baseline terpisah; jangan menyembunyikannya di patch UI.
**Gate 2:** baseline benar dan bersih, PRD tetap ada, backup utuh, existing tests lulus atau blocker diselesaikan dengan izin. Push hanya fast-forward normal ke branch tujuan setelah review diff dan izin eksekusi; jika remote maju, fetch dan reevaluasi, bukan force.

### Tahap 3 — Inventaris arsitektur, source map dan kontrak
- [ ] Baca tree, README, dependency/lock, CI, collector, snapshot validator, config, DB schema/migrations, SQL, Python domain, streamlit routes, CSS/assets, public docs, test harness. Tentukan entrypoint dan cara build aktual dari repo, jangan mengasumsikan perintah lama masih valid.
- [ ] Buat matriks fungsi main → field schema → komponen V9.5.52 → test oracle; petakan setiap KPI, chart, tooltip, status, filter, kalender, export, finding dan evidence. Catat fungsi existing yang tetap dibutuhkan meski UI lama diganti.
- [ ] Tetapkan ADR adapter/host; bedakan data retrieval, validation, domain, view model, renderer dan client state. Buat schema versioning, null/error/loading contract dan allowlist URL.
- [ ] Bekukan snapshot publik produksi yang sudah terbit dari main secara read-only (bytes/hash/capture/manifest); jangan menjalankan refresh baru. Gunakan clock yang sama untuk Python dan frontend, fixture sintetis terpisah; jangan commit salinan data sensitif atau dataset pengganti. Baseline output dicatat untuk scope normal/7/partial/stale/small sample/unknown/empty/open backlog partial.
- [ ] Buat daftar path boleh diubah (UI, adapter, assets, build, tests, docs); path dilindungi (collector, analytics, DB, dataset, workflow, cloud config, creds). Perubahan protected path harus punya justifikasi dan persetujuan tersendiri.
**Gate 3:** seluruh field/method punya mapping; sumber authoritative jelas; tidak ada kontrak baru tanpa persetujuan.

### Tahap 4 — Foundation frontend dan adapter (vertical slice)
- [ ] Port tokens/layout/sidebar/topbar, tema, bahasa, typography, ikon, fokus, chart primitives, loader/error/empty, pagination/search/date picker, drawer/modal, toast jika existing. Gunakan source modular kandidat; hindari copy HTML monolitik sebagai sumber utama bila source tersedia.
- [ ] Implement adapter tipis read-only dengan schema check, freshness, abort/timeout, request dedupe, stale response/race guard, last-good sesuai policy, retry manual hanya load snapshot existing saat failure. Validasi missing/invalid/duplicate/older/private/internal tidak lolos. Tidak ada mock fallback yang terlihat seperti produksi.
- [ ] Satu jalur data nyata (Dashboard vertical slice) sampai render KPI/chart dan satu evidence link; tes Python oracle dan client contract. Jangan menggandakan formula atau mengubah sumber data agar cocok UI.
- [ ] Build deterministik dengan dependency terkunci, konfigurasi host dev/staging, tidak memasukkan token di build. Gunakan existing tooling selama layak. Catat perubahan lockfile dan license/dependency.
**Gate 4:** shell enam rute dapat diakses, vertical slice nyata lulus, kontrak adapter dan loading/error/freshness lulus, tidak ada perubahan path dilindungi.

### Tahap 5 — Integrasi rute berurutan
Untuk tiap rute: implementasi → unit/contract → interaction/visual → parity → review diff → commit kecil; jangan mulai rute berikutnya sebelum gate rute sebelumnya.
- [ ] 5.1 Dashboard: R01, AU01/AU03/AU04, Sorotan, status, CTA, period/per-source scope, count-up; tes data fresh/partial/empty/stale.
- [ ] 5.2 Eksplor: R02, UX01/02/03, search/filter/reset, pagination dan detail, hasil kosong dan repo tidak eligible, long name/URL.
- [ ] 5.3 Issue: R03, AU02/03/05/06, backlog & umur/coverage, chart/tabel, filter/kalender/CSV/evidence.
- [ ] 5.4 Pull Request: R04, UX05, median min lima, draft/open/merged, bin/timestamp, filter/kalender/evidence/CSV.
- [ ] 5.5 CI: R05, UX01, known/unknown/other, creation-date, denominator/rasio, retry/fallback/kalender/CSV.
- [ ] 5.6 Temuan Utama: R06, AU08, rank/eligibility, case study, bukti, definisi/fokus, empty dan perubahan snapshot.
- [ ] 5.7 Cross-route: AU07/09, A00, UX04, C01/02, AS02/03, tema/bahasa/state, keyboard/touch, shared components, history/deep link sesuai host, export dan error. Hapus UI lama dari jalur aktif hanya setelah semua fungsi pengganti terbukti. Pertahankan rollback melalui Git; jangan menyisakan dua entrypoint produksi/dua pipeline aktif.
**Gate 5:** R01–R06 dan semua ID §5.2 punya PASS pada integrated build; tidak ada rute placeholder, fungsi yang diam-diam hilang, atau data hard-coded.

### Tahap 6 — Data QA dan differential parity (wajib)
- [ ] Dengan pinned snapshot + fixed clock, jalankan Python main sebagai oracle dan integrated adapter/UI; normalisasi representasi yang sah saja (format, timezone tampilan, urutan yang tidak semantik). Numeric integer/count exact; decimal pakai toleransi yang disepakati sebelum tes dan sesuai presisi domain; null/zero/unknown distinct. Bandingkan raw model sebelum format UI serta teks yang tampil.
- [ ] Cohort 50 ID unik dan stable, 50/49/0 eligible, scope joint 28/7/exploratory, coverage source, 7/28 window, per-date UTC, partial day, freshness and failure, issue inventories, PR median threshold 4/5, CI known/unknown/zero, finding threshold/tie/order/case-study/evidence, SQL vs model, CSV. Uji real snapshot beku dan fixture batas; jangan memanipulasi produksi untuk memaksa edge.
- [ ] Kalender: sumber/status/filter, min date 2026-01-01, max snapshot, leap day, rollover UTC/WIB, range terbalik, refresh saat dialog terbuka, filter tabel tidak mengubah isi ekspor. Uji safe CSV escaping untuk untrusted cells; jika kontrak berubah, stop dan minta keputusan.
- [ ] Security/data quality: reject bad schema, duplicate/old snapshot, private/internal repo termasuk perubahan visibility, invalid timestamp/NaN/Infinity, null/unknown, long labels, negative/inconsistent counts, stale last-good.
- [ ] Buat machine-readable diff report per field/rute/scenario; setiap beda dikategorikan intentional-presentational/approved contract change/bug. Bug diperbaiki di lapisan yang tepat, bukan mengubah oracle. Perbedaan otomatis selector dicatat sebagai approved existing decision.
**Gate 6:** zero unexplained analytical differences, zero invalid data leak, semua export/evidence valid; hasil ini baru disebut production-snapshot parity setelah benar-benar diuji.

### Tahap 7 — QA lintas menu, aksesibilitas, anti-slop dan performa
- [ ] Matrix seluruh 6 rute × viewport 320/360/390/768/1280/1440 CSS px × 2 tema × 2 bahasa; desktop/tablet/mobile, orientation/zoom 200% dan reflow 320; normal/reduced motion. Periksa visual, overflow dokumen, clipped control, duplicate H1/ID/nav, salah label, layout shift, focus dan target touch. Scroll internal tabel yang disengaja bukan otomatis bug.
- [ ] Chromium, Firefox, WebKit/Safari; bila tersedia iOS/Android fisik dan screen reader NVDA/VoiceOver. Emulasi WebKit bukan klaim Safari fisik. Keyboard-only, pointer/touch, Enter/Space/Tab/Shift+Tab/Arrow/Home/End/Escape, modal semantics, focus return, aria-controls, accessible names, status updates, contrast solid/gradient/SVG/transparency. Target WCAG 2.2 AA: teks normal 4,5:1, teks besar/nontext relevan 3:1, target 24×24 CSS px atau pengecualian sah; uji manual bersama automated screening. Jangan klaim compliance hanya dari scanner.
- [ ] Regresi normal/slow/offline/timeout/429/500, stale/empty/loading, background refresh, race, duplicate/retry, theme/language while loading, scroll/focus/chart tooltip, pagination/filter saat data berubah, history/reload, export/evidence.
- [ ] Ukur cold/warm load, JS/CSS bundle, network requests, render/navigation latency, memory setelah berulang rute, animasi dan reduced motion. Gunakan perangkat/network/clock dan baseline yang sama, minimal 5 pengulangan dan median + variasi. Target awal yang diusulkan untuk preview: LCP ≤2,5s, CLS ≤0,1, INP ≤200ms sebagai sasaran web-vitals p75 lapangan jika telemetry tersedia; lab proxy dilaporkan terpisah, bukan klaim field INP. Tidak menurunkan kualitas data untuk performa. Bila host tidak dapat mengukur metrik tertentu, jelaskan metode alternatif dan keterbatasan.
- [ ] Anti-slop: periksa duplicate logic, dead code, layering CSS, shared state, excessive dependency, misleading copy, redundant UI, arbitrary magic number. Tidak mengejar jumlah !important/fungsi; refactor hanya jika ada manfaat terukur, preserve fallback/media/cascade, ulang computed-style dan behavior.
- [ ] Human evaluation: tugas HRD memahami data tanpa jargon, Analyst mereproduksi angka, pengguna teknis membuka evidence. Jika tidak ada partisipan independen, beri label heuristic only, jangan mengarang feedback. Uji minimal skenario task walkthrough; user study nyata opsional jika pemilik memilih tidak melakukannya, tetapi klaim human-tested dilarang.
**Gate 7:** tidak ada P0/P1, tidak ada critical accessibility/task blocker, performance regression material diselesaikan atau didokumentasikan dan disetujui. Lingkungan yang tidak tersedia tidak dihitung lulus; bila tes wajib tidak dapat dijalankan, BLOCKED sampai ada bukti atau risk acceptance eksplisit untuk item nonkritis.

### Tahap 8 — Security, operasional dan rollback
- [ ] Review diff path protected, dataset hash terhadap frozen baseline (snapshot main yang bergerak adalah delta sah hanya setelah rebaseline/review), cohort manifest, workflow paths/triggers, permissions, concurrency, dispatch guard, DB BIGINT/migration compatibility, CI freshness semantics. Jangan menjalankan writer hanya untuk pengujian UI.
- [ ] Audit token/env/build/source map, network/URL query, logs/artifacts/error response, Git history diff; secret scanner dengan output teredaksi, unsafe HTML injection/XSS, external URL protocol/rel, CSP/headers sesuai host, CSV escaping, access control/CORS/rate limiting bila ada endpoint server. Secret tidak pernah masuk public repo/browser. Bila menemukan secret, stop publikasi, lapor lokasi tanpa nilai dan koordinasikan revoke/rotate dengan pemilik.
- [ ] Uji failure recovery read-only, last-good dan rollback menggunakan fixture/storage isolasi. Pastikan staging tidak memakai kredensial write produksi dan tidak menjalankan snapshot publisher kedua. Periksa scheduler/Worker read-only bila akses tersedia; status jadwal tidak dianggap keberhasilan refresh.
- [ ] Siapkan rollback pre-merge: simpan main SHA, kandidat SHA, commit per tahap, build reference; revert commit integrasi pada branch dengan review, atau kembali ke deployment last-known-good kelak. Jangan restore dataset lama ke produksi secara manual atau force-reset main. Uji rollback di lingkungan terisolasi.
**Gate 8:** no secret/private leak, no second writer, protected config intact, rollback dry run terbukti; P0/P1 unresolved = NO-GO.

### Tahap 9 — Final regression, CI dan PR
- [ ] Fetch main terbaru. Klasifikasikan delta sejak pinned baseline: snapshot-only vs kode/domain/workflow/schema. Merge main secara normal di branch, ulang parity pada snapshot terbaru yang dipin dan full regression untuk perubahan kandidat/kontrak. Jika main berubah saat CI, validasi merge candidate terbaru; jangan mengandalkan hasil SHA lama.
- [ ] Clean checkout/build pada exact candidate SHA; dependency install terkunci; jalankan seluruh perintah CI aktual, unit Python, SQL/domain, Node/Worker, AppTest semua route (jika tetap berlaku), lint/typecheck/build, UI tests, parity, security tests. Jika suite lama tidak relevan karena host berubah, jelaskan mapping dan tes pengganti; jangan sekadar skip.
- [ ] Pastikan semua bukti terkait SHA yang sama: report pass/fail/blocked, JUnit/JSON, screenshot/trace, baseline/main SHA, snapshot hash+capture, dependency/browser versions, diff allowlist, PRD traceability, ADR, known limitations, rollback. Jangan publikasi screenshot data nonpublik.
- [ ] Review PR lengkap: base main, head codex/uiux-redesign; title/scope, perubahan per rute, protected files, perbedaan selector yang disetujui, bukti CI GitHub-hosted, parity, accessibility/perf, risk register dan rollback. Periksa merge conflict/required checks/branch protection. Push hanya branch target setelah review dan otorisasi eksekusi; jangan mengubah main.
- [ ] Siapkan keputusan GO/NO-GO untuk pemilik. Tidak merge, squash, rebase remote, deploy production atau mengubah pengaturan repo sebelum persetujuan eksplisit. Draft PR hanya jika disetujui dalam pelaksanaan; dokumentasi ini sendiri tidak membuat PR.
**Gate 9:** exact SHA + merge candidate lulus CI, semua mandatory requirements PASS, zero P0/P1, semua risiko nonkritis diterima tertulis, approval pemilik. Jika salah satu hilang: NO-GO untuk merge.

### Tahap 10 — Setelah merge (rencana terpisah; belum diotorisasi)
- [ ] Setelah pemilik menyetujui merge, verifikasi main hasil merge, smoke 6 rute, CI, diff protected, freshness read-only dan baseline rollback. Jika regresi, koordinasikan revert terkontrol, jangan overwrite snapshot.
- [ ] Sebelum repo privat: tentukan strategi salin kode dari main stabil, lisensi dan history/secret hygiene; jangan menyalin .env, PAT, Worker secret, kredensial DB atau data privat. Buat repo privat baru hanya atas izin, set akses minimum; token baru dengan scope minimum, simpan hanya server/environment. Rotation/revoke token lama sesuai persetujuan dan dependency map.
- [ ] Pilih arsitektur hosting kompatibel Vercel berdasarkan runtime/build/timeout/storage/size; frontend statis + server read-only bila layak, backend Python/collector dapat tetap terpisah sesuai ADR. Jangan mengaktifkan collector/writer kedua. Pindahkan empat rujukan snapshot ke adapter server setelah jalur pengganti terbukti; validasi cache, auth, schema, stale/error, preview access, logs, secret scan, bundle/network, biaya/limit. Jangan publikasikan identitas repo privat atau data yang tidak diizinkan.
- [ ] Preview Vercel dengan env nonproduksi, uji parity/data/6 rute/security/performance/cross-browser, monitoring/rollback last-known-good. Approval terpisah sebelum deployment production. Jangan menyatakan Vercel siap hanya karena HTML lokal berhasil.

## 7. Matriks pengujian dan quality gate

| Suite | Wajib | Bukti |
|---|---|---|
| Candidate regression | Semua suite §6 tahap 1 pada final hash | Test output + hash + fixtures |
| Baseline main | Existing suite pada pinned SHA | CI config, log, exit code |
| Data/domain | Differential parity real snapshot + synthetic edges | Per-field diff report, clock/hash, SQL/CSV |
| 6 routes | Unit/contract + E2E, per rute dan cross-route | Reports + screenshots/trace |
| UX/responsive | Matrix 6×6×2×2 = 144 layout combinations; interaction matrix terpisah | viewport/browser/state/fixture; exceptions |
| Chart | 120 kombinasi dasar AU03 dan keyboard/touch | tick geometry, point counts, values, tooltip |
| Accessibility | Keyboard, contrast, semantics, zoom/reflow, reduced motion, screen reader bila tersedia | automated + manual, batas lingkungan |
| Resilience | offline/slow/invalid/stale/race/retry | network fixture/trace, no dispatch |
| Security/ops | secret/privacy, protected paths, writer, snapshot validator, rollback | redacted scan, diff, dry run |
| CI & merge | GitHub-hosted exact SHA dan merge candidate | run link, required checks, review |

**Rubrik 100% bobot:** integritas data/metodologi 20%; fungsi dan reliability 15%; UI visual/konsistensi 10%; UX/HRD comprehension 15%; aksesibilitas 10%; visualisasi 10%; performa 5%; maintainability/anti-slop 5%; keamanan/operasional 10%. Beri 0–10 hanya untuk dimensi dengan bukti; N/T bila belum diuji, jangan hitung sebagai nol atau nilai sempurna; skor total final hanya setelah seluruh dimensi wajib dinilai. Target >8,5 tidak menggantikan gate. Reviewer independen vs self-review dicatat. Nilai per menu dan persona di report akhir.

## 8. Prioritas dan risk register

| ID | Prioritas gerbang | Risiko | Pencegahan / kondisi penutupan |
|---|---|---|---|
| F01 | P0 | Baseline branch tertinggal | Gate 0–2; ancestor main, diff awal docs-only |
| F02 | P1 | Regresi belum lengkap pada hash final | Gate 1; semua suite rerun |
| F03 | P1 | Drift Python–JS | Gate 3/6; zero unexplained diff |
| F04 | P1 | Referensi snapshot di client | Gate 4/8; no secret/private payload; server replacement sebelum private/deploy |
| F05 | P1 | Modular source belum terintegrasi | Gate 4/5; reproducible build dan mapping |
| F06 | P2 | Cross-browser/perangkat | Gate 7; bukti atau limitation/risk acceptance |
| F07 | P2 (P0/P1 bila task blocked) | A11y | Gate 7; critical blockers zero |
| F08 | P2 | Kinerja hosting | Lab sekarang, preview deployment tahap 10 |
| F09 | P3 | CSS/shared state debt | Konservatif, backlog jika tidak menyebabkan bug |
| R10 | P0 | Kehilangan kerja lokal | Backup restore test; no destructive reset |
| R11 | P0 | Secret/private leakage atau writer kedua | Gate 8; stop, isolate, approval |
| R12 | P1 | Main bergerak/CI stale | Gate 9; rebaseline dan exact SHA |
| R13 | P1 | Missing artifacts/test harness | Gate 0/1; recover, BLOCKED bila hilang |
| R14 | P1 | Fitur hilang setelah port | Traceability R01–R06/AU/UX; E2E |

Severity temuan aktual: P0 = kehilangan data/secret, corruption, production writer/branch tidak aman; P1 = salah KPI/kontrak, fungsi utama gagal, regression gate gagal; P2 = kualitas/aksesibilitas/performa nonblocking; P3 = minor/debt. Prioritas gerbang di atas bukan klaim bug baru yang sudah terbukti.

## 9. Kontrol perubahan, otorisasi, penghentian dan pelanjutan

Boleh dilakukan setelah izin eksekusi: read-only inspeksi, backup lokal aman, baseline sinkronisasi non-destructive, tes terisolasi, patch UI/adapter yang sesuai PRD, commit terkontrol di branch tujuan. Minta approval sebelum: menghapus data/kerja unik secara permanen; mengubah domain/cohort/SQL/schema/workflow/cron/Worker/secret; dependency/hosting berbiaya atau framework rewrite; perubahan metodologi/UX di luar kontrak; push backup/secret/data; merge main; repo privat, rotasi token, deploy produksi. Bila izin push branch belum jelas, laporkan diff dan minta izin. P0/security blocker: stop segera. Tidak mengeksekusi sebagian sebagai selesai.

Simpan checkpoint per gate: ID tahap, main SHA, branch HEAD, candidate HTML SHA, snapshot hash/capture, test command/exit, passed/failed/blocked, evidence, change allowlist, next action. Jika limit/timeout/interupsi, lanjut dari checkpoint terakhir yang terbukti; rerun gate yang SHA/input berubah; jangan menghitung tes terputus sebagai lulus. Hindari pekerjaan paralel yang menulis file sama.

## 10. Deliverables dan format laporan penutup

- [ ] PRD ini dan changelog keputusan/ADR; source/evidence map.
- [ ] Backup ledger lokal aman dan restore verification; baseline SHA + diff.
- [ ] Source modular, adapter/schema, dependency lock, build/dev instructions, tests; hanya file yang diperlukan masuk git.
- [ ] Traceability ledger per requirement dan gate, raw test output, parity report, screenshot/trace non-sensitif, security/perf/accessibility report.
- [ ] Pre-merge report dengan nilai per aspek/menu/persona, severity, blockers, batas bukti, protected-file diff, GitHub CI link, rollback dan rekomendasi GO/NO-GO.
- [ ] Handoff deploy privat/Vercel terpisah; bukan bagian dari status selesai integrasi branch.

Template ledger: `ID | Requirement | Stage | SHA | Fixture/snapshot | Test/evidence | Result | Owner | Next action`. Template ringkasan: baseline main SHA, head SHA, candidate hash, scope, semua gate, bukti aktual, risiko terbuka, keputusan dan persetujuan. Untuk hasil yang tidak diuji gunakan BLOCKED/N/T, bukan PASS. Tidak ada checklist yang dicentang saat pembuatan PRD.

**Definition of Done branch:** Gate 0–9 terpenuhi, review lengkap, bukti traceable dan keputusan siap merge disampaikan kepada pemilik. Merge bukan bagian otomatis dari DoD branch. **Definition of Done produksi:** persetujuan terpisah, tahap 10 dan validasi hosting/security/operasional terpenuhi. 

**Instruksi pertama bagi pelaksana:** baca PRD ini dan laporan eksekusi V9.5.52, lakukan tahap 0 read-only dan backup; hentikan bila bukti/artefak tidak tersedia. Jangan menyentuh main, scheduler, dataset atau token. Jangan menerapkan desain lama hanya karena ada di worktree. Laporkan gerbang sebelum bergerak, bukan menebak atau mengejar skor.
