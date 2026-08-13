import sys
import os

def evaluate_action(action: str):
    destructive_keywords = [
        "drop", "delete", "wipe", "broken_tag", "0.0.0.0:22", 
        "5000", "delete ns", "privileged: true", "hostnetwork: true", 
        "rm -rf", "drop database", "bypass security"
    ]
    
    action_lower = action.lower()
    for kw in destructive_keywords:
        if kw in action_lower:
            return False, f"Destructive keyword detected: '{kw}'"
    return True, "Action passed security guardrails."

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: No action provided to IntentLock Guardrail.")
        sys.exit(1)
        
    target_action = sys.argv[1]
    print(f"🛡️ IntentLock analyzing action: '{target_action}'...")
    
    is_safe, reason = evaluate_action(target_action)
    
    if not is_safe:
        print(f"🚨 GUARDRAIL TRIGGERED: Blocked due to malicious/destructive intent!")
        print(f"Reason: {reason}")
        sys.exit(1)
    else:
        print(f"✅ SUCCESS: {reason}")
        sys.exit(0)
