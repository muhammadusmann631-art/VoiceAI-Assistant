# Backend Ki Details (FastAPI & Python)

Yeh file backend ke saare components, libraries, APIs aur endpoints ki details Roman English mein explain karti hai.

---

## 1. Backend Mein Konsi Libraries Use Ho Rahi Hain?

Backend `backend/main.py` file FastAPI framework par chal raha hai. Ismein niche di gayi important libraries use ho rahi hain:

* **FastAPI:** Main web framework hai jis par saari APIs (endpoints) bani hui hain.
* **CORS Middleware:** Taake frontend (React app running on port 5173) backend (running on port 8000) se secure communication kar sake.
* **Pydantic (BaseModel):** API requests ke incoming JSON data validation ke liye.
* **Httpx:** Asynchronous HTTP client jo backend se external APIs (OpenAI and ElevenLabs) ko call karne ke liye use hota hai.
* **Dotenv (load_dotenv):** `.env` file se secure API keys (OpenAI, ElevenLabs) read karne ke liye.

---

## 2. Backend Ke Endpoints (APIs) Aur Unka Kaam

Backend mein 3 main API endpoints hain:

### A. `POST /transcribe`
* **Kaam:** Yeh user ke bolay hue audio ko text mein convert (transcribe) karta hai.
* **Details:** 
  1. Frontend isko audio blob (.webm format) send karta hai.
  2. Backend is file ko read kar ke **OpenAI Whisper-1 API** par send karta hai.
  3. OpenAI audio ko text mein badal kar wapas bhejta hai aur backend wahi text frontend ko return kar deta hai.

### B. `POST /extract-task`
* **Kaam:** Transcribed text se AI ke zariye tasks extract karta hai.
* **Details:**
  1. Frontend isko simple text bhejta hai.
  2. Backend **OpenAI GPT-4o-mini** ko call karta hai.
  3. GPT-4o-mini text se tasks ki list array JSON return karta hai.

### C. `POST /process-command`
* **Kaam:** Main voice workflow process karta hai (Add/Delete/Bye intents aur validation logic handle karta hai).
* **Details:**
  1. **Fuzzy Deletion Match:** Frontend active tasks ke user names ko backend par send karta hai. Agar user voice command par bolta hai *"Usman ke task delete kar do"*, to GPT active list se exact name match kar ke task delete kar deta hai.
  2. **Partial Task Warnings:** Agar user 5-6 tasks ek sath bole aur unmein se kisi task ka deadline time guzar chuka ho (past time), to backend valid tasks ko database mein assign karwa deta hai aur voice par specific warning deta hai (e.g. *"Abdullah ka bataya hua time guzar chuka hai. Aur baki Usman ko task de diya gaya hai"*).
  3. **Bye Intent:** Agar user *"bye"* bole, to session end status return karta hai.

### D. `POST /speak`
* **Kaam:** Text-to-Speech (TTS) conversion karta hai taake assistant user se bol kar baat kar sake.
* **Details:**
  1. Frontend isko text send karta hai jo bolna hai.
  2. Backend **ElevenLabs API** (`eleven_multilingual_v2` model) ko call karta hai.
  3. Response dynamic audio play ke liye download file stream bhejta hai.

---

## 3. Backend Se Frontend Ko Kya Data Milta Hai?

* **Transcription:** Text transcript dictionary (e.g. `{"text": "..."}`).
* **Process Result JSON:**
  - `action`: "add", "delete", "bye", or "error".
  - `speak_text`: Confirmation message string (Urdu).
  - `tasks_to_add`: Filtered list of valid tasks to append.
