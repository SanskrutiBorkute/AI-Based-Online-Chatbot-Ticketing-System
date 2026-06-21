import urllib.request, urllib.parse, json, uuid, time, sqlite3

BASE = 'http://127.0.0.1:5000'

def post_json(path, data):
    req = urllib.request.Request(BASE+path, data=json.dumps(data).encode('utf-8'), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=10) as f:
        return json.load(f)

def get_json(path):
    with urllib.request.urlopen(BASE+path, timeout=10) as f:
        return json.load(f)

session_id = 'smoke-' + str(uuid.uuid4())[:8]
print('Session ID:', session_id)

# 1. Start a new chat session (clear)
r = post_json('/api/chat/clear', {'session_id': session_id, 'language': 'en'})
print('clear:', r)

# 2. Get history
h = get_json(f'/api/chat/history/{session_id}')
print('history start:', h)

# 3. Send refund-related query
msg1 = 'I want a refund for my ticket.'
r1 = post_json('/api/chat/message', {'session_id': session_id, 'message': msg1, 'language': 'en'})
print('send1:', r1)

# 4. Reply with '3' to select 'Create support ticket'
r2 = post_json('/api/chat/message', {'session_id': session_id, 'message': '3', 'language': 'en'})
print('send2:', r2)

# 5. Send slot values
details = 'from Nagpur to Mumbai on 20th June, PNR 1234567890, train_number 12952, passenger_name John Doe, email john@example.com'
r3 = post_json('/api/chat/message', {'session_id': session_id, 'message': details, 'language': 'en'})
print('send3:', r3)

# 6. Confirm ticket creation with 'YES'
final = r3
if "would you like me to create a support ticket?" in r3.get('reply', '').lower():
    r4 = post_json('/api/chat/message', {'session_id': session_id, 'message': 'YES', 'language': 'en'})
    print('send4:', r4)
    final = r4

# 5. Verify ticket creation
ticket_id = final.get('ticket_id')
print('ticket_id:', ticket_id)

if ticket_id:
    t = get_json(f'/api/tickets/{ticket_id}')
    print('ticket:', json.dumps(t).encode('ascii', errors='replace').decode('ascii'))
else:
    print('No ticket created. Last reply:', final.get('reply'))

# 6. Verify ticket stored in SQLite
try:
    import os
    db_path = os.path.join(os.path.dirname(__file__), 'railai.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, type, priority, department FROM tickets ORDER BY rowid DESC LIMIT 5")
    rows = cur.fetchall()
    print('recent tickets (db):', rows)
    conn.close()
except Exception as e:
    print('sqlite error:', e)

# 7-9: Predictions: category, priority, department from response/ticket
print('category (reply):', final.get('category'))
if ticket_id:
    print('priority:', t.get('priority'))
    print('department:', t.get('department'))

# 10-11: Dashboard and analytics
stats = get_json('/api/dashboard/stats')
print('dashboard stats:', stats)
analytics = get_json('/api/analytics/data')
print('analytics:', json.dumps(analytics).encode('ascii', errors='replace').decode('ascii'))

# 12: Check for randomness markers (no random fields should be present)
def check_no_random(obj):
    s = json.dumps(obj)
    indicators = ['random', 'randint', 'Random', 'choice']
    for ind in indicators:
        if ind.lower() in s.lower():
            return False, ind
    return True, None

ok, ind = check_no_random(stats)
print('dashboard no-random:', ok, ind)
ok2, ind2 = check_no_random(analytics)
print('analytics no-random:', ok2, ind2)

print('chat history:', get_json(f'/api/chat/history/{session_id}'))
