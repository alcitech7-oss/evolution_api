"""
APPOINTMENT SYSTEM - Creates appointments in the database and generates receipts
"""

import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import json

# ==================== CONFIGURATIONS ====================
INPUT_FOLDER = "mensagens_recebidas"
OUTPUT_FOLDER = "mensagens_enviadas"
APPOINTMENTS_FOLDER = "agendamentos"
DATABASE = "agendamentos.db"
STATES_FILE = "estados_conversas.json"

print("="*60)
print("APPOINTMENT SYSTEM - STARTING...")
print("="*60)

AVAILABLE_TIMES = {
    "monday": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "tuesday": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "wednesday": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "thursday": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "friday": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
    "saturday": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30"],
    "sunday": []
}

PROFESSIONALS = [
    {"id": 1, "name": "Dr. Carlos Silva", "specialty": "Cardiology"},
    {"id": 2, "name": "Dra. Ana Santos", "specialty": "Dermatology"},
    {"id": 3, "name": "Dr. Roberto Lima", "specialty": "Orthopedics"},
    {"id": 4, "name": "Dra. Fernanda Costa", "specialty": "Pediatrics"},
]

conversation_states = {}

def save_states():
    with open(STATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversation_states, f, ensure_ascii=False, indent=2, default=str)

def load_states():
    global conversation_states
    if os.path.exists(STATES_FILE):
        with open(STATES_FILE, 'r', encoding='utf-8') as f:
            conversation_states = json.load(f)

def create_folders():
    for folder in [INPUT_FOLDER, OUTPUT_FOLDER, APPOINTMENTS_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Folder created: {folder}")

def init_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_appointments INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            professional_id INTEGER,
            professional_name TEXT,
            date DATE,
            time TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized")

def get_or_create_client(phone: str, name: str = "Patient") -> dict:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
    client = cursor.fetchone()
    
    if not client:
        cursor.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", (name, phone))
        conn.commit()
        cursor.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        client = cursor.fetchone()
        print(f"  [DB] New client created: {name} - {phone}")
    
    conn.close()
    return dict(client)

def save_appointment(client_id: int, professional: dict, date: str, time: str) -> int:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO appointments (client_id, professional_id, professional_name, date, time, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (client_id, professional['id'], professional['name'], date, time))
    
    appointment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"  [DB] Appointment SAVED! ID: {appointment_id} - {professional['name']} - {date} {time}")
    return appointment_id

def confirm_appointment(appointment_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE appointments SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP WHERE id = ?
    ''', (appointment_id,))
    
    cursor.execute('''
        UPDATE clients SET total_appointments = total_appointments + 1 
        WHERE id = (SELECT client_id FROM appointments WHERE id = ?)
    ''', (appointment_id,))
    
    conn.commit()
    conn.close()
    print(f"  [DB] Appointment CONFIRMED! ID: {appointment_id}")

def cancel_appointment(appointment_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE appointments SET status = "cancelled" WHERE id = ?', (appointment_id,))
    conn.commit()
    conn.close()
    print(f"  [DB] Appointment CANCELLED! ID: {appointment_id}")

def get_client_appointments(phone: str, status: str = None) -> List[dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    client = get_or_create_client(phone)
    
    if status:
        cursor.execute('''
            SELECT * FROM appointments WHERE client_id = ? AND status = ? ORDER BY date, time
        ''', (client['id'], status))
    else:
        cursor.execute('''
            SELECT * FROM appointments WHERE client_id = ? ORDER BY date, time
        ''', (client['id'],))
    
    appointments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return appointments

def get_appointment(appointment_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()
    conn.close()
    return dict(appointment) if appointment else None

def detect_intent(message: str) -> dict:
    msg_lower = message.lower()
    
    if any(p in msg_lower for p in ['book', 'schedule', 'appointment', 'time']):
        if any(p in msg_lower for p in ['reschedule', 'change', 'move']):
            return {'intent': 'reschedule'}
        return {'intent': 'book'}
    elif any(p in msg_lower for p in ['cancel', 'delete', 'remove']):
        return {'intent': 'cancel'}
    elif any(p in msg_lower for p in ['confirm', 'yes', 'ok']):
        return {'intent': 'confirm'}
    elif any(p in msg_lower for p in ['list', 'my appointments', 'show']):
        return {'intent': 'list'}
    elif any(p in msg_lower for p in ['help', 'menu', 'options']):
        return {'intent': 'help'}
    elif message.strip().isdigit() and 1 <= int(message.strip()) <= 10:
        return {'intent': 'number_selection', 'number': int(message.strip())}
    else:
        return {'intent': 'unknown'}

def extract_professional(message: str) -> Optional[dict]:
    msg_lower = message.lower()
    for p in PROFESSIONALS:
        if p['name'].lower() in msg_lower or p['specialty'].lower() in msg_lower:
            return p
    return None

def extract_date(message: str) -> Optional[str]:
    today = datetime.now()
    msg_lower = message.lower()
    
    if 'today' in msg_lower:
        return today.strftime('%Y-%m-%d')
    if 'tomorrow' in msg_lower:
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    if 'next week' in msg_lower:
        days = (7 - today.weekday()) % 7
        return (today + timedelta(days=days if days > 0 else 7)).strftime('%Y-%m-%d')
    
    pattern = r'(\d{1,2})[/-](\d{1,2})'
    match = re.search(pattern, message)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        try:
            date = datetime(today.year, month, day)
            if date < today:
                date = datetime(today.year + 1, month, day)
            return date.strftime('%Y-%m-%d')
        except:
            pass
    return None

def get_available_times(date: str, professional_id: int = None) -> List[str]:
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    day_name = date_obj.strftime('%A').lower()
    times = AVAILABLE_TIMES.get(day_name, [])
    
    import random
    random.seed(f"{date}_{professional_id}")
    occupied = random.sample(times, min(3, len(times) // 3)) if times else []
    return [t for t in times if t not in occupied]

def send_response(phone: str, message: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{OUTPUT_FOLDER}/{phone}_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"TO: {phone}\n")
        f.write(f"DATE: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("="*50 + "\n")
        f.write(message)
    
    print(f"  -> Response saved: {filename}")

def generate_receipt(appointment_id: int, phone: str):
    appointment = get_appointment(appointment_id)
    if appointment:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{APPOINTMENTS_FOLDER}/appointment_{appointment['id']}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("APPOINTMENT RECEIPT\n")
            f.write("="*60 + "\n\n")
            f.write(f"Protocol: {appointment['id']}\n")
            f.write(f"Patient: {phone}\n")
            f.write(f"Professional: {appointment['professional_name']}\n")
            f.write(f"Date: {appointment['date'].replace('-', '/')}\n")
            f.write(f"Time: {appointment['time']}\n")
            f.write(f"Status: {appointment['status'].upper()}\n")
            f.write(f"Created at: {appointment['created_at']}\n")
            f.write("\n" + "="*60 + "\n")
        
        print(f"  -> RECEIPT generated: {filename}")
        return True
    return False

def process_message(phone: str, message: str, name: str):
    global conversation_states
    
    # Get current state
    state = conversation_states.get(phone, {'step': 'start', 'data': {}})
    client = get_or_create_client(phone, name)
    
    print(f"  State: {state['step']}")
    
    # Process based on current step
    if state['step'] == 'awaiting_time':
        try:
            choice = int(message.strip())
            times = state['data']['times']
            if 1 <= choice <= len(times):
                selected_time = times[choice - 1]
                
                appointment_id = save_appointment(
                    client['id'],
                    state['data']['professional'],
                    state['data']['date'],
                    selected_time
                )
                
                msg = f"""APPOINTMENT PENDING CONFIRMATION

Professional: {state['data']['professional']['name']}
Date: {state['data']['date'].replace('-', '/')}
Time: {selected_time}
Code: {appointment_id}

To CONFIRM, type: CONFIRM
To CANCEL, type: CANCEL"""
                
                send_response(phone, msg)
                conversation_states[phone] = {'step': 'awaiting_confirmation', 'data': {'appointment_id': appointment_id}}
                save_states()
                return
            else:
                send_response(phone, f"Invalid option! Choose 1 to {len(times)}")
                return
        except ValueError:
            send_response(phone, "Enter ONLY the time number")
            return
    
    elif state['step'] == 'awaiting_confirmation':
        if 'confirm' in message.lower() or 'yes' in message.lower():
            confirm_appointment(state['data']['appointment_id'])
            generate_receipt(state['data']['appointment_id'], phone)
            
            appointment = get_appointment(state['data']['appointment_id'])
            msg = f"""APPOINTMENT CONFIRMED!

Professional: {appointment['professional_name']}
Date: {appointment['date'].replace('-', '/')}
Time: {appointment['time']}
Protocol: {appointment['id']}

You will receive a reminder 24 hours before."""
            
            send_response(phone, msg)
            conversation_states[phone] = {'step': 'start', 'data': {}}
            save_states()
            return
            
        elif 'cancel' in message.lower() or 'no' in message.lower():
            cancel_appointment(state['data']['appointment_id'])
            send_response(phone, "APPOINTMENT CANCELLED! Time slot released.")
            conversation_states[phone] = {'step': 'start', 'data': {}}
            save_states()
            return
        else:
            send_response(phone, "Type CONFIRM to confirm or CANCEL to cancel")
            return
    
    # New intent detection
    intent = detect_intent(message)
    print(f"  Intent: {intent['intent']}")
    
    if intent['intent'] == 'book':
        professional = extract_professional(message)
        
        if not professional:
            msg = "CHOOSE A PROFESSIONAL:\n\n"
            for i, p in enumerate(PROFESSIONALS, 1):
                msg += f"{i} - {p['name']} - {p['specialty']}\n"
            msg += "\nEnter the professional number:"
            send_response(phone, msg)
            conversation_states[phone] = {'step': 'awaiting_professional', 'data': {}}
            save_states()
            return
        
        date = extract_date(message)
        if not date:
            msg = "WHICH DATE?\n\nExamples:\n- today\n- tomorrow\n- next week\n- 25/12\n\nEnter the date:"
            send_response(phone, msg)
            conversation_states[phone] = {'step': 'awaiting_date', 'data': {'professional': professional}}
            save_states()
            return
        
        times = get_available_times(date, professional['id'])
        if not times:
            msg = f"No times available for {date.replace('-', '/')}. Choose another date:"
            send_response(phone, msg)
            conversation_states[phone] = {'step': 'awaiting_date', 'data': {'professional': professional}}
            save_states()
            return
        
        msg = f"AVAILABLE TIMES\n\nDate: {date.replace('-', '/')}\nProfessional: {professional['name']}\n\n"
        for i, t in enumerate(times[:8], 1):
            msg += f"{i} - {t}\n"
        msg += "\nEnter the NUMBER of the time:"
        
        send_response(phone, msg)
        conversation_states[phone] = {
            'step': 'awaiting_time',
            'data': {
                'professional': professional,
                'date': date,
                'times': times
            }
        }
        save_states()
        
    elif intent['intent'] == 'list':
        appointments = get_client_appointments(phone)
        if not appointments:
            send_response(phone, "You have no scheduled appointments.")
        else:
            msg = "YOUR APPOINTMENTS:\n\n"
            for app in appointments:
                status_icon = {'confirmed': '[OK]', 'pending': '[ ]', 'cancelled': '[X]'}.get(app['status'], '[?]')
                msg += f"{status_icon} {app['professional_name']}\n"
                msg += f"   Date: {app['date'].replace('-', '/')} at {app['time']}\n"
                msg += f"   Status: {app['status']}\n\n"
            send_response(phone, msg)
    
    elif intent['intent'] == 'cancel':
        appointments = get_client_appointments(phone, status='confirmed')
        if not appointments:
            send_response(phone, "No confirmed appointments to cancel.")
        elif len(appointments) == 1:
            cancel_appointment(appointments[0]['id'])
            send_response(phone, f"APPOINTMENT CANCELLED!\n\n{appointments[0]['professional_name']}\n{appointments[0]['date'].replace('-', '/')} at {appointments[0]['time']}")
        else:
            msg = "WHICH APPOINTMENT TO CANCEL?\n\n"
            for i, app in enumerate(appointments, 1):
                msg += f"{i} - {app['professional_name']} - {app['date'].replace('-', '/')} at {app['time']}\n"
            send_response(phone, msg)
    
    elif intent['intent'] == 'confirm':
        pending = get_client_appointments(phone, status='pending')
        if pending:
            confirm_appointment(pending[0]['id'])
            generate_receipt(pending[0]['id'], phone)
            send_response(phone, f"APPOINTMENT CONFIRMED! Protocol: {pending[0]['id']}")
        else:
            send_response(phone, "No pending appointments to confirm.")
    
    else:
        msg = """APPOINTMENT ASSISTANT

COMMANDS:
1. Book: "Book with Dr. Carlos for tomorrow"
2. List: "My appointments"
3. Cancel: "Cancel my appointment"
4. Confirm: "CONFIRM" (after booking)"""
        send_response(phone, msg)

def process_message_file(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split multiple messages in the same file
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.split('\n')
        phone = None
        name = "Patient"
        message = []
        
        for line in lines:
            if line.startswith("FROM:"):
                phone = line.replace("FROM:", "").strip()
            elif line.startswith("NAME:"):
                name = line.replace("NAME:", "").strip()
            elif not line.startswith("DATE:") and not line.startswith("===") and line.strip():
                message.append(line)
        
        if phone and message:
            message_text = ' '.join(message).strip()
            print(f"\n[Processing] {phone} - {name}")
            print(f"Message: {message_text[:80]}")
            process_message(phone, message_text, name)

def process_all_messages():
    load_states()
    
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.txt') and not f.endswith('.processed')]
    
    if not files:
        print(f"\nNo messages in: {INPUT_FOLDER}/")
        return
    
    print(f"\nProcessing {len(files)} file(s)...")
    for file in files:
        path = os.path.join(INPUT_FOLDER, file)
        print(f"\n--- Reading file: {file} ---")
        try:
            process_message_file(path)
            os.rename(path, path + ".processed")
            print(f"[OK] {file} processed")
        except Exception as e:
            print(f"[ERROR] {file}: {e}")

def create_single_test_file():
    """Creates a single file with the complete flow"""
    content = """FROM: 5511999999999
NAME: Joao Silva
DATE: 15/12/2024 10:00:00
==================================================
Book with Dr. Carlos Silva for tomorrow

FROM: 5511999999999
NAME: Joao Silva
DATE: 15/12/2024 10:02:00
==================================================
1

FROM: 5511999999999
NAME: Joao Silva
DATE: 15/12/2024 10:05:00
==================================================
CONFIRM

FROM: 5511999999999
NAME: Joao Silva
DATE: 15/12/2024 10:10:00
==================================================
My appointments"""
    
    with open(f"{INPUT_FOLDER}/test_complete.txt", 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\nTest file created: {INPUT_FOLDER}/test_complete.txt")

# ==================== MAIN ====================
create_folders()
init_database()
create_single_test_file()
process_all_messages()

print("\n" + "="*60)
print("PROCESSING COMPLETE!")
print(f"Responses: {OUTPUT_FOLDER}/")
print(f"Receipts: {APPOINTMENTS_FOLDER}/")
print("="*60)

# Show total appointments
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM appointments")
count = cursor.fetchone()[0]
print(f"\nTotal appointments in database: {count}")
conn.close()
