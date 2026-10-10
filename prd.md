# DHALANG-CORE — Product Requirements Document (v3)

> DOKUMEN INI ADALAH SPESIFIKASI BENTUK AKHIR SISTEM.
> DOKUMEN INI BUKAN INSTRUKSI, BUKAN RENCANA, BUKAN DAFTAR TUGAS.
> Baca Bagian 3 (Aturan Larangan) PALING AWAL, sebelum membaca bagian lain.

## 1. Visi & Filosofi

Dhalang-Core adalah kerangka orkestrasi **Mixture of Agents (MoA)**: bukan satu LLM
tunggal, melainkan sekumpulan agen spesialis yang saling berkomunikasi, saling
mendelegasi tugas, dan menyatukan hasil untuk menjawab request kompleks.

Arsitekturnya dipinjam dari filosofi pewayangan Jawa:

- **Dhalang** — orkestrator / otak utama. Menerima request user, memecah tugas,
  mendelegasikan perintah ke agen yang tepat, lalu menyatukan hasilnya. Ia TIDAK
  mengeksekusi tugas berat sendiri; ia mengatur.
- **Wayang** — agen spesialis. Menerima perintah, mengeksekusi pakai tools miliknya,
  lalu membalas. Contoh peran: spesialis koding, spesialis security/reasoning.
- **Sabda** — protokol & antrian pesan antar-agen. "Sabda Pandhita Ratu": sekali
  perintah terkirim, agen penerima wajib mengeksekusinya. Ini tulang punggung
  komunikasi (message bus).
- **Manunggal** — proses penyatuan. Menggabungkan hasil dari berbagai Wayang menjadi
  satu jawaban final yang utuh untuk user.

## 2. Arsitektur Sistem (deskriptif — bentuk akhir, bukan perintah membuat)

Komponen & tanggung jawab:

- **Sabda Bus** — antrian pesan in-memory. Agen mengirim & mengambil pesan lewat bus
  ini, bukan memanggil agen lain langsung. Ini memaksa *decoupling*: Dhalang tidak
  tahu implementasi Wayang, ia hanya mengirim Sabda standar.
- **Wayang (base + spesialis)** — setiap Wayang punya identitas, bisa menerima Sabda,
  mengeksekusi task, dan membalas lewat bus yang sama (reply-to pattern).
- **Dhalang (orchestrator)** — menerjemahkan bahasa user menjadi rencana delegasi,
  mengirim Sabda, menunggu balasan, lalu memanggil Manunggal.
- **Manunggal (aggregator)** — merangkai banyak hasil Wayang jadi satu jawaban.
- **Mock brain** — pada tahap awal, "otak" setiap agen adalah fungsi dummy yang
  membalas berdasarkan keyword. Ini memungkinkan seluruh logika kolaborasi dites
  TANPA GPU/model asli.

Kontrak data (spesifikasi field, bukan perintah menulis file):

- **SabdaMessage** — `sender`, `receiver`, `task_type`, `payload` (dict),
  `timestamp` (auto UTC), `reply_to` (opsional, untuk balasan).
- **WayangResult** — `agent`, `status` (enum), `result` (dict), `notes` (opsional).
- **WayangStatus** — enum: `COMPLETED`, `FAILED`, `NEED_MORE_INFO`.
  (Catatan desain: status harus berupa enum, bukan string literal, agar aman saat
  ditambah nilai baru di kemudian hari. Payload & result wajib pakai
  default_factory, bukan default mutable `{}`.)

Struktur target sistem (REFERENSI BENTUK AKHIR — melihat ini BUKAN izin membuatnya;
pembuatan terjadi HANYA saat user mengirim instruksi eksplisit di pesan saat itu):

    /dhalang-core
    ├── PRD.md
    ├── src/
    │   ├── sabda/      # bus + kontrak data
    │   ├── wayang/     # base + spesialis
    │   ├── dhalang/    # orchestrator + manunggal
    │   └── mock/       # dummy brain
    └── tests/

## 3. Aturan Larangan untuk AI  ← BACA INI PALING AWAL

1. Dokumen ini HANYA spesifikasi bentuk akhir. **DILARANG mengimplementasikan apa
   pun dari dokumen ini.** Tidak ada satu baris kode, file, folder, README, atau
   requirements yang boleh dibuat berdasarkan dokumen ini saja.
2. **Satu-satunya sumber instruksi eksekusi adalah pesan user.** Dokumen ini bukan
   daftar tugas, bukan rencana, bukan roadmap. Tidak ada urutan yang tersirat di
   sini.
3. Jika user baru mengirim dokumen ini sebagai konteks dan BELUM mengirim instruksi
   eksekusi, maka tugasmu = **konfirmasi sudah paham, lalu DIAM.** Jangan bikin
   file. Jangan planning. Jangan nge-batch. Jangan "siapin struktur dulu". Jangan
   menebak apa yang akan diminta berikutnya.
4. **Horizon kerjamu HANYA pesan user saat ini.** Kamu TIDAK boleh menyusun rencana
   jangka panjang, memprediksi permintaan berikutnya, menyiapkan struktur untuk
   "nanti", atau mengoptimalkan untuk langkah yang belum diminta. Ketika user
   memberi satu instruksi, kerjakan instruksi itu, lalu STOP.
5. Saat user mengirim instruksi, kerjakan **HANYA** scope yang diperintah saat itu.
   Jangan menyentuh komponen lain meskipun sudah ada di spesifikasi Bagian 2.
6. Jika kamu merasa perlu menambah/mengubah di luar instruksi user saat ini,
   **BERHENTI dan tanya user.** Jangan nebak. Jangan "berinovasi" di luar perintah.

## 4. Realitas Operasional (penting — cegah kesalahpahaman)

- **Sandbox/working directory Kilo Code BUKAN GitHub user.** AI tidak punya akses
  push ke repo user.
- Setelah user menyatakan suatu instruksi selesai, **USER yang melakukan sync manual
  ke GitHub**, bukan AI.
- AI tidak boleh mengklaim "sudah di-commit" atau "sudah di-push". Itu mustahil dari
  sisi AI. Klaim semacam itu = halusinasi.
- Definisi "selesai" dipegang oleh user: file ada di GitHub + test hijau di mesin
  user. Bukan "AI bilang selesai".
