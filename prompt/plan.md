Baik, gue akan kasih **BRUTAL MVP PLAN** yang bisa lo **copy-paste langsung ke Cursor** sebagai blueprint awal.
Ini **straight-to-the-point**, **tanpa basa-basi**, dan **tanpa “fluff”**.
Ini *bukan* high-level bullshit — ini *rencana implementasi nyata* buat ngebangun bot analisa saham berbasis OHLCV + LLM.

---

# **🔥 MVP SPEC — STOCK ANALYSIS AI (Cursor-Ready Blueprint)**

*(You said “don’t screw anything up” — so gue bikin se-presisi mungkin.)*

---

## **1. MVP GOAL (JELAS & TERUKUR)**

**Membuat sistem yang:**

1. User input: ticker saham Indonesia (ex: MDLA, BBCA, ASII).
2. Backend fetch OHLCV dari Yahoo Finance.
3. Backend hitung indikator dasar:

   * EMA20/50
   * RSI
   * MACD
   * Support/Resistance (simple swing high/low)
   * Volume profile sederhana
4. Backend feeding summarized market data ke LLM.
5. LLM output laporan **singkat** (bukan panjang seperti contoh awal).
6. Sistem limit request per user (per-plan).
7. Dasbor sederhana: input ticker → output laporan.

**That's MVP.**
Gak usah mikir screener, backtest, AI prediction — nanti.

---

# **2. TECH STACK (MVP VERSION — SIMPLE & MURAH)**

### **Backend**

* **Python 3.11+**
* **FastAPI** (cepat, clean, modern)
* **yfinance** (OHLCV)
* **pandas + numpy** (perhitungan indikator)
* **pydantic** (model schema)
* **OpenAI SDK** (LLM)
* **PostgreSQL / Supabase** (auth, quota tracking)

### **Frontend**

* Next.js 14
* TailwindCSS
* shadcn/ui
* NextAuth (atau Supabase Auth)

### **Deployment**

* **Frontend:** Vercel
* **Backend:** Railway / Fly.io
* **DB:** Supabase (recommended)

---

# **3. SYSTEM ARCHITECTURE (SINGKAT, JELAS)**

```
[User]
   |
   v
[Next.js Frontend]
   |
   v
[FastAPI Backend: /analyze?ticker=MDLA]
   |
   |- Fetch OHLCV (yfinance)
   |- Compute indicators
   |- Summarize numeric data
   v
[OpenAI LLM: gpt-4o-mini]
   |
   v
[FastAPI returns JSON]
   |
   v
[Frontend render report]
```

---

# **4. REQUIRED API ENDPOINTS (MVP)**

### **POST /analyze**

Input:

```json
{
  "ticker": "MDLA",
  "user_id": "123"
}
```

Output:

```json
{
  "ticker": "MDLA",
  "ohlcv_days": 90,
  "indicators": { ... },
  "ai_report": "..."
}
```

---

# **5. PYTHON BACKEND — FOLDER STRUCTURE (Cursor-Ready)**

```
/backend
  /app
    main.py
    routers/
      analyze.py
    services/
      fetch_data.py
      indicators.py
      llm.py
      quota.py
    models/
      schema.py
    utils/
      cache.py
```

---

# **6. BACKEND — CORE FUNCTIONS (INI WAJIB ADA)**

*(Just copy to Cursor and implement satu-satu)*

### **fetch_data.py**

* Function: `get_ohlcv(ticker: str, days: int = 90)`

### **indicators.py**

* Function: `compute_indicators(df)`

  * EMA20, EMA50
  * RSI
  * MACD
  * Support/Resistance (simple pivot)
  * Volume avg

### **llm.py**

* Function: `generate_report(data: dict)`
* Use `gpt-4o-mini` (hemat cost but cukup pintar)

### **quota.py**

* Function: `check_quota(user_id)`
* Function: `decrement_quota(user_id)`

---

# **7. LLM PROMPT (MASTER PROMPT ENGINEER VERSION — HIGH IMPACT, LOW COST)**

*(Ini yang harus lo copy ke backend untuk prompt-nya.)*

```
You are StockAnalysisGPT, an objective financial analysis engine.

Your job: summarize key insights from the supplied OHLCV + indicators.

STRICT RULES:
- Keep output 4 paragraf maksimal.
- Jangan memberi saran investasi.
- Fokus pada tren, risiko, momentum, level penting.
- Gunakan bahasa Indonesia formal dan ringkas.
- Jangan bertele-tele atau membuat narasi panjang.

INPUT DATA:
{{data}}

OUTPUT FORMAT:
1. **Ringkasan Tren Utama**
2. **Level Penting (Support / Resistance / EMA / Volume)**
3. **Momentum & Risk Check**
4. **Kesimpulan Singkat (Tanpa rekomendasi eksplisit)**
```

Ini **prompt optimal** untuk hemat token + output tetap berkualitas.

---

# **8. FRONTEND FLOW (NEXT.JS)**

Sederhana:

**/dashboard**

* Input box: “Masukkan ticker saham”
* Button: “Analyze”
* Call backend
* Render JSON → tampilkan 4 section

**/account**

* Lihat sisa kuota
* Upgrade plan

---

# **9. QUOTA SYSTEM (simple algorithm MVP)**

1. Saat user hit `/analyze`
2. Backend cek database:

   * `requests_remaining > 0 ?`
3. Jika tidak:

   * return error `{ message: "Kuota habis" }`
4. Jika ada:

   * decrement quota
   * proses analysis

Selesai.

---

# **10. PAYMENT MVP (PAKAI INI AJA DULU)**

* Gunakan **Midtrans Snap** (Indonesia friendly)
* Setelah payment:

  * trigger webhook
  * tambah kuota user sesuai plan
* Done.

---

# **11. MVP PRIORITY LIST — TANPA NGALOR NGIDUL**

### **W1 — Build Core Backend**

* Setup FastAPI
* Endpoint /analyze
* Fetch OHLCV
* Indicators
* Prompt LLM

### **W2 — Auth + Quota**

* Supabase auth
* Quota table
* Quota middleware

### **W3 — Frontend**

* Simple dashboard
* Loading + error
* Display hasil

### **W4 — Payments**

* Midtrans
* Webhook
* Tier mapping

### **W5 — Deploy**

* Backend: Railway
* Frontend: Vercel
* Domain: analisisaham.ai
* SSL ready

That's MVP.

---

# **12. DONE.**

Ini blueprint yang bisa lo **paste ke Cursor dan langsung eksekusi**.
Bener-bener disusun untuk **build cepat**, **biaya rendah**, **risk minimal**, dan **tanpa overengineering**.

Kalau lo mau, gue bisa lanjut bikinin:

* file-by-file skeleton
* sample code backend
* full prompt library
* UI wireframe
* system architecture diagram

Cukup bilang: **“lanjut skeleton code”**.
