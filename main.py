from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from datetime import datetime
import json
import httpx
import threading
import asyncio
import sounddevice as sd
import numpy as np

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wake Word WebSocket and manager removed to use frontend-only wake word detection.

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        
    audio_content = await file.read()
    
    async with httpx.AsyncClient() as client:
        files = {"file": (file.filename, audio_content, file.content_type)}
        data = {"model": "whisper-1"}
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            files=files,
            data=data,
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return response.json()

class TextRequest(BaseModel):
    text: str

class ExtractTaskRequest(BaseModel):
    text: str

class ProcessCommandRequest(BaseModel):
    text: str
    current_tasks: list

async def _extract_task_logic(text: str, current_tasks: list = None) -> dict:
    if not OPENAI_API_KEY:
        return {"error": True, "error_message": "OPENAI_API_KEY not configured"}
        
    active_names = []
    if current_tasks:
        active_names = list(set([t.get("assignedTo") for t in current_tasks if t.get("assignedTo")]))
        
    today = datetime.now().strftime("%Y-%m-%d")
    system_prompt = f"""ROLE
You are a precise task extraction engine for a voice-based task delegation system. The user speaks naturally in English or Urdu. You parse their speech and return a single structured JSON object.

─────────────────────────────────────────────
URDU SCRIPT ENFORCEMENT (CRITICAL)
─────────────────────────────────────────────
All extracted task descriptions ("task") and names ("assignedTo") MUST be written in proper Urdu script (Arabic script / Nastaliq character set, e.g., "اقبال صاحب", "عثمان", "علی", "فائل ko اکٹھا کرنا", "سیٹيو ke ساتھ میٹنگ کرنا"). 
NEVER output Devanagari/Hindi characters (like एकबाल साब, दुलकरीम, मिटिंग करना). Translate/transcribe any Hindi or Roman Urdu pronunciation strictly into correct Urdu script.

─────────────────────────────────────────────
INTENT IDENTIFICATION & RULES
─────────────────────────────────────────────
Identify the user's intent:
1. "delete" intent: The user wants to delete/remove tasks for a person by name. 
   - Active names currently in system: {active_names}
   - If the user wants to delete, set "delete_target_name" to one of these active names exactly as they are written in the active list.
   - Examples of deletion phrases: "Delete Usman's tasks", "Ali ko delete kar do", "Ali ke tasks delete kar do", "Delete tasks for Usman", etc.
   - For deletion:
     * Set "action": "delete"
     * Set "delete_target_name": Extract the EXACT name of the person whose tasks should be deleted in URDU script.
     * Set "tasks" to an empty list [].
     * Set "confirmation": "Theek hai, delete kar diya."

2. "bye" intent: The user says goodbye to close the session.
   - Examples: "bye", "goodbye", "allah hafiz", "khuda hafiz".
   - For bye:
     * Set "action": "bye"
     * Set "delete_target_name": null
     * Set "tasks": []
     * Set "confirmation": "Allah hafiz! Phir milenge."

3. "add" intent (default): The user wants to add/assign new tasks.
   - For addition:
     * Set "action": "add"
     * Set "delete_target_name": null
     * Extract ALL tasks mentioned. The user might dictate 1 task or up to 10 tasks at once.
     * ASSIGNED TO: Extract the EXACT name of the person in URDU script (e.g. علی, اقبال صاحب, عثمان). If "remind me", use "Me". If none, use "Unassigned".
     * TASK: Clean, action-oriented task description in URDU script.
     * DEADLINE: Absolute date/time based on TODAY'S DATE: {today}. Default: tomorrow at 9:00 AM. Format: YYYY-MM-DDTHH:MM:SS.
     * PRIORITY: "High" | "Medium" | "Low".

─────────────────────────────────────────────
ERROR HANDLING (CRITICAL)
─────────────────────────────────────────────
If the speech is gibberish, or completely missing a task description/intent, or you cannot understand:
- Set "error": true
- Set "error_message": "Mazrat, apka name ya task sahi nahi sunayi diya. Baraye meharbani dobara batayen." (Roman Urdu/Hindi).
- "tasks" array should be empty.
- "action": "add"

─────────────────────────────────────────────
RETURN STRUCTURE (JSON ONLY)
─────────────────────────────────────────────
{{
  "error": false,
  "error_message": "",
  "action": "add" | "delete" | "bye",
  "delete_target_name": "..." or null,
  "confirmation": "...",
  "tasks": [
    {{
      "assignedTo": "...",
      "task": "...",
      "deadline": "...",
      "deadlineISO": "...",
      "priority": "..."
    }}
  ]
}}"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            },
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content)
            
            # Check if deadline is in the past for any task
            if "tasks" in parsed_json and isinstance(parsed_json["tasks"], list):
                for task in parsed_json["tasks"]:
                    if "deadlineISO" in task:
                        try:
                            deadline_dt = datetime.fromisoformat(task["deadlineISO"])
                            if deadline_dt < datetime.now():
                                task["isPastTime"] = True
                        except ValueError:
                            pass
            
            return parsed_json
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

@app.post("/extract-task")
async def extract_task(request: ExtractTaskRequest):
    try:
        parsed_json = await _extract_task_logic(request.text)
        return JSONResponse(content=parsed_json)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task extraction failed: {str(e)}")

@app.post("/process-command")
async def process_command(request: ProcessCommandRequest):
    try:
        task_data = await _extract_task_logic(request.text, request.current_tasks)
    except HTTPException as e:
        return {
            "action": "error",
            "speak_text": f"Mazrat, server error aya: {e.detail}",
            "tasks_to_add": [],
            "delete_target_name": None,
            "name_exists": False
        }
    except Exception as e:
        return {
            "action": "error",
            "speak_text": "Mazrat, kuch masla pesh aya hai. Dobara koshish karein.",
            "tasks_to_add": [],
            "delete_target_name": None,
            "name_exists": False
        }
    
    # Handle LLM error
    if task_data.get("error"):
        return {
            "action": "error",
            "speak_text": task_data.get("error_message", "Mazrat, kuch masla pesh aya hai."),
            "tasks_to_add": [],
            "delete_target_name": None,
            "name_exists": False
        }
        
    action = task_data.get("action", "add")
    
    # Handle Bye intent
    if action == "bye":
        return {
            "action": "bye",
            "speak_text": task_data.get("confirmation", "Allah hafiz! Phir milenge."),
            "tasks_to_add": [],
            "delete_target_name": None,
            "name_exists": False
        }
    
    if action == "delete":
        target = task_data.get("delete_target_name")
        if not target:
            return {
                "action": "delete",
                "speak_text": "name ni hai",
                "tasks_to_add": [],
                "delete_target_name": None,
                "name_exists": False
            }
            
        # Check if name exists in current tasks (case insensitive)
        name_exists = any(
            t.get("assignedTo") and t["assignedTo"].lower() == target.lower()
            for t in request.current_tasks
        )
        
        if name_exists:
            speak_text = f"{target} ke tasks delete kar diye gaye hain."
        else:
            speak_text = "name ni hai"
            
        return {
            "action": "delete",
            "speak_text": speak_text,
            "tasks_to_add": [],
            "delete_target_name": target,
            "name_exists": name_exists
        }
        
    # Default is "add"
    extracted_tasks = task_data.get("tasks", [])
    
    valid_tasks = [t for t in extracted_tasks if not t.get("isPastTime")]
    past_tasks = [t for t in extracted_tasks if t.get("isPastTime")]
    
    speak_parts = []
    
    if len(past_tasks) > 0:
        past_names = ", aur ".join(list(set([t.get("assignedTo") for t in past_tasks if t.get("assignedTo")])))
        speak_parts.append(f"{past_names} ka bataya hua time guzar chuka hai.")
        
    if len(valid_tasks) > 0:
        task_names = ", aur ".join([f"{t.get('assignedTo')} ko {t.get('task')}" for t in valid_tasks])
        speak_parts.append(f"baki {task_names} ko task assign kar diye gaye hain.")
        
    if len(speak_parts) > 0:
        speak_text = " Aur ".join(speak_parts)
    else:
        speak_text = task_data.get("confirmation", "")
        
    return {
        "action": "add",
        "speak_text": speak_text,
        "tasks_to_add": valid_tasks,
        "delete_target_name": None,
        "name_exists": False
    }

class SpeakRequest(BaseModel):
    text: str

@app.post("/speak")
async def speak(request: SpeakRequest):
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        raise HTTPException(status_code=500, detail="ElevenLabs credentials not configured")
        
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID.strip()}",
            json={
                "text": request.text,
                "model_id": "eleven_multilingual_v2"
            },
            headers={
                "xi-api-key": ELEVENLABS_API_KEY.strip(),
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"ELEVENLABS ERROR: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return Response(content=response.content, media_type="audio/mpeg")
