import time
import psycopg2
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import pytz

load_dotenv()

DB_URL = os.getenv("RAIL_DB")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

IST = pytz.timezone('Asia/Kolkata')

print("🚀 Worker started...")


def send_telegram(subject, topic):
    print(f"📤 Sending Telegram → {subject} | {topic}")

    msg = f"""
⏰ Reminder!
📚 Subject: {subject}
📌 Topic: {topic}

The following subject and topic are not completed yet.
Please start studying and complete them now.
"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg
        })
        print("📡 Telegram response:", res.status_code, res.text)
    except Exception as e:
        print("❌ Telegram error:", e)


while True:
    print("\n⏱️ Checking tasks...")

    try:
        print("🔌 Connecting to DB...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        print("📥 Fetching tasks...")
        cur.execute("""
        SELECT id, subject_name, topic_name, deadline
        FROM tasks;
        """)

        tasks = cur.fetchall()
        print(f"📊 Total tasks fetched: {len(tasks)}")

        # ✅ current IST time
        now = datetime.now(IST)
        print("🕒 Current IST time:", now)

        for task in tasks:
            task_id, subject, topic, deadline = task

            print(f"\n➡️ Task ID {task_id} → {subject} | {topic}")
            print("   Raw deadline:", deadline)

            # ✅ Treat DB time as IST directly
            if deadline.tzinfo is None:
                deadline = IST.localize(deadline)

            print("   Deadline (IST):", deadline)
            print("   Time diff:", deadline - now)

            # CONDITION: deadline passed
            if deadline <= now:
                print("⚠️ Deadline passed → triggering reminder")

                send_telegram(subject, topic)

                new_deadline = deadline + timedelta(hours=1.5)
                print("🔄 New deadline (IST):", new_deadline)

                # CONDITION: crosses next day
                if new_deadline.date() > deadline.date():
                    print("🗑️ Deleting task (crossed day)")
                    cur.execute("DELETE FROM tasks WHERE id = %s;", (task_id,))
                else:
                    print("✏️ Updating deadline")

                    # store directly in IST (no conversion)
                    cur.execute(
                        "UPDATE tasks SET deadline = %s WHERE id = %s;",
                        (new_deadline.replace(tzinfo=None), task_id)
                    )
            else:
                print("✅ Not due yet")

        conn.commit()
        print("💾 DB commit successful")

        cur.close()
        conn.close()
        print("🔒 DB connection closed")

    except Exception as e:
        print("❌ ERROR:", e)

    print("😴 Sleeping for 5 minutes...\n")
    time.sleep(300)
