Siap. Gue bakal bikin **instruksi lengkap** untuk Cursor — *tanpa kode*, hanya **apa yang harus dibuat**, **alur teknis**, **struktur file**, **perkiraan endpoint**, **interaksi sistem**, dan **output yang diharapkan**.
Ini adalah blueprint final supaya Cursor bisa langsung membangun bot Telegram + backend + flow kuota + analisa saham.

Ini yang akan lo copy-paste ke Cursor.
Gue tulis **rapi, eksplisit, dan tidak ambigu**.

---

# ✅ **INSTRUKSI FINAL UNTUK CURSOR (MVP STOCK ANALYZER + TELEGRAM BOT)**

## **1. Tujuan Utama MVP**

Bangun sistem analisa saham berbasis AI yang bekerja via Telegram Bot dengan fitur:

* User kirim `/analisa TICKER`
* Sistem cek kuota berdasarkan user Telegram ID
* Fetch OHLCV dari yfinance
* Hitung indikator teknikal (EMA20/50, RSI, MACD, Support/Resistance)
* Backend minta LLM untuk membuat analisis profesional
* Telegram bot mengirim hasil + chart
* Jika kuota habis → tampilkan tombol upgrade

---

# **2. Komponen Sistem yang Wajib Dibuat**

**A. Backend FastAPI**
**B. Sistem Kuota**
**C. Integrasi yfinance + indikator**
**D. Integrasi LLM (Gemini 2.5 Flash)**
**E. Endpoint REST untuk dipanggil Telegram bot**
**F. Telegram Bot Worker (python-telegram-bot)**
**G. Chart generator (matplotlib)**
**H. Fallback report panjang jadi file .txt**

---

# **3. Struktur Folder (WAJIB)**

```
/backend
  |-- main.py
  |-- routers/
  |     |-- analyze.py
  |     |-- quota.py
  |-- services/
  |     |-- fetcher.py
  |     |-- indicators.py
  |     |-- ai.py
  |     |-- chart.py
  |-- models/
  |     |-- quota.py
  |-- database.py
  |-- utils.py

/bot
  |-- bot.py
  |-- handlers/
        |-- start.py
        |-- analisa.py
        |-- callbacks.py

.env
requirements.txt
```

---

# **4. Backend Requirements (Tanpa kode)**

## **4.1. Endpoint wajib**

### **POST /api/analyze**

Input:

```
{
  "ticker": "BBCA",
  "user_id": 123456
}
```

Output:

```
{
  "ticker": "BBCA",
  "indicators": {...},
  "ai_report": "string panjang",
  "chart_path": "string path"
}
```

### **GET /quota/check**

Params:

```
user_id=123
```

Output:

```
{
  "ok": true,
  "remaining": 29
}
```

### **POST /quota/decrement**

Input:

```
{ "user_id": 123 }
```

---

# **5. Alur Kerja Endpoint /api/analyze (WAJIB ikuti persis)**

1. Ambil OHLCV via yfinance (min. range 6 bulan)
2. Hitung indikator:

   * EMA20
   * EMA50
   * RSI
   * MACD
   * Level support/resistance
3. Generate chart line (harga + EMA) → simpan `chart_path`
4. Susun prompt LLM
5. Panggil Gemini 2.5 Flash
6. Return full report (tanpa dipersingkat)
7. Telegram bot nanti yang merangkum

---

# **6. Telegram Bot Requirements (Tanpa kode)**

## **6.1. Commands wajib**

* `/start` → kirim instruksi singkat
* `/analisa TICKER` → trigger analisa
* Callback buttons:

  * `upgrade`
  * `save:<ticker>`
  * `full:<ticker>`

---

## **6.2. Alur Telegram Bot Saat User Ketik /analisa BBCA**

1. Bot ambil Telegram user_id

2. Bot panggil `GET /quota/check`

3. Jika kuota habis →

   * Kirim pesan “Kuota habis, upgrade sekarang”
   * Kirim inline buttons → `[Upgrade]`
   * STOP

4. Jika kuota cukup:

   * Bot mengirim “Sedang memproses…”
   * Bot panggil `/quota/decrement` (early decrement)
   * Bot panggil backend `/api/analyze` timeout 25s
   * Terima JSON: indikator + laporan AI + chart_path

5. Bot mengirim ringkasan singkat:

   * Harga
   * Trend
   * Level penting
   * Rekomendasi singkat
     (ambil dari 800–1000 karakter pertama ai_report)

6. Bot mengirim chart.png

7. Jika report > 4000 chars →

   * simpan ke file `.txt`
   * kirim file sebagai document

8. Kirim inline button:
   `[Save Watchlist]  [Upgrade]  [Full Report]`

---

# **7. UX Format Pesan Telegram (WAJIB pakai template ini)**

### **Pesan ringkas**

```
🤖 ANALISA SAHAM — {TICKER}

📊 Harga Terakhir: {price}
📈 Trend: {trend_summary}

1) Level Penting
- Support: {support}
- Resistance: {resistance}
- Entry Ideal: {entry_range}

2) Momentum
- RSI: {rsi}
- EMA20/50: {ema_relation}
- MACD: {macd_summary}

3) Kesimpulan
{short_summary}

📎 Chart terlampir.
🔧 Gunakan tombol di bawah untuk aksi lainnya.
```

---

# **8. Ketentuan Chart Generator**

* Chart line 6 bulan
* Overlay EMA20 & EMA50
* Highlight terakhir 20 candle
* Save ke `/tmp/<ticker>_chart.png`
* Return path ke bot

---

# **9. Prompt LLM (WAJIB)**

Gunakan format:

**SYSTEM:**

```
You are an expert Indonesian stock analyst...
(Wajib isi lengkap sama seperti prompt yg sudah dibuat sebelumnya)
```

**USER:**

```
Ticker: {TICKER}
Indicators:
{json indicators lengkap}
```

LLM output minimal 4 bagian:

1. Momentum
2. Trend
3. Level penting
4. Rekomendasi aksi

---

# **10. Behavior Wajib**

* Semua error dari backend → bot jawab “Server sibuk, coba lagi”
* Jika model timeout → retry sekali dengan prompt lebih pendek
* Jika chart gagal → tetap kirim teks

---

# **11. Behavior Kuota**

* Decrement harus atomic
* Jika analisa gagal, backend boleh panggil `/quota/increment`
* Kuota default user baru: 3 request free
* Plan:

  * Rp50.000 → 30 request
  * Rp100.000 → 100 request
  * Rp500.000 → 1000 request

---

# **12. Output yang harus dihasilkan oleh Cursor**

Setelah instruksi ini, Cursor harus menghasilkan:

1. **Backend lengkap**: endpoint, service, chart, prompt, integration
2. **Telegram bot worker lengkap**
3. **Env template**
4. **Dokumentasi singkat cara run dev**
5. **Uji otomatis sederhana (health check)**
6. **Mampu memproses 3–5 analisa berturut-turut tanpa error**

---

# **13. Checklist jadi (Cursor harus centang semua ini)**

* [ ] API bekerja via FastAPI
* [ ] yfinance sukses fetch
* [ ] Indikator lengkap menghasilkan angka benar
* [ ] LLM terpanggil & respon masuk
* [ ] Chart muncul
* [ ] Telegram bot berhasil mengirim
* [ ] Kuota berkurang
* [ ] Report panjang bisa terkirim via .txt
* [ ] Model fallback berjalan
* [ ] Semua endpoint ter-test via curl/postman

---

# **14. Jika ada hal yang tidak bisa dikerjakan Cursor**

Instruksi buat Cursor:

> “Jika ada hal yang tidak dapat diimplementasikan atau ambigu, lakukan yang paling mendekati dengan asumsi paling aman dan dokumentasikan asumsi tersebut.”

---

# **15. Mode Output Cursor**

Instruksi terakhir:

> “Jangan membuat unit-test yang rumit. Jangan melakukan refactor besar. Fokus ke MVP siap digunakan.”

---