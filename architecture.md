# Iqbal Shab Agent Architecture

Yeh document system ki aam functionality, models, aur components ki flow explain karta hai.

## 1. Speech-To-Text (STT) - User Input
**Model Used:** OpenAI `whisper-1`
**Kaam:** Jab user mic button dabata hai, aawaz record hoti hai. Yeh audio OpenAI ki Whisper API ke pas jati hai jo us aawaz ko exact text mein badal deti hai. (e.g. *"jameel ko kal ka meeting task de do"*).

## 2. LLM Processing - Task Extraction
**Model Used:** OpenAI `gpt-4o-mini`
**Kaam:** Whisper se aane wala text LLM ke paas jata hai. Humara custom prompt GPT ko guide karta hai ke wo:
- **ASSIGNED TO:** Sahi Urdu/Pakistani name nikaley (e.g. Jameel).
- **TASK:** Action-oriented task identify karey (e.g. "meeting attend karna").
- **DEADLINE:** Date aur exact time assign karey (`deadlineISO` format mein).
Pura result structured JSON format mein wapas bhejta hai.

## 3. Frontend Operations - State & Reminders
**Framework:** React (Vite)
**Kaam:** 
- JSON aane par, list mein neeche naye tasks add ho jate hain.
- Google Calendar se automatically link ho jate hain agar logged in ho.
- **Local Reminder System:** Har 10 seconds baad system task ka waqt check karta hai. Jaise hi waqt hota hai, yeh automatically remind karta hai.

## 4. Text-To-Speech (TTS) - Output
**Model Used:** ElevenLabs `eleven_multilingual_v2`
**Voice ID:** `A5W9pR9OjIbu80J0WuDW`
**Kaam:** 
- Task extraction par pehlay confirmation bolta hai (e.g., *"Task assign kar diye gaye hain. Jameel ko meeting ka task."*).
- Jab reminder ka time aata hai, toh yeh awaaz mein pop-up notification de kar bolta hai: *"Reminder: Jameel ki deadline aa gayi hai..."*.

---
**Summary:**
`Audio ➡️ Whisper (Text) ➡️ LLaMA (Task JSON) ➡️ React (UI & Reminder Time) ➡️ ElevenLabs (Voice Output)`
