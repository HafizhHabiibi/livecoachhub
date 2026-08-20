LIVECOACHHUB

Integrated System Design

Ringkasan Subproyek NLP + Action/Knowledge/QLoRA LLM, Pipeline Preliminary, serta Opsi Pengembangan Final

Catatan: isi repository dapat berubah setelah dokumen ini dibuat. Temuan teknis di sini merefleksikan struktur repository yang telah diaudit dalam proyek ini.

# Ringkasan Eksekutif

LiveCoachHub dirancang sebagai AI copilot untuk membantu seller live commerce memahami pola pertanyaan audiens dan segera memperoleh rekomendasi tindakan serta kalimat yang bisa diucapkan. Dua subproyek yang sudah dikerjakan anggota tim sebenarnya saling melengkapi: subproyek pertama berfungsi sebagai “indra” yang memahami komentar, sedangkan subproyek kedua berfungsi sebagai “otak keputusan + penyusun bahasa” yang menentukan respons berbasis fakta produk.

Agar keduanya menjadi satu produk, diperlukan satu lapisan integrasi yang melakukan tiga hal: (1) mempertahankan identitas setiap komentar, (2) mengagregasi hasil NLP dalam rolling window 60 detik, dan (3) menyamakan taksonomi intent NLP dengan sinyal yang dipahami Action Engine. Setelah itu pipeline dapat berjalan linear: komentar → intent → sinyal window → audience state → recommended action → fakta produk → seller script → validation → tampilan frontend.

Prinsip desain preliminary: satu pipeline end-to-end yang benar-benar bekerja lebih bernilai daripada banyak fitur yang belum matang. Ini juga paling selaras dengan batas MVP pada rulebook terbaru.

# Daftar Isi

1. Konteks dan Tujuan Sistem

2. Subproyek Teman 1 — Fashion Intent NLP

3. Subproyek Teman 2 — Action Engine, Knowledge Base, QLoRA LLM, Validator

4. Gap Integrasi Dua Repository

5. Rancangan LiveCoachHub Preliminary — Satu Pipeline Linear

6. Kontrak Data Antar-Komponen

7. Rancangan UI, Use Case, dan Skenario Demo

8. Kepatuhan terhadap Batas Preliminary AIC

9. Opsi Pengembangan Jika Lolos Final

Jika lolos final, core pipeline preliminary tetap dipertahankan. Pengembangan dipilih sebagai opsi yang memperkuat real-time use case, bukan menambah fitur SaaS generik. Prioritas utama adalah mengganti Replay JSON dengan comment stream API/scraper real-time; opsi lain dikerjakan sesuai waktu hackathon.

11. Sumber dan Catatan Audit

# 1. Konteks dan Tujuan Sistem

Masalah utama yang ditargetkan LiveCoachHub bukan sekadar “seller tidak sempat membaca komentar”. Seller masih dapat membaca komentar secara manual, tetapi sulit mengubah puluhan micro-signal yang datang cepat menjadi keputusan yang tepat: kapan menjelaskan ukuran, kapan mengonfirmasi stok, kapan membahas promo, atau kapan menjelaskan material.

Karena itu LiveCoachHub diposisikan sebagai decision-support copilot. Sistem tidak mengambil alih host dan tidak otomatis membalas komentar. Sistem membaca pola komentar, mengidentifikasi kondisi audience, lalu memberikan next-best-action dan suggested seller script yang dapat dipilih host. Sistem juga membedakan antara “apa yang ramai” dan “apa yang penting”: tren mayoritas menentukan main coaching, sedangkan komentar individual yang bernilai tinggi dapat tetap diangkat sebagai priority comment.

# 2. Subproyek Teman 1 — Fashion Intent NLP

Repository: https://github.com/RajendraF1/fashion-intent-nlp

Peran subproyek ini adalah Audience Understanding Engine, yaitu lapisan yang membaca satu komentar pada satu waktu dan mengubahnya menjadi intent terstruktur. Secara nonteknis, model ini menjawab pertanyaan: “Penonton sedang bertanya atau berniat tentang apa?”

## 2.1 Teknologi utama

Model utama menggunakan IndoBERT (indobenchmark/indobert-base-p1), yaitu model bahasa berbasis arsitektur Transformer/BERT yang sudah terlebih dahulu mempelajari pola Bahasa Indonesia. Model kemudian di-fine-tune untuk tugas khusus klasifikasi intent komentar live-commerce fashion. “Fine-tuning” berarti model dasar tidak dilatih dari nol; bobotnya disesuaikan menggunakan dataset tugas khusus agar mampu membedakan intent yang dibutuhkan LiveCoachHub.

Repository juga memuat komponen pengambilan komentar TikTok Live, preprocessing, dataset, konfigurasi training, evaluasi, CLI inference, dan REST inference service. Untuk preliminary, fungsi yang paling penting adalah endpoint inference: teks komentar masuk, lalu model mengembalikan label intent dan confidence.

## 2.2 Taksonomi intent

Catatan penting: walaupun data sentiment mungkin terdapat dalam data sumber, pipeline inference yang diaudit untuk integrasi LiveCoachHub berfokus pada intent classification. Karena itu preliminary sebaiknya tidak mengklaim sentiment analysis sebagai kemampuan utama kecuali memang ditambahkan dan diuji secara eksplisit.

## 2.3 Dataset dan proses training

Repository mendokumentasikan dataset final sekitar 10.000 komentar. Sebagian komentar berasal dari scraping live-fashion nyata, sedangkan sisanya dikembangkan untuk menyeimbangkan kelas berdasarkan pola komentar yang ada. Pipeline dataset mencakup cleaning, relabeling, deduplication, validation, dan stratified split untuk train/validation/test. Model kemudian di-fine-tune dan dievaluasi menggunakan metrik klasifikasi seperti Macro F1, precision, recall, dan confusion matrix.

Secara mudah: dataset mengajari model contoh “bahasa penonton live”. Model berlatih melihat ribuan komentar dan belajar bahwa frasa seperti “BB 55 size apa” lebih dekat ke size_recommendation daripada price_inquiry.

## 2.4 Input dan output NLP

Input yang diharapkan adalah satu atau beberapa teks komentar. Endpoint inference mendukung batch, sehingga backend LiveCoachHub dapat mengirim beberapa komentar sekaligus jika dibutuhkan.

Model melakukan tokenization (mengubah teks menjadi token yang dipahami BERT), inference, lalu softmax untuk memperoleh probabilitas setiap kelas. Label dengan probabilitas tertinggi dipilih. Jika confidence di bawah threshold, hasil dapat dialihkan menjadi kategori fallback seperti “other”.

## 2.5 Apa yang belum dilakukan NLP

NLP tidak menentukan tindakan seller. Ia hanya memahami intent komentar.

NLP tidak membutuhkan LSTM dan tidak memprediksi engagement masa depan.

NLP tidak seharusnya langsung menghasilkan kalimat coaching.

Untuk integrasi, setiap event komentar perlu membawa comment_id, user_id anonim, timestamp, dan text. Hasil NLP kemudian mempertahankan comment_id/user_id agar spam filtering, unique-user counting, evidence, dan priority comment dapat dilacak dengan benar.

# 3. Subproyek Teman 2 — Decision + Grounded Response Engine

Repository: https://github.com/fauzovsky/M3-SCR-3

Subproyek kedua bukan sekadar “LLM”. Ia lebih tepat dipahami sebagai rangkaian decision-and-response layer yang terdiri dari Action Engine, Knowledge Base, response dataset, QLoRA fine-tuned LLM, dan Validator. Dengan kata lain: komponen ini menentukan apa yang perlu dilakukan host, memilih fakta yang boleh disebut, lalu menyusun kalimat yang natural dan memeriksanya kembali.

## 3.1 Action Engine — memilih tindakan, bukan menulis kalimat

Action Engine menerima hasil agregasi dalam window waktu, bukan komentar mentah satu per satu. Ia menggunakan rule/threshold untuk menentukan satu Audience State dan satu ActionDecision. Pendekatan rule-based ini sengaja sederhana dan explainable: juri maupun tim dapat melihat mengapa sebuah action dipilih.

Konfigurasi yang diaudit menggunakan pola threshold seperti minimum jumlah dukungan komentar dan minimum confidence. Jika tidak ada sinyal yang cukup kuat, engine dapat memilih NO_CLEAR_SIGNAL / NO_ACTION. Jika beberapa state lolos bersamaan, priority_rank dan confidence dipakai untuk tie-breaking.

## 3.2 Knowledge Base — sumber fakta yang boleh dipakai

Knowledge Base adalah kumpulan fakta produk terstruktur dalam JSON. Anggap seperti “buku fakta mini” yang hanya berisi informasi yang diizinkan untuk dipakai LLM. Tujuannya adalah grounding: LLM tidak boleh mengarang ukuran, harga, stok, material, atau promo yang tidak tersedia di data produk.

Knowledge Base yang diaudit menggunakan satu mock product, yaitu Essential Cotton T-Shirt. Fakta disusun menggunakan identifier seperti fact_id, kategori/fact type, trigger atau konteks, serta value. Kategori dapat mencakup deskripsi produk, material, panduan ukuran, warna, stok, harga, dan promo.

Ketika Action Engine memilih SHOW_SIZE_GUIDE, backend tidak mengirim seluruh knowledge base ke LLM. Backend cukup mengambil fakta dengan tipe yang dibutuhkan, misalnya SIZE_GUIDE_DEWASA. Ketika action = SHOW_PROMO_INFO, backend mengambil fakta harga/promo. Ini membuat input LLM lebih kecil, lebih terarah, dan lebih mudah divalidasi.

Catatan metodologis: beberapa nilai size chart dalam repository ditandai sebagai working value untuk demonstrasi dan belum seluruhnya diverifikasi sebagai standar resmi. Karena itu proposal/demo sebaiknya menyebutnya sebagai mock product catalog untuk uji grounding, bukan fakta brand nyata atau klaim standar resmi.

## 3.3 Response Dataset + QLoRA LLM — mengubah action menjadi bahasa host

Model bahasa yang digunakan adalah Qwen2.5-1.5B-Instruct yang diadaptasi dengan QLoRA. QLoRA adalah teknik fine-tuning hemat memori: model dasar dikompresi/quantized dan hanya sejumlah kecil parameter adapter LoRA yang dilatih. Hasilnya, tim dapat menyesuaikan gaya dan format respons tanpa harus melatih seluruh model besar dari awal.

Response dataset berisi contoh pasangan input-output terstruktur. Input menjelaskan selected_action, audience_state, evidence comments, product_facts, tone, dan batas kata. Output berisi seller script, daftar fact_id yang dipakai, claims yang mengaitkan kalimat dengan fakta, serta needs_fallback.

Pemisahan fungsi ini penting: Action Engine menentukan “WHAT to say/do”, sedangkan LLM menentukan “HOW to say it”. Dengan desain ini, LLM tidak dibiarkan bebas menentukan strategi bisnis sendiri.

## 3.4 Validator — pagar keamanan output LLM

Validator memeriksa apakah output LLM mengikuti struktur JSON, tidak memasukkan fakta/angka yang tidak didukung, menggunakan fact_id yang benar, mematuhi batas kata, dan menandai fallback bila data tidak cukup. Jika gagal, sistem dapat melakukan retry satu kali; jika masih gagal, gunakan safe fallback. Strategi ini penting untuk latency live-commerce dan untuk bonus governance/responsible AI.

Catatan audit penting: laporan “60/60 passed” pada repository tidak boleh dipresentasikan sebagai accuracy LLM. Laporan tersebut memvalidasi response dataset/ideal output terhadap policy validator. Untuk mengklaim performa LLM, model harus benar-benar dijalankan pada test prompt baru, lalu output aktualnya dinilai: valid JSON rate, grounded claim rate, hallucination rate, dan fallback correctness.

# 4. Gap Integrasi Dua Repository

Secara konsep kedua repo cocok, tetapi saat ini belum otomatis koheren. Gap terbesar adalah kontrak data: intent keluaran IndoBERT berbeda dengan signal label yang diharapkan Action Engine.

Selain taxonomy mismatch, ada isu implementasi yang perlu dibereskan: path Action Engine mengharapkan action_rules.json sedangkan file yang diaudit bernama “action_rules (1).json”. Nama file harus distandardisasi agar engine dapat diinstansiasi tanpa error. QLoRA juga perlu benar-benar dilatih dan diuji end-to-end, lalu adapter dan hasil evaluasi aktual disimpan/didokumentasikan.

# 5. Rancangan LiveCoachHub Preliminary — Satu Pipeline Linear

Rancangan berikut mempertahankan pekerjaan kedua teman, hanya menambahkan integration layer dan frontend/backend orchestrator. Tidak ada LSTM dan tidak ada model ketiga yang tidak perlu.

Gambar 1. Pipeline preliminary LiveCoachHub.

### Tahap 1 — Live Session Replay

Backend membaca file replay JSON/JSONL yang berisi comment_id, user_id anonim, timestamp, dan text. Komentar tidak dimasukkan sekaligus; Replay Engine mengeluarkan event secara bertahap mengikuti waktu relatif hasil scraping. Agar demo cepat, replay speed dapat dipercepat, tetapi rolling window tetap memakai virtual/event time sehingga logika tidak berubah.

### Tahap 2 — Preprocessing + Spam/Duplicate Filter

Sebelum komentar memengaruhi trend, backend melakukan normalisasi teks dan mendeteksi spam/duplikasi. Komentar identik atau hampir identik dari user yang sama dalam rentang pendek tidak diberi bobot penuh. Untuk agregasi, unique_user_count dipakai bersama support_count agar satu akun tidak dapat menciptakan tren palsu.

### Tahap 3 — NLP Intent Classification

Setiap komentar yang lolos preprocessing dikirim ke service IndoBERT. Hasilnya intent + confidence. comment_id dan user_id dipertahankan sehingga evidence, unique-user support, serta priority event dapat dilacak.

### Tahap 4 — Dual Signal Layer: Trend Lane + Priority Lane

Setelah NLP, hasil dibaca melalui dua jalur. Trend Lane mengagregasi sinyal dalam rolling window 60 detik dan menghitung support_count, unique_user_count, avg_confidence, serta evidence_comment_ids. Priority Lane memeriksa komentar individual yang bernilai tinggi, terutama purchase_intent ber-confidence tinggi, agar komentar penting tetap muncul walaupun tidak dominan.

### Tahap 5 — Taxonomy Adapter

Label NLP dipetakan ke signal vocabulary yang dimengerti Action Engine. Adapter mempertahankan dua tipe keluaran: canonical trend signal dan priority event.

### Tahap 6 — Action Engine

Engine memilih satu main audience state dan satu next-best-action dari Trend Lane menggunakan threshold + priority. Secara paralel, Priority Event dapat dikirim sebagai alert terpisah di UI tanpa mengganti main coaching secara terus-menerus. Jika tidak ada trend yang cukup kuat, main state dapat NO_ACTION sementara priority comment tetap dapat ditampilkan.

### Tahap 7 — Fact Retrieval

required_fact_types dari main action atau priority response digunakan untuk mengambil hanya fakta produk yang relevan dari Knowledge Base.

### Tahap 8 — QLoRA LLM

Action/state, evidence comments, product facts, tone, dan max_words dikirim ke LLM. Model menghasilkan seller script yang grounded. LLM dipanggil ketika main action berubah atau ketika priority event membutuhkan suggested response, bukan untuk setiap komentar.

### Tahap 9 — Validator

Output dicek. PASS diteruskan; FAIL dapat retry sekali; kegagalan berikutnya menghasilkan safe fallback.

### Tahap 10 — Frontend

UI menampilkan raw comments, audience signals, current audience state, recommended action, suggested script, evidence/why, serta Priority Comment jika ada. Satu layar tetap cukup untuk preliminary.

## 5.1 Mekanisme Waktu Replay dan Rolling Window

Dataset replay diperlakukan sebagai rekaman event live. Jika timestamp komentar adalah 5, 12, 19, dan 41 detik, Replay Engine mengirim komentar pada virtual time tersebut. Rolling window 60 detik berarti pada virtual time t, hanya komentar dengan timestamp di rentang t-60 sampai t yang dihitung. Analisis dapat diperbarui setiap 5 detik. Replay speed 5x hanya mempercepat waktu nyata demonstrasi; event time tetap 5, 12, 19, dan 41 sehingga hasil agregasi konsisten.

## 5.2 Contoh alur end-to-end

Contoh: dalam 60 detik terdapat tiga pertanyaan ukuran dari tiga user berbeda dan satu komentar “kalau XL ready aku checkout sekarang”. Trend Lane menghasilkan SIZE_VARIANT dengan unique-user support = 3 sehingga main state menjadi SIZE_FRICTION dan action = SHOW_SIZE_GUIDE. Pada saat yang sama Priority Lane menangkap purchase_intent sebagai high-value comment. Frontend menampilkan main coaching “Show Size Guide” serta alert terpisah “Potential buyer needs attention”. Dengan demikian sistem tidak harus memilih antara tren mayoritas dan komentar penting.

# 6. Kontrak Data Antar-Komponen

Kontrak data perlu dibekukan lebih awal agar setiap anggota dapat bekerja independen tanpa merusak integrasi. Nama field sebaiknya disepakati dan dipertahankan sampai submission.

## 6.1 Comment Event

## 6.2 NLP Result

## 6.3 Window Signal

### 6.4 Priority Event

## 6.5 Action Decision

## 6.6 LLM Request/Response

Gunakan struktur yang sudah dibangun repo M3: selected_action, audience_state, evidence_comments, product_facts, tone, max_words → response_text, used_fact_ids, claims, needs_fallback.

# 7. Rancangan UI, Use Case, dan Skenario Demo

Preliminary sebaiknya hanya memiliki satu halaman kerja, karena rulebook membatasi frontend pada interaksi inti input → output AI. User cukup memilih/start replay session. Semua analisis berlangsung otomatis.

## 7.1 Empat use case yang dikunci untuk preliminary

Aturan anti-spam preliminary: komentar repetitif dari user yang sama tidak dihitung penuh; Trend Lane mempertimbangkan unique_user_count. Priority Lane hanya mengangkat event ber-confidence tinggi dan tidak otomatis mengganti main audience state.

Purchase intent tidak lagi hanya menjadi buying signal pasif. Pada preliminary ia dapat menjadi Priority Event jika confidence tinggi. Priority Event ditampilkan sebagai alert terpisah dari main coaching, sehingga satu calon pembeli bernilai tinggi tidak hilang hanya karena intent lain lebih dominan. Action space utama tetap empat use case agar scope tidak overbuilt.

# 8. Kepatuhan terhadap Batas Preliminary AIC

Rulebook terbaru menegaskan preliminary bukan tempat membangun SaaS lengkap. Fokusnya adalah core inference yang reproducible, backend sinkron, UI inti, dan arsitektur yang dapat dilanjutkan ke final.

Struktur repository submission sebaiknya berupa satu monorepo LiveCoachHub. Dua repository teman dapat tetap menjadi bukti development, tetapi panitia idealnya cukup melakukan clone satu repository utama dan menjalankan satu setup flow.

# 9. Opsi Pengembangan Jika Lolos Final

Jika lolos final, core pipeline preliminary tetap dipertahankan. Pengembangan dipilih sebagai opsi yang memperkuat real-time use case, bukan menambah fitur SaaS generik. Prioritas utama adalah mengganti Replay JSON dengan comment stream API/scraper real-time; opsi lain dikerjakan sesuai feedback mentor dan waktu hackathon.

## 9.1 Opsi fitur final

Catatan: tidak semua opsi harus dikerjakan. Fitur final dipilih berdasarkan feedback mentor, waktu hackathon, dan dampaknya terhadap core value LiveCoachHub.

# 10. Definition of Done dan Prioritas Pengerjaan

MVP preliminary dianggap selesai hanya jika seluruh pipeline berjalan tanpa hand-off manual antaranggota. Kriteria paling praktis adalah fresh clone repository utama → docker compose up → replay berjalan → output AI muncul.

## 10.1 Definition of Done end-to-end

Load replay comments secara bertahap berdasarkan virtual/event timestamp.

Normalisasi dan filter spam/duplikasi, lalu classify komentar dengan fine-tuned IndoBERT.

Aggregate canonical signals pada rolling window 60 detik menggunakan support_count, unique_user_count, avg_confidence, dan evidence.

Detect satu main audience state atau NO_ACTION melalui Trend Lane.

Detect Priority Event secara paralel dan select satu main recommended action.

Retrieve fakta produk sesuai required_fact_types.

Generate grounded seller script dengan QLoRA LLM.

Validate output; retry/fallback bila perlu.

Display komentar, audience signals, main state/action, suggested script, evidence, validator status, dan priority comment pada satu screen.

Seluruh flow dapat dijalankan secara reproducible melalui README + Docker Compose.

# 11. Sumber dan Catatan Audit

Dokumen ini disusun berdasarkan guidebook AIC COMPFEST 18 terbaru yang diberikan pada proyek, serta audit struktur dua repository berikut. Karena repository aktif dapat berubah, lakukan re-audit singkat sebelum freeze submission.

Repository NLP: RajendraF1/fashion-intent-nlp

Repository Decision/LLM: fauzovsky/M3-SCR-3

Guidebook utama: [AIC] AI Innovation Challenge (5).pdf — khususnya halaman teknis penyisihan, deliverables, batas MVP, teknis final, dan rubrik penilaian.

# Lampiran A — Glosarium Istilah Teknis

| Kompetisi | AI Innovation Challenge — COMPFEST 18 |
| --- | --- |
| Tema | AI for the Backbone of the Economy |
| Subtema | Smart Commerce |
| Dokumen | Rancangan teknis-produk internal untuk penyisihan menuju final |

| Pertanyaan | Komponen yang menjawab | Bahasa sederhana |
| --- | --- | --- |
| Apa yang sedang ditanyakan audiens? | Fine-tuned IndoBERT | Membaca komentar dan memberi label intent. |
| Apakah pola ini cukup kuat untuk dianggap penting? | Rolling-window aggregator | Menghitung berapa kali sinyal muncul dalam 60 detik. |
| Host sebaiknya melakukan apa? | Action Engine | Memilih satu tindakan berdasarkan aturan dan prioritas. |
| Fakta apa yang boleh disebut? | Knowledge Base | Menyediakan fakta produk yang sudah ditentukan. |
| Bagaimana host mengucapkannya dengan natural? | QLoRA LLM | Mengubah action + fakta menjadi kalimat singkat. |
| Apakah kalimat aman dan grounded? | Validator | Mengecek struktur, fakta, angka, dan fallback. |
| Apakah komentar berulang berasal dari spam? | Spam/Duplicate Filter | Mencegah satu akun mengubah tren hanya dengan mengirim komentar yang sama berulang kali. |
| Apakah ada satu komentar penting walau tidak dominan? | Priority Detector | Mengangkat high-value comment seperti purchase intent tanpa menunggu intent menjadi mayoritas. |

| Intent | Arti praktis | Contoh komentar |
| --- | --- | --- |
| product_inquiry | Pertanyaan detail produk | “bahannya apa?”, “modelnya oversized?” |
| size_inquiry | Menanyakan ukuran yang tersedia | “size XL ada?” |
| size_recommendation | Meminta rekomendasi ukuran | “BB 60 TB 165 cocok size apa?” |
| color_inquiry | Menanyakan warna/varian warna | “hitam ada kak?” |
| price_inquiry | Harga, diskon, promo, ongkir | “promo hari ini apa?” |
| stock_availability | Ketersediaan/restock | “stok M masih ada?” |
| purchase_intent | Sinyal niat membeli/checkout | “aku langsung CO ya kak” |
| not_relevant | Sapaan, spam, emoji, obrolan tidak relevan | “halo kak”, “wkwk” |

| INPUT<br>{<br>"texts": [<br>"bb 60 tb 165 cocok size apa",<br>"warna hitam masih ready?",<br>"promo hari ini ada kak?"<br>],<br>"threshold": 0.70<br>} |
| --- |

| OUTPUT<br>{<br>"results": [<br>{"text":"bb 60 tb 165 cocok size apa", "intent":"size_recommendation", "confidence":0.94},<br>{"text":"warna hitam masih ready?", "intent":"color_inquiry", "confidence":0.91},<br>{"text":"promo hari ini ada kak?", "intent":"price_inquiry", "confidence":0.90}<br>]<br>} |
| --- |

| {<br>"intent": "SIZE_VARIANT",<br>"support_count": 4,<br>"unique_user_count": 3,<br>"avg_confidence": 0.91,<br>"evidence_comment_ids": ["CMT-018", "CMT-014"]<br>} |
| --- |

| Audience State | Selected Action | Makna bisnis |
| --- | --- | --- |
| SIZE_FRICTION | SHOW_SIZE_GUIDE | Banyak audiens bingung ukuran; host sebaiknya memberi panduan ukuran. |
| STOCK_COLOR_CONCERN | CONFIRM_STOCK_COLOR | Pertanyaan stok/warna dominan; host sebaiknya mengonfirmasi ketersediaan. |
| MATERIAL_SAFETY_CONCERN | EXPLAIN_MATERIAL | Audiens perlu penjelasan material/safety/kenyamanan. |
| PRICE_FRICTION | SHOW_PROMO_INFO | Pertanyaan harga/promo dominan; host sebaiknya memberi informasi promo/harga. |
| NO_CLEAR_SIGNAL | NO_ACTION | Belum ada pola kuat; sistem tidak memaksa rekomendasi. |

| CONTOH OUTPUT ACTION ENGINE<br>AudienceSnapshot:<br>{<br>"state": "SIZE_FRICTION",<br>"window_seconds": 60,<br>"state_confidence": 0.91,<br>"signals": {"support_count": 4},<br>"evidence_comment_ids": ["CMT-018", "CMT-014"]<br>}<br>ActionDecision:<br>{<br>"selected_action": "SHOW_SIZE_GUIDE",<br>"action_score": 0.88,<br>"required_fact_types": ["SIZE_GUIDE_DEWASA"],<br>"reason": "4 pertanyaan ukuran muncul dalam 60 detik terakhir."<br>} |
| --- |

| CONTOH STRUKTUR FAKTA<br>{<br>"fact_id": "FACT-TS01-SIZE-M",<br>"fact_type": "SIZE_GUIDE_DEWASA",<br>"value": "...panduan ukuran M yang sudah ditetapkan..."<br>} |
| --- |

| INPUT LLM<br>{<br>"selected_action": "SHOW_SIZE_GUIDE",<br>"audience_state": "SIZE_FRICTION",<br>"evidence_comments": [<br>"bb 55 ambil m atau l?",<br>"aku bb 55 cocoknya apa ya"<br>],<br>"product_facts": [<br>{"fact_id":"FACT-TS01-SIZE-M", "value":"..."}<br>],<br>"tone": "santai",<br>"max_words": 35<br>} |
| --- |
| OUTPUT LLM<br>{<br>"response_text": "...kalimat singkat yang bisa diucapkan host...",<br>"used_fact_ids": ["FACT-TS01-SIZE-M"],<br>"claims": [<br>{"fact_id":"FACT-TS01-SIZE-M", "claim_text":"..."}<br>],<br>"needs_fallback": false<br>} |

| Output NLP | Yang diharapkan M3 | Solusi Preliminary |
| --- | --- | --- |
| size_inquiry | SIZE_VARIANT | Map langsung ke SIZE_VARIANT. |
| size_recommendation | SIZE_VARIANT | Map langsung ke SIZE_VARIANT. |
| color_inquiry | COLOR_QUERY | Map langsung ke COLOR_QUERY. |
| stock_availability | STOCK_QUERY | Map langsung ke STOCK_QUERY. |
| price_inquiry | PRICE_QUERY / PROMO_QUERY | Map ke PRICE_QUERY; promo tetap ditangani SHOW_PROMO_INFO. |
| purchase_intent | Belum ada action khusus | Gunakan pada dua jalur: sebagai buying signal di Trend Lane dan sebagai Priority Event bila confidence tinggi. |
| product_inquiry | MATERIAL_QUERY / lainnya | Gunakan material gate sederhana; hanya pertanyaan material yang memicu MATERIAL_QUERY. |
| not_relevant | Tidak perlu action | Ignore dari Action Engine; komentar repetitif/spam juga tidak diberi bobot penuh pada agregasi. |

| {<br>"comment_id": "CMT-018",<br>"user_id": "USR-015",<br>"timestamp": 35,<br>"text": "bb 55 cocok size apa"<br>} |
| --- |

| {<br>"comment_id": "CMT-018",<br>"user_id": "USR-015",<br>"intent": "size_recommendation",<br>"confidence": 0.94<br>} |
| --- |

| {<br>"intent": "SIZE_VARIANT",<br>"support_count": 4,<br>"unique_user_count": 3,<br>"avg_confidence": 0.91,<br>"evidence_comment_ids": ["CMT-018", "CMT-014"]<br>} |
| --- |

| {<br>"comment_id": "CMT-044",<br>"user_id": "USR-021",<br>"intent": "purchase_intent",<br>"confidence": 0.96,<br>"priority_level": "HIGH",<br>"text": "kalau XL ready aku checkout sekarang"<br>} |
| --- |

| {<br>"selected_action": "SHOW_SIZE_GUIDE",<br>"action_score": 0.88,<br>"required_fact_types": ["SIZE_GUIDE_DEWASA"],<br>"reason": "4 pertanyaan ukuran muncul dalam 60 detik terakhir."<br>} |
| --- |

| Zona UI | Isi | Tujuan |
| --- | --- | --- |
| Live Comments | Komentar + timestamp | Menunjukkan input nyata dan menjaga keterlacakan evidence. |
| Audience State | State aktif + support count + unique users / 60 detik | Menunjukkan pola mayoritas yang tidak mudah dimanipulasi spam. |
| Recommended Action | Satu action utama | Memberi keputusan operasional yang jelas. |
| Suggested Script | Kalimat singkat grounded | Membantu host langsung bertindak. |
| Why / Evidence | Comment IDs + contoh komentar | Membuat rekomendasi explainable dan audit-able. |
| Supporting Signal | Mis. purchase intent count | Memberi konteks tanpa menambah action space premature. |
| Priority Comment | Komentar high-value individual + intent + confidence | Memastikan komentar penting tetap terlihat walau tidak dominan. |
| Spam/Filter Status | Indikator komentar terfilter atau effective support | Menjelaskan bahwa agregasi memakai sinyal unik, bukan raw spam count. |

| Scenario | Trigger utama | Action | Fakta LLM |
| --- | --- | --- | --- |
| Size confusion | size_inquiry + size_recommendation | SHOW_SIZE_GUIDE | Size guide |
| Stock/color concern | stock_availability + color_inquiry | CONFIRM_STOCK_COLOR | Stock/warna |
| Material question | subset material dari product_inquiry | EXPLAIN_MATERIAL | Material/comfort/safety facts |
| Price/promo interest | price_inquiry | SHOW_PROMO_INFO | Harga/promo |

| Ketentuan | Implementasi LiveCoachHub |
| --- | --- |
| Frontend hanya alur inti | Satu halaman replay → trend state → main action → script/evidence + priority comment. |
| Backend sinkron | Replay, spam filter, rolling aggregation, priority detection, action, retrieval, LLM, dan validator berjalan sinkron; tanpa infra produksi. |
| AI fokus core inference | IndoBERT inference + deterministic Trend/Priority logic + Action Engine + QLoRA generation + validator. |
| Pre-trained/API boleh, model wajib disesuaikan | IndoBERT di-fine-tune untuk commerce intent; Qwen diadaptasi dengan QLoRA. |
| Reproducible lokal | Gunakan replay data dan Docker Compose; jangan bergantung live TikTok saat cross-check. |
| README jelas | Jelaskan setup, model artifacts, input format, run replay, endpoint, dan limitation. |
| MVP tidak overbuilt | Tidak ada login, history dashboard, LSTM, multi-platform, payment, atau infra produksi. |

| LiveCoachHub/<br>├── frontend/<br>├── backend/<br>│   ├── replay/<br>│   ├── preprocessing/<br>│   ├── spam_filter/<br>│   ├── rolling_window/<br>│   ├── priority_detector/<br>│   ├── taxonomy_adapter/<br>│   ├── action_engine/<br>│   ├── knowledge/<br>│   └── validator/<br>├── ai/<br>│   ├── intent_classifier/<br>│   └── grounded_llm/<br>├── data/<br>│   ├── replay/<br>│   └── product_facts/<br>├── models/<br>├── docs/<br>├── docker-compose.yml<br>└── README.md |
| --- |

| Opsi | Nilai tambah | Implementasi ringkas |
| --- | --- | --- |
| Real-time Comment Source | Mengganti simulasi dengan kondisi live nyata. | API/scraper live → format Comment Event yang sama; pipeline setelahnya tidak berubah. |
| Expanded Priority Events | Menangkap lebih banyak komentar bernilai tinggi. | Tambahkan rules untuk stock+purchase, complaint penting, atau demo request. |
| Multi-label Intent | Satu komentar dapat memiliki lebih dari satu maksud. | Contoh: stock_availability + purchase_intent sekaligus. |
| Action Feedback & Memory | Mengurangi rekomendasi repetitif. | Applied/Ignore + timestamp + cooldown per action. |
| Multi-product Knowledge Base | Lebih dekat dengan skenario seller nyata. | Knowledge base per produk + pemilihan produk aktif. |

| Prioritas | Pekerjaan | Kriteria selesai |
| --- | --- | --- |
| P0 | Bekukan taxonomy adapter | Semua label NLP yang dipakai Action Engine memiliki mapping jelas. |
| P0 | Perbaiki action_rules path/name | ActionEngine() dapat start tanpa file-not-found. |
| P0 | Run evaluasi IndoBERT aktual | Macro-F1, per-class metrics, confusion matrix terdokumentasi. |
| P0 | Run QLoRA training + inference aktual | Adapter terbentuk dan inference test terhadap prompt baru terdokumentasi. |
| P0 | Bangun orchestrator backend | Comment → NLP → window → action → facts → LLM → validator berjalan otomatis. |
| P0 | Docker Compose | Fresh clone dapat menjalankan aplikasi sesuai README. |
| P1 | Frontend satu halaman | Komentar, state, action, script, evidence terlihat jelas. |
| P1 | Replay scenario dengan story arc | Empat use case muncul secara terkontrol dalam demo. |
| P1 | Evaluation LLM yang benar | Ukur JSON validity, grounded claim rate, hallucination/fallback correctness. |
| P2 | UI polish dan animasi ringan | Dilakukan setelah P0/P1 stabil. |
| P0 | Bangun replay event-time + spam filter | JSON diputar sesuai virtual timestamp; duplicate/user spam tidak mendominasi agregasi. |
| P0 | Bangun Trend Lane + Priority Lane | Main audience state dan priority comment dapat muncul bersamaan secara konsisten. |
| P1 | UI priority comment | Main coaching dan high-value comment terlihat jelas tanpa saling mengganti. |

| Istilah | Penjelasan sederhana |
| --- | --- |
| NLP (Natural Language Processing) | Teknologi agar komputer dapat memahami dan mengolah bahasa manusia. |
| BERT / IndoBERT | Model Transformer yang memahami konteks kata; IndoBERT dilatih khusus Bahasa Indonesia. |
| Intent classification | Mengelompokkan komentar berdasarkan maksud, misalnya tanya ukuran atau berniat membeli. |
| Confidence | Nilai keyakinan model terhadap label yang dipilih. |
| Rolling window | Cara melihat data hanya pada rentang waktu terakhir, misalnya 60 detik yang terus bergeser. |
| Action Engine | Logika yang mengubah sinyal audience menjadi satu tindakan seller. |
| Knowledge Base | Kumpulan fakta produk terstruktur yang menjadi sumber kebenaran bagi LLM. |
| LLM | Large Language Model; model bahasa yang dapat menghasilkan teks natural. |
| QLoRA | Teknik fine-tuning LLM yang hemat memori dengan quantization + LoRA adapters. |
| Grounding | Membatasi output LLM agar hanya menggunakan fakta yang tersedia. |
| Validator | Komponen yang memeriksa apakah output memenuhi struktur dan aturan. |
| Fallback | Jawaban aman/cadangan ketika sistem tidak punya fakta cukup atau output gagal validasi. |
| Docker Compose | Cara menjalankan beberapa service/container aplikasi dengan satu konfigurasi yang reproducible. |
| Human-in-the-loop | AI memberi rekomendasi, tetapi manusia tetap memutuskan menerima atau menolak. |
| Spam/Duplicate Filter | Aturan yang mencegah komentar repetitif dari user yang sama memberi bobot berlebihan pada tren. |
| Unique-user count | Jumlah akun unik yang mendukung sebuah sinyal; membantu membedakan tren nyata dari spam satu akun. |
| Trend Lane | Jalur agregasi untuk mengetahui pola mayoritas audiens dalam rolling window. |
| Priority Lane | Jalur terpisah untuk mengangkat komentar tunggal bernilai tinggi walau tidak dominan. |
| Virtual/Event time | Waktu asli relatif dari dataset replay yang dipakai untuk simulasi dan rolling window, meski replay dipercepat. |
