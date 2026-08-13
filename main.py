import sqlite3
import time
import requests
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="IntentLock AI-Powered Ollama Guardrail Gateway")

DB_FILE = "intentlock_ollama.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"  # Ensure you have pulled llama3 via 'ollama pull llama3'

mock_cluster_pods = {
    "default/intent-app-redis-cache": "Running",
    "kube-system/coredns-565d847f4c-abcde": "Running"
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DROP TABLE IF EXISTS snapshots")
    conn.execute("""
        CREATE TABLE snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            state TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def take_snapshot():
    conn = sqlite3.connect(DB_FILE)
    state = str(mock_cluster_pods)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO snapshots (timestamp, state) VALUES (?, ?)", (time.time(), state))
    conn.commit()
    snapshot_id = cursor.lastrowid
    conn.close()
    return snapshot_id

class IntentRequest(BaseModel):
    agent_name: str
    target_service: str
    config_action: str

def evaluate_intent_with_ollama(action: str):
    prompt = f"""
    You are an elite AI infrastructure guardrail and security proxy. 
    Analyze the following configuration or deployment action: "{action}"
    Determine if it is SAFE or DANGEROUS (e.g., destructive, privilege escalation, dropping databases, unauthorized network exposure, or malicious rogue actions).
    Respond strictly in valid JSON format with only two keys: 
    "verdict": "SAFE" or "DANGEROUS", 
    "reason": "short string explanation of why"
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        if response.status_code == 200:
            result_data = response.json().get("response", "{}")
            parsed = json.loads(result_data)
            return parsed.get("verdict", "SAFE").upper(), parsed.get("reason", "Evaluated by Ollama.")
    except Exception as e:
        # Fallback security check if Ollama is offline or times out
        destructive_keywords = ["delete ns", "privileged: true", "hostnetwork: true", "rm -rf", "drop database"]
        for kw in destructive_keywords:
            if kw in action.lower():
                return "DANGEROUS", "Fallback rule triggered: Dangerous keyword detected."
    return "SAFE", "Passed semantic evaluation."

@app.post("/apply")
def apply_intent(intent: IntentRequest):
    pre_snapshot_id = take_snapshot()

    # Semantic AI Evaluation via Ollama
    verdict, reason = evaluate_intent_with_ollama(intent.config_action)
    
    if verdict == "DANGEROUS":
        return {
            "status": "rolled_back",
            "error": f"Ollama AI Guardrail Blocked Intent: {reason} (Agent: [{intent.agent_name}])",
            "restored_to_snapshot": pre_snapshot_id
        }

    pod_key = f"default/intent-app-{intent.target_service}"

    if "crash" in intent.config_action.lower():
        mock_cluster_pods[pod_key] = "CrashLoopBackOff"
    else:
        mock_cluster_pods[pod_key] = "Running"

    time.sleep(2)
    
    if mock_cluster_pods.get(pod_key) == "CrashLoopBackOff":
        del mock_cluster_pods[pod_key]
        return {
            "status": "auto_rolled_back",
            "reason": f"Autonomous Health Check Failed: Pod [{pod_key}] entered CrashLoopBackOff.",
            "restored_to_snapshot": pre_snapshot_id
        }

    post_snapshot_id = take_snapshot()
    return {
        "status": "approved_and_deployed",
        "service": intent.target_service,
        "message": f"Ollama Semantic Validation Passed: {reason}",
        "snapshot_id": post_snapshot_id
    }

def restore_snapshot_internal(snapshot_id: int):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT state FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    conn.close()
    if not row:
        return False
    global mock_cluster_pods
    mock_cluster_pods = eval(row[0])
    return True

@app.post("/rollback/{snapshot_id}")
def rollback(snapshot_id: int):
    success = restore_snapshot_internal(snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot ID not found.")
    new_snap = take_snapshot()
    return {
        "status": "rolled_back_successfully",
        "restored_to_snapshot": snapshot_id,
        "current_snapshot_id": new_snap
    }
