# Frontend Ki Details (React & Vite)

Yeh file frontend ke saare React components, custom Hooks, utilities aur files ke functions ko Roman English mein explain karti hai.

---

## 1. Project Directory Structure

Frontend components aur logic `frontend/src` directory ke andar distributed hain:
* **`App.jsx`:** Main core controller file jo frontend ka state aur voice lifecycle handle karti hai.
* **`components/MicButton.jsx`:** Microphone capture interface aur visual design (AI listening states aur wave controls).
* **`components/TaskList.jsx`:** Active tasks list show karne aur unhe categorise (Pending/Completed, Today/Tomorrow) karne ke liye.
* **`components/TaskCard.jsx`:** Single task card details and individual delete action display karta hai.
* **`utils/`:** Backend API handlers (e.g. whisper transcribing, calendar events, OpenAI task extraction).

---

## 2. Important Files Aur Unka Kaam

### A. `src/App.jsx`
Yeh poori application ka **control center** hai. Ismein niche diye gaye important features run ho rahe hain:
1. **Local State Management:** Active tasks ko state mein maintain karta hai aur use `localStorage` ke sath automatically sync karta hai taake page refresh hone par tasks delete na hon.
2. **Local SpeechRecognition Hook:** 
   - Browser ki built-in **Web Speech API** (`window.SpeechRecognition`) ko run karta hai jo background mein continuously listen karti hai.
   - **Wake Words:** `"ok simrin"` aur `"ok simran"` bolne par recording loop open karta hai.
   - **Thanks Triggers:** Recording ke dauran, jab user `"thanks"`, `"thanks you"`, `"thank you"`, ya `"shukriya"` bolta hai:
     - System automatically record stop kar deta hai.
     - Auto-resume session parameter (`shouldAutoResumeSession.current`) true ho jata hai taake task process hone aur confirmation audio khatam hone par frontend **dubara listening start kar de** (bila dobara "OK Simrin" bole).
   - **Bye Triggers:** Jab user `"bye"`, `"ok bye"`, `"okay bye"`, ya `"allah hafiz"` bolta hai:
     - System recording stop karta hai.
     - Speak confirmation ke baad listener idle wake-word state par return chala jata hai (session end ho jata hai).
3. **Google Calendar Event Setup:** Google OAuth flow token use kar ke new tasks ko Google Calendar mein automatic add karta hai.
4. **Local Reminder System:** Har 10 seconds par checks run karta hai, agar kisi task ki deadline ho jaye to sound alarm/voice play karta hai.

### B. `src/components/MicButton.jsx`
* **Microphone Capture:** React MediaRecorder API use kar ke high quality webm audio record karta hai.
* **Audio Flow:** Recording start hone se pehle AI system response sound play karta hai *"How can I help you today?"*, uske fauran baad device microphone control handle kiya jata hai.
* **State Sync:** Recording start/stop statuses aur transitions (idle -> starting -> recording -> processing) ko main `App.jsx` ke sath share karta hai.

### C. `src/components/TaskList.jsx` & `TaskCard.jsx`
* Active tasks ko group wise sort karta hai (e.g., today's tasks, tomorrow's tasks, etc.).
* Tasks ke progress statuses (Pending/Completed) toggles manage karta hai.
* Frontend manual buttons allow karta hai tasks ko single clicks par delete karne ke liye.

---

## 3. Utilities in `src/utils/`

* **`whisper.js`:** Audio blob le kar backend `/transcribe` endpoint par upload karta hai.
* **`gpt.js`:** Transcription text backend `/extract-task` endpoint par bhejta hai.
* **`elevenlabs.js`:** Speech request text backend `/speak` endpoint par call kar ke audio array play karta hai.
* **`calendar.js`:** Google OAuth credentials aur task description use kar ke calendar events add karta hai.
