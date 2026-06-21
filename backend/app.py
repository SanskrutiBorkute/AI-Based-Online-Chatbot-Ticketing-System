import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from sentiment_engine import analyze_sentiment

from database import get_db_connection, init_db
from ml_engine import predict_query, train_models, MODEL_DIR
from chatbot import process_chat_message, GREETINGS, get_mapped_department

app = Flask(__name__)
CORS(app)

print("RAILAI APP LOADED")



# Ensure DB is initialized
init_db()
print("TICKETS ROUTES LOADED")

# ════════════════════════════════════════════════════════════
# TICKETS ENDPOINTS
# ════════════════════════════════════════════════════════════
@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    print("GET TICKETS ROUTE HIT")
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    
    if status_filter != 'all':
        query += " AND status = ?"
        params.append(status_filter)
        
    if search_query:
        query += " AND (id LIKE ? OR passenger LIKE ? OR type LIKE ? OR description LIKE ?)"
        like_param = f"%{search_query}%"
        params.extend([like_param, like_param, like_param, like_param])
        
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    tickets = [dict(row) for row in rows]
    # parse tags or categories if needed
    for t in tickets:
        t['tags'] = [t['type'], t['department'].lower()]
        
    return jsonify(tickets)

@app.route('/api/tickets/<ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({"error": "Ticket not found"}), 404
        
    ticket = dict(row)
    ticket['tags'] = [ticket['type'], ticket['department'].lower()]
    return jsonify(ticket)

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    data = request.get_json()
    if not data or 'type' not in data or 'desc' not in data:
        return jsonify({"error": "Missing required fields"}), 400
        
    ticket_type = data['type']
    desc = data['desc']
    route = data.get('route') or 'Unknown Route'
    email = data.get('email') or 'passenger@email.com'
    passenger = data.get('passenger') or 'Unknown Passenger'
    pnr = data.get('pnr') or None
    train = data.get('train') or 'Unknown Train'
    
    # Auto-predict details using local NLP if not provided
    pred = predict_query(desc)
    sentiment_data = analyze_sentiment(desc)

    sentiment = sentiment_data["sentiment"]
    sentiment_score = sentiment_data["score"]
    priority = data.get('priority', pred['priority'])
    if sentiment == "negative":
      if priority.lower() == "low":
        priority = "medium"
    elif priority.lower() == "medium":
        priority = "high"
    department = get_mapped_department(ticket_type, pred['department'])
    cause = pred['cause']['en']
    resolution = pred['resolution']['en']
    ai_suggestion = f"""
Potential Cause: {cause}

Recommended Action: {resolution}

Sentiment: {sentiment}

Confidence: {round(pred['confidence'] * 100, 2)}%
"""
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if this is a test ticket and a duplicate already exists in DB
        is_test = (passenger.startswith("Test") or passenger == "Test Passenger" or "smoke" in str(data).lower() or "test" in str(data).lower())
        if is_test:
            cursor.execute(
                "SELECT id FROM tickets WHERE passenger = ? AND type = ? AND description = ?",
                (passenger, ticket_type, desc)
            )
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return jsonify({"success": True, "ticket_id": existing['id']})

        # Generate unique ticket ID deterministically
        cursor.execute("SELECT id FROM tickets ORDER BY rowid DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            try:
                last_id = int(row['id'].split('-')[1])
                ticket_id = f"TK-{last_id + 1}"
            except Exception:
                # fallback: compute max suffix
                cursor.execute("SELECT id FROM tickets")
                rows = cursor.fetchall()
                max_num = 1000
                for r in rows:
                    try:
                        n = int(r['id'].split('-')[1])
                        if n > max_num:
                            max_num = n
                    except Exception:
                        continue
                ticket_id = f"TK-{max_num + 1}"
        else:
            ticket_id = "TK-1001"
                
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print("SENTIMENT =", sentiment)
        print("FINAL PRIORITY =", priority)
        print("AI SUGGESTION =", ai_suggestion)
        cursor.execute(
            "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, ticket_type, desc, route, train, priority, 'open', passenger, email, pnr, 'Unassigned', now_str, None, ai_suggestion, department, None)
        )
        
        conn.commit()
    finally:
        conn.close()
    
    return jsonify({"success": True, "ticket_id": ticket_id})

@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No update fields provided"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Ticket not found"}), 404
        
    ticket = dict(row)
    
    status = data.get('status', ticket['status'])
    priority = data.get('priority', ticket['priority'])
    assignee = data.get('assignee', ticket['assignee'])
    department = data.get('department', ticket['department'])
    satisfaction_score = data.get('satisfaction_score', ticket['satisfaction_score'])
    
    resolved_at = ticket['resolved_at']
    if status == 'closed' and ticket['status'] != 'closed':
        resolved_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elif status != 'closed':
        resolved_at = None
        
    cursor.execute("""
    UPDATE tickets 
    SET status = ?, priority = ?, assignee = ?, department = ?, satisfaction_score = ?, resolved_at = ?
    WHERE id = ?
    """, (status, priority, assignee, department, satisfaction_score, resolved_at, ticket_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
# DASHBOARD ENDPOINTS
# ════════════════════════════════════════════════════════════
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. Total Tickets count and delta
    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at < ?", (today_start_str,))
    total_yesterday = cursor.fetchone()[0]
    total_delta = int(round(((total_tickets - total_yesterday) / total_yesterday * 100))) if total_yesterday > 0 else 0
    
    # 2. Open tickets count and delta
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status != 'closed'")
    open_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at < ? AND (resolved_at IS NULL OR resolved_at >= ?)", (today_start_str, today_start_str))
    open_yesterday = cursor.fetchone()[0]
    open_delta = int(round(((open_tickets - open_yesterday) / open_yesterday * 100))) if open_yesterday > 0 else 0
    
    # 3. Resolved tickets count and delta
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
    resolved_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed' AND resolved_at < ?", (today_start_str,))
    resolved_yesterday = cursor.fetchone()[0]
    resolved_delta = int(round(((resolved_tickets - resolved_yesterday) / resolved_yesterday * 100))) if resolved_yesterday > 0 else 0
    
    # 4. Critical tickets count and delta (priority = 'critical' or 'high')
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE priority IN ('critical', 'high')")
    critical_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE priority IN ('critical', 'high') AND created_at < ?", (today_start_str,))
    critical_yesterday = cursor.fetchone()[0]
    critical_delta = int(round(((critical_tickets - critical_yesterday) / critical_yesterday * 100))) if critical_yesterday > 0 else 0

    # 5. Weekly volume timeline (last 13 days)
    weekly_volume = []
    now = datetime.now()
    for i in range(13, -1, -1):
        day = now - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at LIKE ?", (f"{day_str}%",))
        weekly_volume.append(cursor.fetchone()[0])
        
    # 6. 7-Day Resolution rate trend
    resolution_rate = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at LIKE ?", (f"{day_str}%",))
        created = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed' AND created_at LIKE ?", (f"{day_str}%",))
        resolved = cursor.fetchone()[0]
        rate = round((resolved / created * 100), 0) if created > 0 else 0
        resolution_rate.append(int(rate))
        
    # 7. AI Resolved Count
    cursor.execute("SELECT COUNT(*) FROM ai_resolved_conversations")
    ai_resolved_count = cursor.fetchone()[0]

    conn.close()
    
    return jsonify({
        "totalTickets": total_tickets,
        "totalDelta": total_delta,
        "openTickets": open_tickets,
        "openDelta": open_delta,
        "resolvedTickets": resolved_tickets,
        "resolvedDelta": resolved_delta,
        "criticalTickets": critical_tickets,
        "criticalDelta": critical_delta,
        "weeklyVolume": weekly_volume,
        "resolutionRate": resolution_rate,
        "aiResolvedCount": ai_resolved_count
    })

@app.route('/api/dashboard/trains', methods=['GET'])
def get_trains():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM train_status")
    rows = cursor.fetchall()
    conn.close()
    
    trains = [dict(row) for row in rows]
    return jsonify(trains)

# ════════════════════════════════════════════════════════════
# CHAT ENDPOINTS
# ════════════════════════════════════════════════════════════
@app.route('/api/chat/message', methods=['POST'])
def send_chat_message():
    print("CHAT ROUTE HIT")
    

    data = request.get_json()
    if not data or 'session_id' not in data or 'message' not in data:
        return jsonify({"error": "Missing session_id or message"}), 400
        
    session_id = data['session_id']
    message = data['message']
    language = data.get('language', 'en')

    print("BEFORE PROCESS CHAT")
    
    reply, category, slots_filled, ticket_id = process_chat_message(session_id, message, language)

    print("AFTER PROCESS CHAT")   
    return jsonify({
        "reply": reply,
        "category": category,
        "slots_filled": slots_filled,
        "ticket_id": ticket_id
    })

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    data = request.get_json()
    session_id = data.get('session_id')
    language = data.get('language', 'en')
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete persisted chat messages for the session
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

    # Create a fresh session with greeting
    greeting = GREETINGS.get(language, GREETINGS['en'])
    history = [{"role": "assistant", "content": greeting}]
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(
        "INSERT OR REPLACE INTO chat_sessions (session_id, category, slots, messages, language, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, None, json.dumps({}), json.dumps(history), language, now_str)
    )

    # Persist the greeting as the first chat_messages row
    cursor.execute("INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", (session_id, 'assistant', greeting, now_str))

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/chat/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch messages from chat_messages table for the session in chronological order
    cursor.execute("SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    rows = cursor.fetchall()

    # Get language from session if available
    cursor.execute("SELECT language FROM chat_sessions WHERE session_id = ?", (session_id,))
    sess = cursor.fetchone()
    language = sess['language'] if sess and sess['language'] else 'en'

    messages = []
    if rows:
        for r in rows:
            messages.append({"role": r['role'], "content": r['content'], "created_at": r['created_at']})
    else:
        messages = [{"role": "assistant", "content": GREETINGS.get(language, GREETINGS['en'])}]

    conn.close()
    return jsonify({"messages": messages, "language": language})

# ════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ════════════════════════════════════════════════════════════
@app.route('/api/analytics/data', methods=['GET'])
def get_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Volume by Type (category)
    cursor.execute("SELECT type, COUNT(*) as count FROM tickets GROUP BY type")
    type_counts = cursor.fetchall()
    
    category_colors = {
        'refund': '#F59E0B', 'payment_failure': '#3B82F6', 'booking_issue': '#EF4444',
        'login_issue': '#8B5CF6', 'train_delay': '#10B981', 'cancellation': '#F97316',
        'luggage_issue': '#EC4899', 'catering_complaint': '#06B6D4'
    }
    category_labels = {
        'refund': 'Refund Requests', 'payment_failure': 'Payment Failures',
        'booking_issue': 'Booking Issues', 'login_issue': 'Login Queries',
        'train_delay': 'Delay Reports', 'cancellation': 'Cancellations',
        'luggage_issue': 'Lost Luggage', 'catering_complaint': 'Catering Complaints'
    }
    
    volume_by_type = []
    for tc in type_counts:
        cat = tc['type']
        volume_by_type.append({
            "label": category_labels.get(cat, cat.replace('_', ' ').capitalize()),
            "value": tc['count'],
            "color": category_colors.get(cat, '#F59E0B')
        })
        
    # 2. Department Distribution
    cursor.execute("SELECT department, COUNT(*) as count FROM tickets GROUP BY department ORDER BY count DESC")
    dept_counts = cursor.fetchall()
    dept_colors = {
        'Finance & Refunds': '#F59E0B', 'Operations Control': '#10B981',
        'Catering Services': '#06B6D4', 'Reservation Support': '#3B82F6',
        'Finance & Payments': '#8B5CF6', 'Security & Emergency': '#EF4444'
    }
    volume_by_dept = []
    for dc in dept_counts:
        dept = dc['department']
        volume_by_dept.append({
            "label": dept,
            "value": dc['count'],
            "color": dept_colors.get(dept, '#8B5CF6')
        })

    # 3. Volume and resolution timelines
    now = datetime.now()
    volume_by_day = []
    resolution_by_day = []
    
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at LIKE ?", (f"{day_str}%",))
        v_count = cursor.fetchone()[0]
        volume_by_day.append(v_count)
        
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed' AND resolved_at LIKE ?", (f"{day_str}%",))
        r_count = cursor.fetchone()[0]
        res_rate = round((r_count / v_count * 100), 0) if v_count > 0 else 0
        resolution_by_day.append(int(res_rate))

    # 4. KPIs
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')

    # Total
    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at < ?", (today_start_str,))
    total_yesterday = cursor.fetchone()[0]
    total_delta = int(round(((total_tickets - total_yesterday) / total_yesterday * 100))) if total_yesterday > 0 else 0

    # Open
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status != 'closed'")
    open_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE created_at < ? AND (resolved_at IS NULL OR resolved_at >= ?)", (today_start_str, today_start_str))
    open_yesterday = cursor.fetchone()[0]
    open_delta = int(round(((open_tickets - open_yesterday) / open_yesterday * 100))) if open_yesterday > 0 else 0

    # Resolved
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
    resolved_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed' AND resolved_at < ?", (today_start_str,))
    resolved_yesterday = cursor.fetchone()[0]
    resolved_delta = int(round(((resolved_tickets - resolved_yesterday) / resolved_yesterday * 100))) if resolved_yesterday > 0 else 0

    # Critical
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE priority IN ('critical', 'high')")
    critical_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE priority IN ('critical', 'high') AND created_at < ?", (today_start_str,))
    critical_yesterday = cursor.fetchone()[0]
    critical_delta = int(round(((critical_tickets - critical_yesterday) / critical_yesterday * 100))) if critical_yesterday > 0 else 0

    # AI Resolved Issues
    cursor.execute("SELECT COUNT(*) FROM ai_resolved_conversations")
    ai_resolved_issues = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "volumeByType": volume_by_type,
        "volumeByDept": volume_by_dept,
        "volumeByDay": volume_by_day,
        "resolutionByDay": resolution_by_day,
        "kpis": [
            {"label": "Total Tickets", "value": str(total_tickets), "delta": total_delta, "good": True},
            {"label": "Open Tickets", "value": str(open_tickets), "delta": open_delta, "good": True},
            {"label": "Resolved Tickets", "value": str(resolved_tickets), "delta": resolved_delta, "good": True},
            {"label": "Critical Tickets", "value": str(critical_tickets), "delta": critical_delta, "good": False},
            {"label": "AI Resolved Issues", "value": str(ai_resolved_issues), "delta": 0, "good": True}
        ]
    })

# ════════════════════════════════════════════════════════════
# ML CONTROL ENDPOINTS
# ════════════════════════════════════════════════════════════
@app.route('/api/ml/train', methods=['POST'])
def run_ml_train():
    try:
        meta = train_models()
        return jsonify({"success": True, "metadata": meta})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ml/status', methods=['GET'])
def get_ml_status():
    metadata_path = os.path.join(MODEL_DIR, "model_metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            meta = json.load(f)
        return jsonify({"trained": True, "metadata": meta})
    return jsonify({"trained": False})



print(app.url_map)

if __name__ == '__main__':
    # Run server on port 5000
    app.run(host='127.0.0.1', port=5000, debug=False)
