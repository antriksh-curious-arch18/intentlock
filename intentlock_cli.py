import argparse
import sys
import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    parser = argparse.ArgumentParser(description="IntentLock CLI - AI Guardrail & Snapshot Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Apply Command
    apply_parser = subparsers.add_parser("apply", help="Send a deployment or config intent to the proxy")
    apply_parser.add_argument("--agent", required=True, help="Name of the AI agent or developer")
    apply_parser.add_argument("--service", required=True, help="Target service name")
    apply_parser.add_argument("--action", required=True, help="Configuration or deployment action description")

    # 2. History Command
    subparsers.add_parser("history", help="View all database snapshots and system states")

    # 3. Rollback Command
    rb_parser = subparsers.add_parser("rollback", help="Time-travel rollback to a specific snapshot ID")
    rb_parser.add_argument("snapshot_id", type=int, help="Target snapshot ID to restore")

    args = parser.parse_args()

    try:
        if args.command == "apply":
            payload = {
                "agent_name": args.agent,
                "target_service": args.service,
                "config_action": args.action
            }
            print(f"🚀 Sending intent for [{args.service}] by [{args.agent}]...")
            response = requests.post(f"{BASE_URL}/apply", json=payload)
            print(response.json())

        elif args.command == "history":
            print("📜 Fetching IntentLock Snapshot History...")
            import sqlite3, pprint
            conn = sqlite3.connect("intentlock.db")
            snapshots = conn.execute("SELECT * FROM snapshots").fetchall()
            for s in snapshots:
                print(f"\n[Snapshot ID: {s[0]}] | Timestamp: {s[1]}")
                pprint.pprint(eval(s[2]))

        elif args.command == "rollback":
            print(f"🔄 Executing time-travel rollback to Snapshot ID [{args.snapshot_id}]...")
            response = requests.post(f"{BASE_URL}/rollback/{args.snapshot_id}")
            print(response.json())

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to IntentLock server! Make sure your FastAPI server is running on port 8000.")
        sys.exit(1)

if __name__ == "__main__":
    main()
