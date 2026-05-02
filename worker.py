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


def send_telegram(subject, topic):
    msg = f"""
⏰ Reminder!
📚 Subject: {subject}
📌 Topic: {topic}

The following subject and topic are not completed yet.
Please start studying and complete them now.
"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg
    })


while True:
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # fetch all tasks
        cur.execute("""
        SELECT id, subject_name, topic_name, deadline
        FROM tasks;
        """)

        tasks = cur.fetchall()

        now = datetime.now(IST)

        for task in tasks:
            task_id, subject, topic, deadline = task

            # timezone handling
            if deadline.tzinfo is None:
                deadline = IST.localize(deadline)
            else:
                deadline = deadline.astimezone(IST)

            # CONDITION: deadline passed
            if deadline <= now:

                # 🔥 send telegram
                send_telegram(subject, topic)

                new_deadline = deadline + timedelta(hours=1.5)

                # CONDITION: crosses next day
                if new_deadline.date() > deadline.date():
                    cur.execute("DELETE FROM tasks WHERE id = %s;", (task_id,))
                else:
                    cur.execute(
                        "UPDATE tasks SET deadline = %s WHERE id = %s;",
                        (new_deadline, task_id)
                    )

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("ERROR:", e)

    # wake every 5 mins
    time.sleep(300)
