import re
import json
import random
import sqlite3
from datetime import datetime
from database import get_db_connection
from ml_engine import predict_query
from sentiment_engine import analyze_sentiment

# Safe print helper to prevent UnicodeEncodeError in Windows stdout console environments
def safe_print(*args, **kwargs):
    new_args = []
    for arg in args:
        try:
            s = str(arg)
            new_args.append(s.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            new_args.append(repr(arg))
    try:
        import sys
        sys.stdout.write(" ".join(new_args) + "\n")
        sys.stdout.flush()
    except Exception:
        pass

print = safe_print

# ════════════════════════════════════════════════════════════
# SLOTS AND CATEGORIES SPECIFICATION
# ════════════════════════════════════════════════════════════
REQUIRED_SLOTS = {
    'refund': ['source_station', 'destination_station', 'pnr', 'journey_date'],
    'train_delay': ['train_number_or_name', 'source_station', 'destination_station'],
    'catering_complaint': ['train_number', 'coach_number', 'seat_number'],
    'payment_failure': ['transaction_id', 'source_station', 'destination_station', 'booking_date'],
    'booking_issue': ['train_number_or_name', 'passenger_name', 'booking_date'],
    'login_issue': ['username_or_mobile'],
    'cancellation': ['pnr', 'cancellation_reason'],
    'luggage_issue': ['pnr', 'item_desc']
}

def get_missing_slots(cat, slts):
    if cat not in REQUIRED_SLOTS:
        return []
    missing = []
    for slot in REQUIRED_SLOTS[cat]:
        if cat == 'train_delay' and slot == 'train_number_or_name':
            continue
        if slot not in slts or not slts[slot]:
            missing.append(slot)
    return missing

CATEGORY_WELCOME_MESSAGES = {
    'en': {
        'refund': "I'm sorry you're facing this issue.",
        'train_delay': "I understand your concern.",
        'catering_complaint': "I'm sorry about your experience.",
        'payment_failure': "I understand you had a payment failure.",
        'booking_issue': "I can help you with your booking issue.",
        'login_issue': "I understand you are having login issues.",
        'cancellation': "I can help with your cancellation request.",
        'luggage_issue': "I can register a complaint for your luggage issue."
    },
    'hi': {
        'refund': "मुझे खेद है कि आप इस समस्या का सामना कर रहे हैं।",
        'train_delay': "मैं आपकी चिंता समझता हूँ।",
        'catering_complaint': "मुझे आपके अनुभव के लिए खेद है।",
        'payment_failure': "मैं समझता हूँ कि आपकी भुगतान विफलता हुई है।",
        'booking_issue': "मैं आपकी बुकिंग समस्या में मदद कर सकता हूँ।",
        'login_issue': "मैं समझता हूँ कि आपको लॉगिन की समस्या हो रही है।",
        'cancellation': "मैं आपके टिकट रद्दीकरण अनुरोध में मदद कर सकता हूँ।",
        'luggage_issue': "मैं आपके सामान की समस्या के लिए शिकायत दर्ज कर सकता हूँ।"
    },
    'mr': {
        'refund': "मला खेद आहे की तुम्हाला या समस्येचा सामना करावा लागत आहे.",
        'train_delay': "मी तुमची चिंता समजू शकतो.",
        'catering_complaint': "तुमच्या वाईट अनुभवाबद्दल मला खेद वाटतो.",
        'payment_failure': "मी समजू शकतो की तुमची पेमेंट अयशस्वी झाली आहे.",
        'booking_issue': "मी तुमच्या बुकिंग समस्येचे निवारण करण्यात मदत करू शकतो.",
        'login_issue': "मी समजू शकतो की तुम्हाला लॉगिन करण्यात अडचण येत आहे.",
        'cancellation': "मी तिकीट रद्द करण्याच्या विनंतीत मदत करू शकतो.",
        'luggage_issue': "मी तुमच्या सामानाच्या समस्येची तक्रार नोंदवू शकतो."
    }
}

CATEGORY_PROBABLE_CAUSES = {
    'refund': {
        'en': "Possible reasons:\n• Settlement delay\n• Cancellation verification\n• Payment gateway processing",
        'hi': "संभावित कारण:\n• भुगतान निपटान में देरी (Settlement delay)\n• रद्दीकरण सत्यापन (Cancellation verification)\n• पेमेंट गेटवे प्रोसेसिंग (Payment gateway processing)",
        'mr': "संभाव्य कारणे:\n• सेटलमेंटला लागणारा वेळ (Settlement delay)\n• तिकीट रद्द करण्याची पडताळणी (Cancellation verification)\n• पेमेंट गेटवे प्रोसेसिंग (Payment gateway processing)"
    },
    'train_delay': {
        'en': "Possible reasons:\n• Operational congestion\n• Weather conditions\n• Signal issues\n• Track maintenance\n• Late incoming train",
        'hi': "संभावित कारण:\n• परिचालन भीड़ (Operational congestion)\n• मौसम की स्थिति (Weather conditions)\n• सिग्नल की समस्या (Signal issues)\n• ट्रैक रखरखाव (Track maintenance)\n• लेट आने वाली ट्रेन (Late incoming train)",
        'mr': "संभाव्य कारणे:\n• ऑपरेशनल गर्दी (Operational congestion)\n• हवामानाची परिस्थिती (Weather conditions)\n• सिग्नल अडचण (Signal issues)\n• रेल्वे मार्गाची दुरुस्ती (Track maintenance)\n• लेट येणारी गाडी (Late incoming train)"
    },
    'catering_complaint': {
        'en': "Possible causes:\n• Vendor quality issue\n• Incorrect meal delivery\n• Catering delay",
        'hi': "संभावित कारण:\n• विक्रेता गुणवत्ता समस्या (Vendor quality issue)\n• गलत भोजन वितरण (Incorrect meal delivery)\n• खानपान में देरी (Catering delay)",
        'mr': "संभाव्य कारणे:\n• विक्रेत्याची गुणवत्ता समस्या (Vendor quality issue)\n• चुकीचे जेवण देणे (Incorrect meal delivery)\n• केटरिंगला उशीर (Catering delay)"
    },
    'payment_failure': {
        'en': "Possible causes:\n• Bank timeout\n• Gateway issue\n• Network interruption",
        'hi': "संभावित कारण:\n• बैंक टाइमआउट (Bank timeout)\n• गेटवे समस्या (Gateway issue)\n• नेटवर्क व्यवधान (Network interruption)",
        'mr': "संभाव्य कारणे:\n• बँक टाइमआऊट (Bank timeout)\n• गेटवे अडचण (Gateway issue)\n• नेटवर्कमध्ये व्यत्यय (Network interruption)"
    },
    'booking_issue': {
        'en': "Booking issues can occur because of:\n• High server traffic during peak hours\n• Database synchronization delays\n• App cache corruption",
        'hi': "बुकिंग में समस्याएँ निम्नलिखित कारणों से हो सकती हैं:\n• पीक आवर्स के दौरान सर्वर पर भारी ट्रैफिक\n• डेटाबेस सिंक्रनाइज़ेशन में देरी\n• ऐप कैश ख़राब होना",
        'mr': "बुकिंगमध्ये अडचणी खालील कारणांमुळे होऊ शकतात:\n• पीक अवर्समध्ये सर्व्हरवर आलेला ताण\n• डेटाबेस समक्रमण विलंब\n• ॲप कॅशे खराब होणे"
    },
    'login_issue': {
        'en': "Login issues can occur because of:\n• Incorrect credentials entered\n• Network authentication errors\n• Account lockout policies",
        'hi': "लॉगिन समस्याएँ निम्नलिखित कारणों से हो सकती हैं:\n• दर्ज किए गए क्रेडेंशियल गलत होना\n• नेटवर्क प्रमाणीकरण त्रुटियाँ\n• खाता लॉकआउट नीतियां",
        'mr': "लॉगिन अडचण खालील कारणांमुळे होऊ शकते:\n• चुकीचा युजरनेम किंवा पासवर्ड\n• नेटवर्क प्रमाणीकरण त्रुटी\n• खाते लॉक पॉलिसी"
    },
    'cancellation': {
        'en': "Cancellation issues can occur because of:\n• Connection issues with booking database\n• Late requests submission\n• Payment gateway refunds delays",
        'hi': "रद्दीकरण समस्याएँ निम्नलिखित कारणों से हो सकती हैं:\n• बुकिंग डेटाबेस के साथ कनेक्शन समस्याएँ\n• देर से अनुरोध सबमिट करना\n• पेमेंट गेटवे रिफंड में देरी",
        'mr': "तिकीट रद्द करताना अडचणी खालील कारणांमुळे होऊ शकतात:\n• बुकिंग डेटाबेसशी संपर्क न होणे\n• उशिरा विनंती सादर करणे\n• पेमेंट गेटवे रिफंडमध्ये विलंब"
    },
    'luggage_issue': {
        'en': "Luggage issues can occur because of:\n• Misplacement during loading\n• Handling errors at station platforms\n• Wrong bag pickup by other passengers",
        'hi': "सामान की समस्याएँ निम्नलिखित कारणों से हो सकती हैं:\n• लोडिंग के दौरान विस्थापन\n• स्टेशन प्लेटफॉर्म पर हैंडलिंग त्रुटियां\n• अन्य यात्रियों द्वारा गलत बैग उठाना",
        'mr': "सामानाची अडचण खालील कारणांमुळे होऊ शकते:\n• लोडिंग दरम्यान सामान विस्थापन\n• स्टेशन प्लॅटफॉर्मवर हाताळणी त्रुटी\n• इतर प्रवाशांकडून चुकीचे सामान उचलणे"
    }
}

SUMMARY_SLOT_NAMES = {
    'en': {
        'source_station': 'Source',
        'destination_station': 'Destination',
        'pnr': 'PNR',
        'journey_date': 'Journey Date',
        'train_number_or_name': 'Train',
        'train_number': 'Train Number',
        'coach_number': 'Coach',
        'seat_number': 'Seat',
        'transaction_id': 'Transaction ID',
        'booking_date': 'Booking Date',
        'passenger_name': 'Passenger Name',
        'username_or_mobile': 'Username/Mobile',
        'cancellation_reason': 'Reason',
        'item_desc': 'Item Description'
    },
    'hi': {
        'source_station': 'Source',
        'destination_station': 'Destination',
        'pnr': 'PNR',
        'journey_date': 'Journey Date',
        'train_number_or_name': 'Train',
        'train_number': 'Train Number',
        'coach_number': 'Coach',
        'seat_number': 'Seat',
        'transaction_id': 'Transaction ID',
        'booking_date': 'Booking Date',
        'passenger_name': 'Passenger Name',
        'username_or_mobile': 'Username/Mobile',
        'cancellation_reason': 'Reason',
        'item_desc': 'Item Description'
    },
    'mr': {
        'source_station': 'Source',
        'destination_station': 'Destination',
        'pnr': 'PNR',
        'journey_date': 'Journey Date',
        'train_number_or_name': 'Train',
        'train_number': 'Train Number',
        'coach_number': 'Coach',
        'seat_number': 'Seat',
        'transaction_id': 'Transaction ID',
        'booking_date': 'Booking Date',
        'passenger_name': 'Passenger Name',
        'username_or_mobile': 'Username/Mobile',
        'cancellation_reason': 'Reason',
        'item_desc': 'Item Description'
    }
}


SLOT_FRIENDLY_NAMES = {
    'en': {
        'source_station': 'Source station',
        'destination_station': 'Destination station',
        'pnr': 'PNR number (if available)',
        'journey_date': 'Journey date',
        'train_number_or_name': 'Train number or train name',
        'train_number': 'Train number',
        'coach_number': 'Coach number',
        'seat_number': 'Seat number',
        'transaction_id': 'Transaction ID (if available)',
        'booking_date': 'Booking date',
        'passenger_name': 'Passenger name',
        'username_or_mobile': 'Registered mobile number or username',
        'cancellation_reason': 'Reason for cancellation',
        'item_desc': 'Description of the lost item'
    },
    'hi': {
        'source_station': 'प्रस्थान स्टेशन (Source station)',
        'destination_station': 'गंतव्य स्टेशन (Destination station)',
        'pnr': 'पीएनआर नंबर (PNR number) (यदि उपलब्ध हो)',
        'journey_date': 'यात्रा की तारीख (Journey date)',
        'train_number_or_name': 'ट्रेन नंबर या ट्रेन का नाम',
        'train_number': 'ट्रेन नंबर',
        'coach_number': 'कोच नंबर',
        'seat_number': 'सीट नंबर',
        'transaction_id': 'लेनदेन आईडी (Transaction ID) (यदि उपलब्ध हो)',
        'booking_date': 'बुकिंग की तारीख',
        'passenger_name': 'यात्री का नाम',
        'username_or_mobile': 'पंजीकृत मोबाइल नंबर या यूजरनेम',
        'cancellation_reason': 'रद्द करने का कारण',
        'item_desc': 'खोए हुए सामान का विवरण'
    },
    'mr': {
        'source_station': 'प्रारंभिक स्टेशन (Source station)',
        'destination_station': 'अंतिम स्टेशन (Destination station)',
        'pnr': 'पीएनआर क्रमांक (PNR number) (असल्यास)',
        'journey_date': 'प्रवासाची तारीख (Journey date)',
        'train_number_or_name': 'ट्रेन नंबर किंवा ट्रेनचे नाव',
        'train_number': 'ट्रेन नंबर',
        'coach_number': 'डबा क्रमांक (Coach number)',
        'seat_number': 'सीट क्रमांक (Seat number)',
        'transaction_id': 'व्यवहार आयडी (Transaction ID) (असल्यास)',
        'booking_date': 'बुकिंगची तारीख',
        'passenger_name': 'प्रवाशाचे नाव',
        'username_or_mobile': 'नोंदणीकृत मोबाईल नंबर किंवा युजरनेम',
        'cancellation_reason': 'तिकीट रद्द करण्याचे कारण',
        'item_desc': 'हरवलेल्या सामानाचे वर्णन'
    }
}

# ════════════════════════════════════════════════════════════
# MULTILINGUAL CHAT SYSTEM PROMPTS
# ════════════════════════════════════════════════════════════
GREETINGS = {
    'en': "Hello! I am **RailAI**, your offline railway assistant. How can I help you with your journey today?",
    'hi': "नमस्ते! मैं **RailAI** हूँ, आपका ऑफलाइन रेलवे सहायक। आज मैं आपकी यात्रा में किस प्रकार सहायता कर सकता हूँ?",
    'mr': "नमस्ते! मी **RailAI** आहे, आपला ऑफलाइन रेल्वे सहाय्यक. आज मी आपल्या प्रवासात कशी मदत करू शकतो?"
}

TICKET_CREATION_MSG = {
    'en': "Thank you for the information. I have auto-created ticket **{ticket_id}** and routed it to **{dept}** department. Priority: **{prio}**.\n\n**Potential Cause**: {cause}\n**Recommended Action**: {res}",
    'hi': "जानकारी के लिए धन्यवाद। मैंने ऑटो-टिकट **{ticket_id}** जनरेट कर दिया है और इसे **{dept}** विभाग को भेज दिया है। प्राथमिकता: **{prio}**।\n\n**संभावित कारण**: {cause}\n**अनुशंसित कार्रवाई**: {res}",
    'mr': "माहिती दिल्याबद्दल धन्यवाद. मी ऑटो-तिकीट **{ticket_id}** तयार केले आहे आणि ते **{dept}** विभागाकडे वर्ग केले आहे. प्राधान्य: **{prio}**.\n\n**संभाव्य कारण**: {cause}\n**शिफारस केलेली कृती**: {res}"
}

# ════════════════════════════════════════════════════════════
# INTENT DETECTION
# ════════════════════════════════════════════════════════════

CASUAL_KEYWORDS = [
    "hello", "hi", "hey", "thanks", "thank you",
    "bye", "good morning", "good afternoon",
    "good evening", "good night", "ok", "okay"
]

FAQ_KEYWORDS = [
    "refund policy",
    "rac",
    "tatkal",
    "train status",
    "how to cancel",
    "cancellation policy",
    "booking rules",
    "how to track train"
]

EMERGENCY_KEYWORDS = [
    "smoke",
    "fire",
    "bomb",
    "injured",
    "emergency",
    "accident",
    "medical emergency"
]

STATUS_KEYWORDS = [
    "ticket status",
    "check ticket",
    "track ticket",
    "status of ticket"
]

CASUAL_RESPONSES = {
    "hello": [
        "👋 Hello! How can I assist you today?",
        "Hi there! Need help with your railway journey?",
        "Welcome to RailAI! How may I help you?"
    ],

    "thanks": [
        "You're welcome. Is there anything else I can help you with today? 😊",
        "Happy to help! Let me know if you need anything else.",
        "Glad I could assist you."
    ],

    "bye": [
        "👋 Goodbye! Have a safe journey.",
        "Take care and travel safely!",
        "Thank you for using RailAI."
    ],

    "morning": [
        "🌅 Good morning! How can I help you today?"
    ],

    "night": [
        "🌙 Good night! Safe travels."
    ]
}

def detect_intent(text):
    text = text.lower().strip()

    if any(word in text for word in EMERGENCY_KEYWORDS):
        return "emergency"

    if any(word in text for word in STATUS_KEYWORDS):
        return "status"

    if any(word in text for word in FAQ_KEYWORDS):
        return "faq"

    # Casual intent is only verified if the input doesn't mention typical issues and is brief
    is_casual = False
    if any(word in text for word in CASUAL_KEYWORDS):
        complaint_words = ["refund", "money", "debited", "failed", "deducted", "booking", "tatkal", "seat", "login", "otp", "delay", "late", "platform", "cancel", "luggage", "bag", "stolen", "lost", "catering", "food", "hygiene"]
        if not any(cw in text for cw in complaint_words) and len(text.split()) <= 4:
            is_casual = True

    if is_casual:
        return "casual"

    return "complaint"

# Helper to generate unique ticket ID
def generate_ticket_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tickets ORDER BY rowid DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        try:
            last_id = int(row['id'].split('-')[1])
            conn.close()
            return f"TK-{last_id + 1}"
        except Exception:
            pass

    # Fallback: compute max numeric suffix from existing IDs
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
    conn.close()
    return f"TK-{max_num + 1}"


def get_mapped_department(category, predicted_dept=None):
    # Mapping according to user specifications:
    # Refund -> Finance & Refunds
    # Train Delay -> Operations Control
    # Food Complaint -> Catering Services
    # Booking Issue -> Reservation Support
    # Payment Failure -> Finance & Payments
    if category == 'refund':
        return 'Finance & Refunds'
    elif category == 'train_delay':
        return 'Operations Control'
    elif category == 'catering_complaint':
        return 'Catering Services'
    elif category == 'booking_issue':
        return 'Reservation Support'
    elif category == 'payment_failure':
        return 'Finance & Payments'
    
    # Fallback to map standard departments to friendly/corrected names
    dept_map = {
        'Finance': 'Finance & Refunds',
        'Ticketing': 'Ticketing Support',
        'IT Support': 'IT Support',
        'Operations': 'Operations Control',
        'Catering': 'Catering Services',
        'Security': 'Security & Emergency'
    }
    if predicted_dept in dept_map:
        return dept_map[predicted_dept]
    return predicted_dept or 'Unassigned'
def save_chat_message(session_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", (session_id, role, content, now_str))
    conn.commit()
    conn.close()


BLACKLIST_WORDS = {
    # English verbs & common complaint/operational keywords
    'train', 'delayed', 'delay', 'late', 'early', 'running', 'status', 'time', 'schedule', 'platform', 'board', 'announcement', 'announcements',
    'refund', 'refunds', 'money', 'paisa', 'rupees', 'rs', 'amount', 'debited', 'failed', 'deducted', 'payment', 'transaction', 'txn', 'card', 'bank',
    'booking', 'bookings', 'tatkal', 'seat', 'coach', 'berth', 'login', 'otp', 'password', 'user', 'username', 'id', 'credentials',
    'cancel', 'cancellation', 'cancellations', 'radd', 'luggage', 'bag', 'bags', 'baggage', 'stolen', 'lost', 'found', 'missing', 'handbag', 'suitcase',
    'catering', 'food', 'hygiene', 'pantry', 'meal', 'lunch', 'dinner', 'breakfast', 'tea', 'water', 'bottle', 'clean', 'dirty', 'bad', 'quality',
    'security', 'emergency', 'accident', 'rpf', 'tte', 'captain', 'police', 'smoke', 'fire', 'bomb', 'injured', 'medical', 'danger',
    'problem', 'issue', 'issues', 'error', 'errors', 'unable', 'cannot', 'cant', 'help', 'please', 'thanks', 'thank', 'welcome', 'journey', 'route',
    'station', 'source', 'destination', 'from', 'to', 'in', 'on', 'at', 'for', 'with', 'by', 'about', 'of', 'and', 'or', 'not', 'no', 'yes',
    'my', 'your', 'his', 'her', 'their', 'our', 'its', 'me', 'you', 'him', 'them', 'us', 'i', 'we', 'they', 'he', 'she', 'it',
    'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'done', 'doing',
    'would', 'should', 'could', 'will', 'shall', 'can', 'may', 'might', 'must',
    'where', 'what', 'when', 'who', 'why', 'how', 'which', 'this', 'that', 'these', 'those',
    'received', 'pending', 'success', 'fail', 'failure', 'failures', 'complaint', 'complaints',
    'a', 'an', 'the', 'some', 'any', 'every', 'each', 'all', 'both', 'either', 'neither',
    # Hindi/Marathi common complaint terms
    'tikit', 'ticket', 'paise', 'nahi', 'aaya', 'gaya', 'kat', 'hua', 'bhala', 'ata', 'kiti', 'vel',
    'u', 'उशिरा', 'वेळ', 'अडचण', 'तक्रार', 'मदत', 'खतरा', 'पैसे', 'भेटत', 'नाही', 'झाले', 'हवा', 'परत',
    'मिळाला', 'केला', 'केले', 'करा', 'शिकायत', 'नुकसान', 'खराब', 'समस्या', 'बुकिंग', 'रद्द', 'मदद', 'कृपया'
}

def is_valid_entity(name):
    if not name:
        return False
    name_clean = name.strip()
    name_lower = name_clean.lower()
    # Reject if it's in blacklist
    if name_lower in BLACKLIST_WORDS:
        return False
    # Reject if it's too short (less than 3 characters)
    if len(name_clean) < 3:
        return False
    # Reject if it contains digits
    if any(c.isdigit() for c in name_clean):
        return False
    # Reject if it contains typical non-word patterns or punctuation
    if not re.match(r'^[a-zA-Z\s]+$', name_clean) and not re.match(r'^[\u0900-\u097F\s]+$', name_clean):
        return False
    return True

def is_valid_train_name(name):
    if not name:
        return False
    name_clean = name.strip()
    name_lower = name_clean.lower()
    if name_lower in BLACKLIST_WORDS:
        return False
    if any(c.isdigit() for c in name_clean):
        return True
    train_keywords = ["express", "rajdhani", "shatabdi", "duronto", "local", "mail", "passenger", "intercity", "garib rath"]
    if any(tk in name_lower for tk in train_keywords):
        return True
    if len(name_clean.split()) > 3:
        return False
    return True


# Extract text slots using regular expressions or fallbacks
def extract_slot_value(text, slot_name, slot_def, category, existing_slots, is_direct_prompt=False):
    text_clean = text.strip()
    text_lower = text_clean.lower()

    # Heuristic for optional inputs (like pnr or transaction_id)
    # If the user explicitly says they don't have it, we fill it with "Not Available"
    if slot_name in ['pnr', 'transaction_id']:
        negative_pattern = r'\b(no|don\'t have|not available|none|na|n/a|dont have|nahi hai|नहीं है|नाही|no pnr|no txn)\b'
        if re.search(negative_pattern, text_lower) and len(text_clean.split()) <= 4:
            return "Not Available"

    # 1. PNR extraction (exactly 10 digits)
    if slot_name == 'pnr':
        matches = re.findall(r'\b\d{10}\b', text)
        if matches:
            return matches[0]

    # 2. Train Number (exactly 5 digits)
    if slot_name in ['train_number', 'train_number_or_name']:
        matches = re.findall(r'\b\d{5}\b', text)
        if matches:
            return matches[0]
        # For train_number_or_name, if it contains typical train keywords or is valid train name
        if slot_name == 'train_number_or_name':
            if is_valid_train_name(text_clean):
                return text_clean

    # 3. Coach Number
    if slot_name == 'coach_number':
        coach_match = re.search(r'\b(?:coach|coach_number|coach\s+number)?\s*([a-zA-Z]{1,2}\d{1,2})\b', text, re.IGNORECASE)
        if coach_match:
            return coach_match.group(1).upper()
        if len(text_clean.split()) <= 2 and re.match(r'^[a-zA-Z]{1,2}\d{1,2}$', text_clean):
            return text_clean.upper()
        if is_direct_prompt and len(text_clean.split()) <= 2:
            return text_clean.upper()

    # 4. Seat Number
    if slot_name == 'seat_number':
        seat_match = re.search(r'\b(?:seat|seat_number|seat\s+number|berth)?\s*(\d{1,3})\b', text, re.IGNORECASE)
        if seat_match:
            val = seat_match.group(1)
            if len(val) <= 3:
                return val
        if text_clean.isdigit() and len(text_clean) <= 3:
            return text_clean
        if is_direct_prompt and text_clean.isdigit() and len(text_clean) <= 3:
            return text_clean

    # 5. Transaction ID
    if slot_name == 'transaction_id':
        txn_match = re.search(r'\b(?:txn|transaction|id|ref)?\s*([a-zA-Z0-9]{6,20})\b', text, re.IGNORECASE)
        if txn_match:
            val = txn_match.group(1)
            if not val.isdigit() or len(val) >= 6:
                return val
        if is_direct_prompt and len(text_clean.split()) <= 3:
            return text_clean

    # 6. Dates (journey_date, booking_date)
    if slot_name in ['journey_date', 'booking_date']:
        date_pattern = r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b'
        date_match = re.search(date_pattern, text)
        if date_match:
            return date_match.group(0)
        
        word_date_pattern = r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b'
        word_date_match = re.search(word_date_pattern, text, re.IGNORECASE)
        if word_date_match:
            return word_date_match.group(0)
        
        relative_dates = ["today", "tomorrow", "yesterday", "day after tomorrow", "आज", "कल", "उद्या", "आजच"]
        for rd in relative_dates:
            if rd in text_lower:
                return rd
        
        if is_direct_prompt:
            if len(text_clean.split()) <= 4 and not any(word in text_lower for word in ["refund", "ticket", "issue", "failed"]):
                return text_clean

    # 7. Station Names (source_station, destination_station)
    if slot_name in ['source_station', 'destination_station']:
        route_match = re.search(
            r'(?:from\s+)?([a-zA-Z\s]+)\s*(?:to|→|->)\s*([a-zA-Z\s]+)',
            text,
            re.IGNORECASE
        )
        if route_match:
            src = route_match.group(1).strip()
            dst = route_match.group(2).strip()
            src = re.sub(r'.*\bfrom\s+', '', src, flags=re.IGNORECASE).strip()
            dst = re.sub(r'\s+\bto\b.*', '', dst, flags=re.IGNORECASE).strip()
            if is_valid_entity(src) and is_valid_entity(dst):
                if slot_name == 'source_station':
                    return src
                else:
                    return dst

        from_match = re.search(r'\bfrom\s+([a-zA-Z\s]+)\b', text, re.IGNORECASE)
        if from_match and slot_name == 'source_station':
            candidate = from_match.group(1).strip()
            if is_valid_entity(candidate):
                return candidate

        to_match = re.search(r'\bto\s+([a-zA-Z\s]+)\b', text, re.IGNORECASE)
        if to_match and slot_name == 'destination_station':
            candidate = to_match.group(1).strip()
            if is_valid_entity(candidate):
                return candidate

        if is_direct_prompt:
            words = text_clean.split()
            if len(words) <= 3 and not any(c.isdigit() for c in text_clean):
                if is_valid_entity(text_clean):
                    return text_clean

    # 8. Passenger Name
    if slot_name == 'passenger_name':
        name_match = re.search(
            r'\b(?:my name is|passenger name(?: is)?|passenger_name|name is|this is|name:?)\s+([a-zA-Z\s]+)',
            text,
            re.IGNORECASE
        )
        if name_match:
            candidate = name_match.group(1).strip()
            candidate = re.sub(r'\b(?:please|and|for|my|ticket|pnr|email|train|train_number|route|station|rs|amount)\b.*', '', candidate, flags=re.IGNORECASE).strip()
            if is_valid_entity(candidate) and len(candidate.split()) <= 4:
                return candidate

        if is_direct_prompt:
            words = text_clean.split()
            if len(words) <= 4 and not any(c.isdigit() for c in text_clean):
                if is_valid_entity(text_clean):
                    return text_clean

    # 9. Username or Mobile
    if slot_name == 'username_or_mobile':
        matches = re.findall(r'\b(?:\d{10}|[a-zA-Z0-9_]{3,15})\b', text)
        if matches:
            for val in matches:
                if val.lower() not in ["login", "user", "pass", "help"]:
                    return val
        if is_direct_prompt and len(text_clean.split()) <= 2:
            return text_clean

    # 10. Cancellation Reason
    if slot_name == 'cancellation_reason':
        if is_direct_prompt:
            if len(text_clean) >= 4 and not any(word in text_lower for word in ["pnr", "ticket", "cancel"]):
                return text_clean

    # 11. Item Description
    if slot_name == 'item_desc':
        desc_match = re.search(r'(?:lost|left|missing|stolen)\s+([a-zA-Z0-9\s,\.-]+)', text, re.IGNORECASE)
        if desc_match:
            return desc_match.group(1).strip()
        if is_direct_prompt:
            if len(text_clean) >= 4:
                return text_clean

    return None


def get_casual_response(text):
    text = text.lower()

    if any(word in text for word in ["thank you", "thanks"]):
        return random.choice(CASUAL_RESPONSES["thanks"])

    if any(word in text for word in ["bye", "goodbye"]):
        return random.choice(CASUAL_RESPONSES["bye"])

    if "good morning" in text:
        return random.choice(CASUAL_RESPONSES["morning"])

    if "good night" in text:
        return random.choice(CASUAL_RESPONSES["night"])

    if any(word in text for word in ["hello", "hi", "hey"]):
        return random.choice(CASUAL_RESPONSES["hello"])

    return random.choice(CASUAL_RESPONSES["hello"])

def find_alternatives_in_dataset(source, destination):
    s_clean = (source or '').lower().strip()
    d_clean = (destination or '').lower().strip()
    
    if not s_clean or not d_clean:
        return []
        
    mappings = {
        'mumbai': 'mum', 'delhi': 'del', 'howrah': 'hwh', 'ahmedabad': 'ahm', 'amritsar': 'asr',
        'cstm': 'mum', 'bct': 'mum', 'ndls': 'del', 'hwh': 'howrah', 'ahm': 'ahmedabad', 'asr': 'amritsar'
    }
    
    s_code = mappings.get(s_clean, s_clean[:3])
    d_code = mappings.get(d_clean, d_clean[:3])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT train_id, name, route, status, delay FROM train_status")
    all_trains = cursor.fetchall()
    conn.close()
    
    alternatives = []
    for t in all_trains:
        t_route = t['route'].lower()
        parts = re.split(r'→|-|->', t_route)
        if len(parts) == 2:
            t_src = parts[0].strip()
            t_dst = parts[1].strip()
            t_src_mapped = mappings.get(t_src, t_src[:3])
            t_dst_mapped = mappings.get(t_dst, t_dst[:3])
            
            if (s_code in t_src_mapped or t_src_mapped in s_code) and (d_code in t_dst_mapped or t_dst_mapped in d_code):
                if t['status'] == 'on-time':
                    alternatives.append(f"Train {t['train_id']} ({t['name']}) - On Time")
                else:
                    alternatives.append(f"Train {t['train_id']} ({t['name']}) - Delayed by {t['delay']} mins")
    return alternatives


TROUBLESHOOTING_STEPS = {
    'refund': {
        'en': "Suggested actions:\n• Verify cancellation status\n• Check original payment account\n• Confirm whether 7 working days have passed",
        'hi': "सुझाए गए कदम:\n• रद्दीकरण स्थिति सत्यापित करें\n• मूल भुगतान खाते की जाँच करें\n• पुष्टि करें कि क्या 7 कार्य दिवस बीत चुके हैं",
        'mr': "सुचविलेल्या कृती:\n• तिकीट रद्द झाल्याची खात्री करा\n• मूळ बँक खाते तपासा\n• ७ कामाचे दिवस झाले आहेत का याची खात्री करा"
    },
    'train_delay': {
        'en': "Suggested actions:\n• Check train running status\n• Verify platform announcements\n• Check railway notifications",
        'hi': "सुझाए गए कदम:\n• ट्रेन चलने की स्थिति की जाँच करें\n• प्लेटफार्म घोषणाओं को सत्यापित करें\n• रेलवे सूचनाओं की जाँच करें",
        'mr': "सुचविलेल्या कृती:\n• ट्रेनची धावण्याची स्थिती तपासा\n• प्लॅटफॉर्मवरील घोषणांची खात्री करा\n• रेल्वेच्या सूचना तपासा"
    },
    'catering_complaint': {
        'en': "Suggested actions:\n• Verify coach and seat details\n• Contact onboard catering staff",
        'hi': "सुझाए गए कदम:\n• कोच और सीट विवरण सत्यापित करें\n• ऑनबोर्ड खानपान कर्मचारियों से संपर्क करें",
        'mr': "सुचविलेल्या कृती:\n• डबा आणि सीटचा तपशील तपासा\n• ऑनबोर्ड केटरिंग कर्मचाऱ्यांशी संपर्क साधा"
    },
    'payment_failure': {
        'en': "Suggested actions:\n• Check account statement\n• Verify transaction status\n• Wait for automatic reversal",
        'hi': "सुझाए गए कदम:\n• खाता विवरण की जाँच करें\n• लेनदेन की स्थिति सत्यापित करें\n• स्वचालित धनवापसी की प्रतीक्षा करें",
        'mr': "सुचविलेल्या कृती:\n• बँक खाते स्टेटमेंट तपासा\n• व्यवहाराची स्थिती तपासा\n• पैसे परत मिळण्यासाठी वाट पहा"
    },
    'booking_issue': {
        'en': "Booking Issue Troubleshooting Steps:\n1. Avoid booking during peak hours (e.g. daily Tatkal hours 10 AM - 12 PM) when server load is highest.\n2. Clear your mobile app cache, or use a web browser in incognito mode.\n3. Switch payment modes (e.g. from Netbanking to UPI) to reduce gateway transaction failures.",
        'hi': "बुकिंग समस्या निवारण चरण:\n1. पीक आवर्स (उदा. दैनिक तत्काल घंटे 10 AM - 12 PM) के दौरान बुकिंग करने से बचें जब सर्वर लोड सबसे अधिक होता है।\n2. अपने मोबाइल ऐप कैशे को साफ़ करें, या गुप्त (incognito) मोड में वेब ब्राउज़र का उपयोग करें।\n3. भुगतान विफलता को कम करने के लिए भुगतान मोड (जैसे नेटबैंकिंग से यूपीआई) बदलें।",
        'mr': "बुकिंग निवारण पायऱ्या:\n१. पीक अवर्समध्ये (सकाळी १० ते दुपारी १२ तत्काल बुकिंग वेळी) बुकिंग करणे टाळा.\n२. मोबाईल ॲपची कॅशे साफ करा किंवा ब्राउझरवर इनकॉग्निटो मोडमध्ये उघडा.\n३. पेमेंट अयशस्वी होणे टाळण्यासाठी दुसरा पेमेंट पर्याय (UPI किंवा कार्ड) वापरा."
    },
    'login_issue': {
        'en': "Login Troubleshooting Steps:\n1. Click 'Forgot Password' to reset credentials and trigger a verification OTP.\n2. Clear the application data storage or reinstall the app to update the localized security certificates.\n3. Wait 15 minutes if your account is locked due to consecutive wrong inputs.",
        'hi': "लॉगिन समस्या निवारण चरण:\n1. क्रेडेंशियल रीसेट करने और सत्यापन ओटीपी प्राप्त करने के लिए 'पासवर्ड भूल गए' पर क्लिक करें।\n2. स्थानीय सुरक्षा प्रमाणपत्रों को अपडेट करने के लिए ऐप डेटा साफ़ करें या ऐप को फिर से इंस्टॉल करें।\n3. गलत पासवर्ड के कारण खाता लॉक होने पर 15 मिनट प्रतीक्षा करें।",
        'mr': "लॉगिन निवारण पायऱ्या:\n१. पासवर्ड विसरल्यास 'Forgot Password' वापरून नवीन पासवर्ड तयार करा.\n२. स्थानिक सुरक्षा प्रमाणपत्रे अपडेट करण्यासाठी ॲप डेटा साफ करा किंवा ॲप पुन्हा इन्स्टॉल करा.\n३. सलग चुकीचे पासवर्ड टाकल्यामुळे खाते लॉक झाले असल्यास १५ मिनिटे वाट पहा."
    },
    'cancellation': {
        'en': "Cancellation Troubleshooting Steps:\n1. Perform cancellation requests online prior to chart preparation for optimal refund eligibility.\n2. Ensure your internet connection is stable so the cancellation ticket handshakes are completed successfully.\n3. Verify passenger boarding station updates before cancelling.",
        'hi': "रद्दीकरण समस्या निवारण चरण:\n1. इष्टतम रिफंड पात्रता के लिए चार्ट तैयार होने से पहले ऑनलाइन रद्दीकरण अनुरोध करें।\n2. सुनिश्चित करें कि आपका इंटरनेट कनेक्शन स्थिर है ताकि रद्दीकरण प्रक्रिया सफलतापूर्वक पूरी हो सके।\n3. रद्द करने से पहले यात्री बोर्डिंग स्टेशन अपडेट सत्यापित करें।",
        'mr': "तिकीट रद्द करण्याचे निवारण पायऱ्या:\n१. योग्य रिफंड मिळण्यासाठी चार्ट तयार होण्यापूर्वी ऑनलाईन तिकीट रद्द करा.\n२. इंटरनेट कनेक्शन स्थिर असल्याची खात्री करा जेणेकरून रद्द करण्याची प्रक्रिया यशस्वी होईल.\n३. रद्द करण्यापूर्वी प्रवाशाचे बोर्डिंग स्टेशन तपासून घ्या."
    },
    'luggage_issue': {
        'en': "Luggage Troubleshooting Steps:\n1. Report the lost baggage detail immediately to the RPF station platform control room.\n2. Make sure you keep your booking ticket/PNR copy handy.\n3. Note down descriptions of neighboring seat passengers who boarded/deboarded recently.",
        'hi': "सामान समस्या निवारण चरण:\n1. खोए हुए सामान के विवरण की रिपोर्ट तुरंत आरपीएफ स्टेशन प्लेटफॉर्म नियंत्रण कक्ष को दें।\n2. सुनिश्चित करें कि आपके पास बुकिंग टिकट/पीएनआर की प्रति उपलब्ध हो।\n3. आसपास के यात्रियों का विवरण नोट करें जो हाल ही में चढ़े या उतरे हैं।",
        'mr': "सामान निवारण पायऱ्या:\n१. हरवलेल्या सामानाची माहिती तात्काळ रेल्वे स्थानकावरील सुरक्षा कक्षात (RPF) द्या.\n२. आपल्याकडे तिकीट किंवा पीएनआरची प्रत जवळ ठेवा.\n३. आसपासच्या प्रवाशांची माहिती नोंदवून घ्या जे नुकतेच ट्रेनमधून चढले किंवा उतरले."
    }
}

STATUS_GUIDANCE = {
    'refund': {
        'en': "Refund Status Guidance:\n- If you cancelled your ticket online, refunds are automatically initiated.\n- Typically, refunds are processed back to the original bank account or booking card within 3 to 7 working days. Please check your bank statements after this period.",
        'hi': "रिफंड स्थिति मार्गदर्शन:\n- यदि आपने अपना टिकट ऑनलाइन रद्द किया है, तो रिफंड स्वचालित रूप से शुरू हो जाता है।\n- आमतौर पर, रिफंड 3 से 7 कार्य दिवसों के भीतर मूल बैंक खाते या बुकिंग कार्ड में वापस आ जाता है। कृपया इस अवधि के बाद अपना बैंक स्टेटमेंट जांचें।",
        'mr': "रिफंड स्थिती मार्गदर्शन:\n- आपण तिकीट ऑनलाईन रद्द केले असल्यास, रिफंडची प्रक्रिया आपोआप सुरू होते.\n- सामान्यतः ३ ते ७ कामाच्या दिवसांत मूळ बँक खात्यात पैसे परत जमा केले जातात. या कालावधीनंतर आपले बँक स्टेटमेंट तपासा."
    },
    'train_delay': {
        'en': "Train Delay Guidance:\n- Train delays occur due to signaling maintenance, track engineering, or visibility issues.\n- Please monitor station platform audio announcements for scheduled departure revisions.",
        'hi': "ट्रेन देरी मार्गदर्शन:\n- सिग्नल रखरखाव, ट्रैक इंजीनियरिंग, या दृश्यता समस्याओं के कारण ट्रेन में देरी होती है।\n- कृपया निर्धारित प्रस्थान समय में बदलाव के लिए स्टेशन प्लेटफॉर्म घोषणाओं को सुनते रहें।",
        'mr': "ट्रेन विलंब मार्गदर्शन:\n- सिग्नलची कामे, रेल्वे मार्गाची दुरुस्ती किंवा हवामानातील बदलामुळे गाड्यांना उशीर होतो.\n- कृपया नवीन वेळेच्या माहितीसाठी स्थानकावरील घोषणांकडे लक्ष द्या."
    },
    'catering_complaint': {
        'en': "Catering Quality Guidance:\n- All catering operations are monitored under strict hygiene standards by IRCTC food safety officers.\n- Pantry car staff are legally bound to display standard price menus. Fines are imposed on vendors for overcharging or poor service.",
        'hi': "कैटरिंग गुणवत्ता मार्गदर्शन:\n- आईआरसीटीसी खाद्य सुरक्षा अधिकारियों द्वारा सख्त स्वच्छता मानकों के तहत सभी खान-पान कार्यों की निगरानी की जाती है।\n- पैंट्री कार कर्मचारी मानक मूल्य मेनू प्रदर्शित करने के लिए कानूनी रूप से बाध्य हैं। विक्रेताओं पर अधिक शुल्क या खराब सेवा के लिए जुर्माना लगाया जाता है।",
        'mr': "खान-पान दर्जा मार्गदर्शन:\n- सर्व केटरिंग सेवांवर आयआरसीटीसी (IRCTC) च्या अन्न सुरक्षा अधिकाऱ्यांचे बारीक लक्ष असते.\n- पॅन्ट्री कार कर्मचाऱ्यांना प्रमाणित दरपत्रक लावणे बंधनकारक आहे. चुकीचे दर आकारल्यास कंत्राटदाराला दंड केला जातो."
    },
    'booking_issue': {
        'en': "Booking Issue Guidance:\n- Failed booking attempts where amount was debited but no ticket generated will undergo automatic reconciliation.\n- Your bank will credit the amount back to your original source account within 3 to 5 business days.",
        'hi': "बुकिंग समस्या मार्गदर्शन:\n- असफल बुकिंग प्रयास जहां राशि काट ली गई थी लेकिन कोई टिकट नहीं बना, वह स्वचालित रूप से सुलझ जाएगी।\n- आपका बैंक 3 से 5 कार्य दिवसों के भीतर राशि को आपके मूल खाते में वापस भेज देगा।",
        'mr': "बुकिंग समस्या मार्गदर्शन:\n- तिकीट बुक न होता पैसे वजा झाले असल्यास बँक व्यवहाराची पडताळणी आपोआप होते.\n- बँक ३ ते ५ कामाच्या दिवसांत वजा झालेली रक्कम आपल्या मूळ खात्यात वर्ग करेल."
    },
    'payment_failure': {
        'en': "Payment Failure Guidance:\n- Transactions failing at the 3D-Secure authentication stage or bank gateway will be rejected.\n- No funds are permanently held by RailAI; debited amounts are auto-refunded to the card source within 24-48 hours.",
        'hi': "भुगतान विफलता मार्गदर्शन:\n- 3D-सिक्योर प्रमाणीकरण चरण या बैंक गेटवे पर विफल होने वाले लेनदेन को अस्वीकार कर दिया जाता है।\n- रेलएआई द्वारा कोई भी राशि रोकी नहीं जाती है; काटे गए पैसे 24-48 घंटों के भीतर स्वतः वापस आ जाते हैं।",
        'mr': "पेमेंट अपयश मार्गदर्शन:\n- बँकेच्या गेटवेवर किंवा सुरक्षेच्या कारणास्तव नाकारले गेलेले व्यवहार रद्द केले जातात.\n- कोणतीही रक्कम रेल्वे प्रशासनाकडे राहत नाही; वजा झालेले पैसे २४-४८ तासांत खात्यात परत मिळतात."
    },
    'login_issue': {
        'en': "Login Lockout Guidance:\n- To protect passenger privacy, IRCTC system lockouts occur after 3 consecutive wrong password attempts.\n- Account unlock triggers automatically after 15 minutes, or you can clear cookies to retry instantly.",
        'hi': "लॉगिन लॉकआउट मार्गदर्शन:\n- यात्री गोपनीयता की सुरक्षा के लिए, लगातार 3 गलत पासवर्ड प्रयासों के बाद सिस्टम लॉक हो जाता है।\n- खाता 15 मिनट के बाद स्वचालित रूप से अनलॉक हो जाता है, या तुरंत प्रयास करने के लिए कुकीज़ साफ़ कर सकते हैं।",
        'mr': "लॉगिन लॉकआउट मार्गदर्शन:\n- प्रवाशांच्या गोपनीयतेसाठी, सलग ३ वेळा चुकीचा पासवर्ड टाकल्यास खाते ब्लॉक केले जाते.\n- १५ मिनिटांनंतर खाते आपोआप अनलॉक होते, किंवा कुकीज साफ करून लगेच प्रयत्न करू शकता."
    },
    'cancellation': {
        'en': "Cancellation Refund Guidance:\n- Refund deduction slabs: Confirmed tickets cancelled >48 hours before departure attract flat cancellation charges.\n- No refund is available for cancelled confirmed Tatkal tickets except in delayed train scenarios.",
        'hi': "रद्दीकरण रिफंड मार्गदर्शन:\n- रिफंड शुल्क: प्रस्थान से 48 घंटे पहले रद्द किए गए कन्फर्म टिकटों पर फ्लैट शुल्क लगता है।\n- कन्फर्म तत्काल टिकट रद्द करने पर कोई रिफंड नहीं मिलता है, केवल ट्रेन विलंब की स्थिति को छोड़कर।",
        'mr': "तिकीट रद्द करण्याचे रिफंड मार्गदर्शन:\n- रिफंड दरपत्रक: रेल्वे सुटण्याच्या ४८ तास आधी तिकीट रद्द केल्यास कमी शुल्क आकारले जाते.\n- कन्फर्म तत्काल तिकीट रद्द केल्यास कोणताही रिफंड मिळत नाही, केवळ ट्रेन लेट असल्यासच नियम लागू होतो."
    },
    'luggage_issue': {
        'en': "Luggage Loss Guidance:\n- RPF coordinates lost luggage recovery across platforms via centralized Lost and Found registrations.\n- Unclaimed luggage retrieved by security teams is deposited in the station master's parcel custody room.",
        'hi': "सामान गुम होने का मार्गदर्शन:\n- आरपीएफ खोए हुए सामान की खोज के लिए प्लेटफार्मों पर समन्वय करता है।\n- सुरक्षा टीमों द्वारा बरामद लावारिस सामान स्टेशन मास्टर के पार्सल कस्टडी रूम में जमा किया जाता है।",
        'mr': "सामान गहाळ मार्गदर्शन:\n- रेल्वे सुरक्षा दल (RPF) स्थानकांवर हरवलेल्या सामानाचा शोध घेण्यासाठी मदत करते.\n- सापडलेले बेवारस सामान स्टेशन मास्टरच्या पार्सल कार्यालयात जमा केले जाते."
    }
}
OPTION2_LABELS = {
    'refund': {
        'en': "Refund status guidance",
        'hi': "रिफंड स्थिति मार्गदर्शन",
        'mr': "रिफंड स्थिती मार्गदर्शन"
    },
    'train_delay': {
        'en': "Alternative trains / schedule guidance",
        'hi': "वैकल्पिक ट्रेनें / समय सारणी मार्गदर्शन",
        'mr': "पर्यायी ट्रेन्स / वेळापत्रक मार्गदर्शन"
    },
    'catering_complaint': {
        'en': "Catering quality guidance",
        'hi': "कैटरिंग गुणवत्ता मार्गदर्शन",
        'mr': "खान-पान दर्जा मार्गदर्शन"
    },
    'booking_issue': {
        'en': "Booking failure guidance",
        'hi': "बुकिंग विफलता मार्गदर्शन",
        'mr': "बुकिंग अपयश मार्गदर्शन"
    },
    'payment_failure': {
        'en': "Payment failure guidance",
        'hi': "भुगतान विफलता मार्गदर्शन",
        'mr': "पेमेंट अपयश मार्गदर्शन"
    },
    'login_issue': {
        'en': "Login lockout guidance",
        'hi': "लॉगिन लॉकआउट मार्गदर्शन",
        'mr': "लॉगिन लॉकआउट मार्गदर्शन"
    },
    'cancellation': {
        'en': "Cancellation policy guidance",
        'hi': "रद्दीकरण नीति मार्गदर्शन",
        'mr': "तिकीट रद्द करण्याचे नियम मार्गदर्शन"
    },
    'luggage_issue': {
        'en': "Luggage loss guidance",
        'hi': "सामान गुम होने का मार्गदर्शन",
        'mr': "सामान गहाळ मार्गदर्शन"
    }
}

INTRO_SUMMARIES = {
    'refund': {
        'en': "Based on the details provided, refund processing may take 3-7 working days.",
        'hi': "प्रदान किए गए विवरण के आधार पर, धनवापसी (refund) प्रसंस्करण में 3-7 कार्य दिवस लग सकते हैं।",
        'mr': "दिलेल्या तपशिलानुसार, रिफंड मिळण्यास ३-७ कामाचे दिवस लागू शकतात."
    },
    'train_delay': {
        'en': "Based on the details provided, train status checking will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, ट्रेन की स्थिति की जांच की जाएगी।",
        'mr': "दिलेल्या माहितीनुसार, ट्रेनच्या सद्यस्थितीची तपासणी केली जाईल."
    },
    'catering_complaint': {
        'en': "Based on the details provided, food quality check will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, भोजन की गुणवत्ता की जांच की जाएगी।",
        'mr': "दिलेल्या माहितीनुसार, जेवणाच्या दर्जाची तपासणी केली जाईल."
    },
    'booking_issue': {
        'en': "Based on the details provided, booking verification will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, बुकिंग सत्यापन किया जाएगा।",
        'mr': "दिलेल्या माहितीनुसार, बुकिंगची पडताळणी केली जाईल."
    },
    'payment_failure': {
        'en': "Based on the details provided, transaction reconciliation will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, लेनदेन मिलान किया जाएगा।",
        'mr': "दिलेल्या माहितीनुसार, बँक व्यवहाराची पडताळणी केली जाईल."
    },
    'login_issue': {
        'en': "Based on the details provided, login verification will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, लॉगिन सत्यापन किया जाएगा।",
        'mr': "दिलेल्या माहितीनुसार, लॉगिनची पडताळणी केली जाईल."
    },
    'cancellation': {
        'en': "Based on the details provided, cancellation validation will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, रद्दीकरण सत्यापन किया जाएगा।",
        'mr': "दिलेल्या माहितीनुसार, तिकीट रद्द करण्याची पडताळणी केली जाईल."
    },
    'luggage_issue': {
        'en': "Based on the details provided, luggage search verification will be performed.",
        'hi': "प्रदान किए गए विवरण के आधार पर, सामान की खोज का सत्यापन किया जाएगा।",
        'mr': "दिलेल्या माहितीनुसार, सामानाच्या शोधाची पडताळणी केली जाईल."
    }
}


def extract_bullets_only(text):
    if not text:
        return ""
    lines = text.split('\n')
    bullets = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('•') or stripped.startswith('*') or stripped.startswith('-') or (stripped and stripped[0].isdigit()) or (stripped and stripped[0] in ['१', '२', '३', '४', '५', '६', '७', '८', '९']):
            clean_line = re.sub(r'^(?:•|\*|-|\d+\.|\d+\)|\w+\.|[\u0967-\u096F]+\.)\s*', '', stripped)
            bullets.append(f"• {clean_line}")
    return "\n".join(bullets)


PROBLEM_SOLVING_HEADERS = {
    'possible_reasons': {
        'en': "Possible reasons:",
        'hi': "संभावित कारण:",
        'mr': "संभाव्य कारणे:"
    },
    'suggested_actions': {
        'en': "Suggested actions:",
        'hi': "सुझाए गए कदम:",
        'mr': "सुचविलेल्या कृती:"
    }
}

PROBLEM_SOLVING_QUESTIONS = {
    'refund': {
        'en': "Was this information helpful?",
        'hi': "क्या यह जानकारी मददगार थी?",
        'mr': "ही माहिती उपयुक्त होती का?"
    },
    'default': {
        'en': "Did this solve your problem?",
        'hi': "क्या इससे आपकी समस्या हल हो गई?",
        'mr': "याने तुमची समस्या मिटली का?"
    }
}

PROBLEM_SOLVING_OPTIONS = {
    'refund': {
        'en': "\n1. Yes, solved\n2. Need more help\n3. Create support ticket\n\nReply with 1, 2, or 3.",
        'hi': "\n1. हाँ, हल हो गया\n2. और सहायता चाहिए\n3. सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
        'mr': "\n१. होय, मिटली\n२. अधिक मदत हवी आहे\n३. सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या।"
    },
    'catering_complaint': {
        'en': "\n1. Yes\n2. Need more assistance\n3. Create support ticket\n\nReply with 1, 2, or 3.",
        'hi': "\n1. हाँ\n2. और सहायता चाहिए\n3. सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
        'mr': "\n१. होय\n२. अधिक मदत हवी आहे\n३. सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या।"
    },
    'payment_failure': {
        'en': "\n1. Yes\n2. Need more assistance\n3. Create support ticket\n\nReply with 1, 2, or 3.",
        'hi': "\n1. हाँ\n2. और सहायता चाहिए\n3. सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
        'mr': "\n१. होय\n२. अधिक मदत हवी आहे\n३. सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या।"
    },
    'default': {
        'en': "\n1. Yes, problem solved\n2. Need more assistance\n3. Create support ticket\n\nReply with 1, 2, or 3.",
        'hi': "\n1. हाँ, समस्या हल हो गई\n2. और सहायता चाहिए\n3. सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
        'mr': "\n१. होय, समस्या मिटली\n२. अधिक मदत हवी आहे\n३. सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या।"
    }
}


def process_chat_message(session_id, user_message, language='en'):
    # Persist the incoming user message first
    save_chat_message(session_id, 'user', user_message)

    CATEGORY_FRIENDLY_NAMES = {
        'en': {
            'refund': 'refund',
            'payment_failure': 'payment failure',
            'booking_issue': 'booking issue',
            'login_issue': 'login issue',
            'train_delay': 'train delay',
            'cancellation': 'cancellation',
            'luggage_issue': 'luggage issue',
            'catering_complaint': 'catering complaint'
        },
        'hi': {
            'refund': 'रिफंड',
            'payment_failure': 'भुगतान विफलता',
            'booking_issue': 'बुकिंग समस्या',
            'login_issue': 'लॉगिन समस्या',
            'train_delay': 'ट्रेन देरी',
            'cancellation': 'टिकट रद्दीकरण',
            'luggage_issue': 'सामान समस्या',
            'catering_complaint': 'खान-पान (Catering) शिकायत'
        },
        'mr': {
            'refund': 'रिफंड',
            'payment_failure': 'पेमेंट अपयश',
            'booking_issue': 'बुकिंग समस्या',
            'login_issue': 'लॉगिन अडचण',
            'train_delay': 'ट्रेन उशीर',
            'cancellation': 'तिकीट रद्द करणे',
            'luggage_issue': 'सामान अडचण',
            'catering_complaint': 'खान-पान (Catering) तक्रार'
        }
    }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    print("SESSION =", session)
    print("SESSION ID =", session_id)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not session:
        cursor.execute(
            "INSERT OR REPLACE INTO chat_sessions (session_id, category, slots, messages, language, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, None, json.dumps({}), json.dumps([]), language, now_str)
        )
        conn.commit()
        category = None
        slots = {}
    else:
        category = session['category']
        try:
            slots = json.loads(session['slots']) if session['slots'] else {}
        except Exception:
            slots = {}
        language = session['language'] if session['language'] else language
        print("LOADED SLOTS =", slots)

    user_lower = user_message.lower().strip()
    print("USER MESSAGE =", user_lower)

    # 0. Intercept if in multi-state confirmation flow
    yes_matches = ["yes", "y", "confirm", "haan", "हां", "हाँ", "हो", "होय", "यस"]
    no_matches = ["no", "n", "cancel", "na", "nahi", "नहीं", "नाही", "नको", "नो"]
    is_yes = any(ym == user_lower or user_lower.startswith(ym + " ") for ym in yes_matches)
    is_no = any(nm == user_lower or user_lower.startswith(nm + " ") for nm in no_matches)

    # State A: Menu Selection Interceptor
    if category and slots.get('awaiting_initial_menu_selection'):
        is_opt1 = "1" in user_lower or any(word in user_lower for word in ["solved", "handled", "problem solved", "yes", "हाँ", "हो", "यस"])
        is_opt2 = "2" in user_lower or any(word in user_lower for word in ["help", "guidance", "more", "additional", "अतिरिक्त", "मदत", "मार्गदर्शन"])
        is_opt3 = "3" in user_lower or any(word in user_lower for word in ["ticket", "support", "create", "सहायता टिकट", "सपोर्ट", "तयार"])

        if is_opt1:
            reply_text = {
                'en': "Great! I'm glad I could help you. Safe travels!",
                'hi': "बहुत बढ़िया! मुझे खुशी है कि मैं आपकी मदद कर सका। आपकी यात्रा सुरक्षित हो!",
                'mr': "उत्कृष्ट! मला आनंद आहे की मी तुम्हाला मदत करू शकलो. आपला प्रवास सुखकर होवो!"
            }.get(language, "Great! I'm glad I could help you. Safe travels!")
            
            # Log to AI resolved conversations
            cursor.execute(
                "INSERT OR REPLACE INTO ai_resolved_conversations (session_id, category, resolved_at) VALUES (?, ?, ?)",
                (session_id, category, now_str)
            )
            conn.commit()

            cursor.execute("UPDATE chat_sessions SET category = NULL, slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps({}), now_str, session_id))
            conn.commit()
            save_chat_message(session_id, 'assistant', reply_text)
            conn.close()
            return reply_text, None, False, None

        elif is_opt2:
            slots.pop('awaiting_initial_menu_selection', None)
            
            if category == 'emergency':
                reply_text = {
                    'en': "Understood. Please stay calm. Locate the nearest railway police (RPF/GRP) staff in your coach or pull the alarm chain if there is active danger. Helpline: **139** or **112**.",
                    'hi': "समझ गए। कृपया शांत रहें। अपने कोच में निकटतम रेलवे पुलिस (RPF/GRP) स्टाफ को ढूंढें या सक्रिय खतरा होने पर अलार्म चेन खींचें। हेल्पलाइन: **139** या **112**।",
                    'mr': "समजले. कृपया शांत राहा. आपल्या डब्यात जवळच्या रेल्वे सुरक्षा रक्षक (RPF/GRP) कर्मचाऱ्यांशी संपर्क करा किंवा धोका असल्यास अलार्म चेन ओढा. हेल्पलाईन: **139** किंवा **112**."
                }.get(language, "Stay calm. Call 139 or 112.")
                slots['awaiting_initial_menu_selection'] = True
                cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
                conn.commit()
                save_chat_message(session_id, 'assistant', reply_text)
                conn.close()
                return reply_text, category, False, None

            slots['deeper_assistance'] = True
            
            # Check missing slots
            missing_slots = get_missing_slots(category, slots)
            
            if missing_slots:
                prompt_intro = {
                    'en': "To provide deeper assistance, please provide:",
                    'hi': "अतिरिक्त सहायता के लिए कृपया प्रदान करें:",
                    'mr': "अधिक मदत करण्यासाठी कृपया खालील माहिती द्या:"
                }.get(language, "To provide deeper assistance, please provide:")
                bullets = "\n".join([f"• {SLOT_FRIENDLY_NAMES.get(language, SLOT_FRIENDLY_NAMES['en']).get(slot, slot.replace('_', ' ').title())}" for slot in missing_slots])
                reply_text = f"{prompt_intro}\n{bullets}"
                
                cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
                conn.commit()
                save_chat_message(session_id, 'assistant', reply_text)
                conn.close()
                return reply_text, category, False, None
            else:
                # All slots pre-filled: show guidance immediately
                s_guidance = ""
                if category == 'refund':
                    src = slots.get('source_station', 'Unknown')
                    dst = slots.get('destination_station', 'Unknown')
                    pnr = slots.get('pnr', 'Unknown')
                    j_date = slots.get('journey_date', 'Unknown')
                    s_guidance = f"I have analyzed your refund request:\n\nSource: {src}\nDestination: {dst}\nPNR: {pnr}\nJourney Date: {j_date}\n\nPossible reasons:\n* Settlement delay\n* Cancellation verification\n* Payment gateway processing\n\nRecommended checks:\n* Verify cancellation status\n* Check original payment account\n* Confirm whether 7 working days have passed"
                else:
                    s_guidance = STATUS_GUIDANCE.get(category, {}).get(language, STATUS_GUIDANCE.get('refund', {}).get(language, ''))
                
                if category == 'train_delay':
                    src = slots.get('source_station', '')
                    dst = slots.get('destination_station', '')
                    alts = find_alternatives_in_dataset(src, dst)
                    if alts:
                        alt_text = {
                            'en': "\n\nAlternative trains available in local dataset:\n" + "\n".join([f"- {a}" for a in alts]),
                            'hi': "\n\nस्थानीय डेटासेट में उपलब्ध वैकल्पिक ट्रेनें:\n" + "\n".join([f"- {a}" for a in alts]),
                            'mr': "\n\nस्थानिक डेटासेटमधील पर्यायी ट्रेन्स:\n" + "\n".join([f"- {a}" for a in alts])
                        }.get(language, "\n\nAlternative trains available:\n" + "\n".join([f"- {a}" for a in alts]))
                        s_guidance += alt_text
                
                # Was this helpful header and options
                q_text = PROBLEM_SOLVING_QUESTIONS.get(category, PROBLEM_SOLVING_QUESTIONS['default']).get(language, 'Was this helpful?')
                o_text = PROBLEM_SOLVING_OPTIONS.get(category, PROBLEM_SOLVING_OPTIONS['default']).get(language, '1. Yes')
                reply_text = f"{s_guidance}\n\n{q_text}{o_text}"
                
                slots.pop('deeper_assistance', None)
                slots['awaiting_helpfulness_confirmation'] = True
                
                cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
                conn.commit()
                save_chat_message(session_id, 'assistant', reply_text)
                conn.close()
                return reply_text, category, False, None

        elif is_opt3:
            slots.pop('awaiting_initial_menu_selection', None)
            
            if category == 'emergency':
                # Create emergency ticket immediately!
                ticket_id = generate_ticket_id()
                now_ticket = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Default values for emergency
                route = 'Unknown Route'
                train = 'Unknown Train'
                passenger = 'Emergency Passenger'
                email = 'emergency@email.com'
                pnr = None
                priority = 'critical'
                department = 'Security & Emergency'
                desc = user_message or 'Emergency reported'
                ai_suggestion = 'Immediate medical / safety intervention required.'
                
                # Duplicate check just in case
                cursor.execute("SELECT id FROM tickets WHERE passenger = ? AND type = ? AND description = ?", (passenger, category, desc))
                existing = cursor.fetchone()
                if existing:
                    ticket_id = existing['id']
                else:
                    cursor.execute(
                        "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (ticket_id, category, desc, route, train, priority, 'open', passenger, email, pnr, 'Unassigned', now_ticket, None, ai_suggestion, department, None)
                    )
                
                cursor.execute("DELETE FROM ai_resolved_conversations WHERE session_id = ?", (session_id,))
                conn.commit()
                
                reply_text = {
                    'en': "Thank you. Your emergency ticket has been registered successfully.\n\nTicket ID: **{ticket_id}**\nDepartment: **Security & Emergency**\nPriority: **Critical**\n\nOur team has been alerted for immediate action.",
                    'hi': "धन्यवाद। आपकी आपातकालीन शिकायत सफलतापूर्वक दर्ज कर ली गई है।\n\nटिकट आईडी: **{ticket_id}**\nविभाग: **Security & Emergency**\nप्राथमिकता: **Critical**\n\nहमारी टीम को तत्काल कार्रवाई के लिए सतर्क कर दिया गया है।",
                    'mr': "धन्यवाद. तुमची आपत्कालीन तक्रार यशस्वीरित्या नोंदवली गेली आहे.\n\nतिकीट आयडी: **{ticket_id}**\nविभाग: **Security & Emergency**\nप्राधान्य: **Critical**\n\nआमच्या पथकाला त्वरित कारवाईसाठी सतर्क केले गेले आहे."
                }.get(language, "Emergency ticket created.").format(ticket_id=ticket_id)
                
                cursor.execute("UPDATE chat_sessions SET category = NULL, slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps({}), now_str, session_id))
                conn.commit()
                save_chat_message(session_id, 'assistant', reply_text)
                conn.close()
                return reply_text, category, True, ticket_id

            # Check missing slots
            missing_slots = get_missing_slots(category, slots)
                        
            if missing_slots:
                slots['ticket_requested'] = True
                prompt_intro = {
                    'en': "To create a support ticket, please provide:",
                    'hi': "सहायता टिकट बनाने के लिए कृपया प्रदान करें:",
                    'mr': "सपोर्ट तिकीट तयार करण्यासाठी कृपया खालील माहिती द्या:"
                }.get(language, "To create a support ticket, please provide:")
                bullets = "\n".join([f"• {SLOT_FRIENDLY_NAMES.get(language, SLOT_FRIENDLY_NAMES['en']).get(slot, slot.replace('_', ' ').title())}" for slot in missing_slots])
                reply_text = f"{prompt_intro}\n{bullets}"
                
                cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
                conn.commit()
                save_chat_message(session_id, 'assistant', reply_text)
                conn.close()
                return reply_text, category, False, None
            else:
                summary_lines = []
                for slot in REQUIRED_SLOTS.get(category, []):
                    friendly = SUMMARY_SLOT_NAMES.get(language, SUMMARY_SLOT_NAMES['en']).get(slot, slot.replace('_', ' ').title())
                    val = slots.get(slot, 'Not Provided')
                    summary_lines.append(f"{friendly}: {val}")
                summary_text = "\n".join(summary_lines)

                cat_friendly = CATEGORY_FRIENDLY_NAMES.get(language, CATEGORY_FRIENDLY_NAMES['en']).get(category, category.replace('_', ' '))

                if language == 'hi':
                    prompt_text = f"मैंने निम्नलिखित जानकारी एकत्र की है:\n\n{summary_text}\n\nयह एक {cat_friendly} संबंधित समस्या प्रतीत होती है।\n\nक्या आप चाहते हैं कि मैं एक सहायता टिकट बनाऊं? हाँ (YES) या ना (NO) में उत्तर दें।"
                elif language == 'mr':
                    prompt_text = f"मी खालील माहिती गोळा केली आहे:\n\n{summary_text}\n\nही {cat_friendly} संबंधित समस्या असल्याचे दिसते।\n\nतुम्ही मला सपोर्ट तिकीट तयार करण्यास सांगू इच्छिता का? YES किंवा NO मध्ये उत्तर द्या।"
                else:
                    prompt_text = f"I have collected the following information:\n\n{summary_text}\n\nThis appears to be a {cat_friendly}-related issue.\n\nWould you like me to create a support ticket? Reply YES or NO."

                slots['awaiting_ticket_confirmation'] = True
                cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
                conn.commit()
                save_chat_message(session_id, 'assistant', prompt_text)
                conn.close()
                return prompt_text, category, False, None

        else:
            if category == 'emergency':
                prompt_text = {
                    'en': "Please select a valid option:\n1. Problem solved\n2. Need additional guidance\n3. Create emergency ticket\n\nReply with 1, 2, or 3.",
                    'hi': "कृपया एक वैध विकल्प चुनें:\n1. समस्या हल हो गई\n2. अतिरिक्त मार्गदर्शन चाहिए\n3. आपातकालीन सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
                    'mr': "कृपया वैध पर्याय निवडा:\n१. समस्या मिटली\n२. अधिक मार्गदर्शन हवे आहे\n३. आपत्कालीन सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या."
                }.get(language, "Please select a valid option: 1, 2, or 3.")
            else:
                prompt_text = {
                    'en': "Please select a valid option:\n1. Yes, problem solved\n2. Need more help\n3. Create support ticket\n\nReply with 1, 2, or 3.",
                    'hi': "कृपया एक वैध विकल्प चुनें:\n1. हाँ, समस्या हल हो गई\n2. और सहायता चाहिए\n3. सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
                    'mr': "कृपया वैध पर्याय निवडा:\n१. होय, समस्या मिटली\n२. अधिक मदत हवी आहे\n३. सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या."
                }.get(language, "Please select a valid option: 1, 2, or 3.")
                
            save_chat_message(session_id, 'assistant', prompt_text)
            conn.close()
            return prompt_text, category, False, None

    # State B: Helpfulness Confirmation Interceptor
    if category and slots.get('awaiting_helpfulness_confirmation'):
        is_opt1 = "1" in user_lower or any(word in user_lower for word in ["solved", "handled", "problem solved", "yes", "हाँ", "हो", "यस"])
        is_opt2 = "2" in user_lower or any(word in user_lower for word in ["help", "guidance", "more", "additional", "अतिरिक्त", "मदत", "मार्गदर्शन"])
        is_opt3 = "3" in user_lower or any(word in user_lower for word in ["ticket", "support", "create", "सहायता टिकट", "सपोर्ट", "तयार"])

        if is_opt1 or is_yes:
            reply_text = {
                'en': "Great! I'm glad I could help you. Safe travels!",
                'hi': "बहुत बढ़िया! मुझे खुशी है कि मैं आपकी मदद कर सका। आपकी यात्रा सुरक्षित हो!",
                'mr': "उत्कृष्ट! मला आनंद आहे की मी तुम्हाला मदत करू शकलो. आपला प्रवास सुखकर होवो!"
            }.get(language, "Great! I'm glad I could help you. Safe travels!")
            
            # Log to AI resolved conversations
            cursor.execute(
                "INSERT OR REPLACE INTO ai_resolved_conversations (session_id, category, resolved_at) VALUES (?, ?, ?)",
                (session_id, category, now_str)
            )
            conn.commit()

            cursor.execute("UPDATE chat_sessions SET category = NULL, slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps({}), now_str, session_id))
            conn.commit()
            save_chat_message(session_id, 'assistant', reply_text)
            conn.close()
            return reply_text, None, False, None
            
        elif is_opt2:
            prompt_text = {
                'en': "I'm sorry to hear that the suggestions did not fully solve the issue. You can escalate this by creating a support ticket.\n\nWould you like me to create a support ticket? Reply YES or NO.",
                'hi': "मुझे यह सुनकर दुख हुआ कि इन सुझावों से आपकी समस्या हल नहीं हुई। आप सहायता टिकट बनाकर इसे आगे बढ़ा सकते हैं।\n\nक्या आप चाहते हैं कि मैं एक सहायता टिकट बनाऊं? हाँ (YES) या ना (NO) में उत्तर दें।",
                'mr': "तुमची समस्या निवारण झाली नसल्याबद्दल आम्हाला खेद वाटतो. आपण सपोर्ट तिकीट तयार करून हे वाढवू शकता.\n\nतुम्ही मला सपोर्ट तिकीट तयार करण्यास सांगू इच्छिता का? YES किंवा NO मध्ये उत्तर द्या।"
            }.get(language, "Would you like me to create a support ticket? Reply YES or NO.")
            
            slots.pop('awaiting_helpfulness_confirmation', None)
            slots['awaiting_ticket_confirmation'] = True
            
            cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
            conn.commit()
            save_chat_message(session_id, 'assistant', prompt_text)
            conn.close()
            return prompt_text, category, False, None
            
        elif is_opt3 or is_no:
            slots.pop('awaiting_helpfulness_confirmation', None)
            
            summary_lines = []
            for slot in REQUIRED_SLOTS.get(category, []):
                friendly = SUMMARY_SLOT_NAMES.get(language, SUMMARY_SLOT_NAMES['en']).get(slot, slot.replace('_', ' ').title())
                val = slots.get(slot, 'Not Provided')
                summary_lines.append(f"{friendly}: {val}")
            summary_text = "\n".join(summary_lines)

            cat_friendly = CATEGORY_FRIENDLY_NAMES.get(language, CATEGORY_FRIENDLY_NAMES['en']).get(category, category.replace('_', ' '))

            if language == 'hi':
                prompt_text = f"मैंने निम्नलिखित जानकारी एकत्र की है:\n\n{summary_text}\n\nयह एक {cat_friendly} संबंधित समस्या प्रतीत होती है।\n\nक्या आप चाहते हैं कि मैं एक सहायता टिकट बनाऊं? हाँ (YES) या ना (NO) में उत्तर दें।"
            elif language == 'mr':
                prompt_text = f"मी खालील माहिती गोळा केली आहे:\n\n{summary_text}\n\nही {cat_friendly} संबंधित समस्या असल्याचे दिसते।\n\nतुम्ही मला सपोर्ट तिकीट तयार करण्यास सांगू इच्छिता का? YES किंवा NO मध्ये उत्तर द्या।"
            else:
                prompt_text = f"I have collected the following information:\n\n{summary_text}\n\nThis appears to be a {cat_friendly}-related issue.\n\nWould you like me to create a support ticket? Reply YES or NO."

            slots['awaiting_ticket_confirmation'] = True
            cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
            conn.commit()
            save_chat_message(session_id, 'assistant', prompt_text)
            conn.close()
            return prompt_text, category, False, None
            
        else:
            q_text = PROBLEM_SOLVING_QUESTIONS.get(category, PROBLEM_SOLVING_QUESTIONS['default']).get(language, 'Was this helpful?')
            o_text = PROBLEM_SOLVING_OPTIONS.get(category, PROBLEM_SOLVING_OPTIONS['default']).get(language, '1. Yes')
            prompt_text = f"{q_text}{o_text}"
            
            save_chat_message(session_id, 'assistant', prompt_text)
            conn.close()
            return prompt_text, category, False, None

    # State C: Ticket Creation Confirmation Interceptor (previously awaiting_confirmation)
    if category and slots.get('awaiting_ticket_confirmation'):
        if is_yes:
            slots.pop('awaiting_ticket_confirmation', None)
            
            cursor.execute("SELECT content FROM chat_messages WHERE session_id = ? AND role = 'user' ORDER BY id ASC", (session_id,))
            user_msgs = [row['content'] for row in cursor.fetchall()]
            desc = user_message
            for msg in user_msgs:
                msg_lower = msg.lower().strip()
                if len(msg_lower) > 5 and not any(w == msg_lower for w in CASUAL_KEYWORDS) and msg_lower not in yes_matches:
                    desc = msg
                    break

            pred = predict_query(desc)
            sentiment_data = analyze_sentiment(desc)
            sentiment = sentiment_data["sentiment"]
            priority = pred.get('priority', 'medium')

            if sentiment == "negative":
                if priority.lower() == "low":
                    priority = "medium"
            elif priority.lower() == "medium":
                priority = "high"
            
            department = get_mapped_department(category, pred.get('department'))
            cause = pred['cause'].get(language, pred['cause'].get('en')) if isinstance(pred.get('cause'), dict) else ''
            resolution = pred['resolution'].get(language, pred['resolution'].get('en')) if isinstance(pred.get('resolution'), dict) else ''
            ai_suggestion = f"\nPotential Cause: {cause}\n\nRecommended Action: {resolution}\n\nSentiment: {sentiment}\n\nConfidence: {round(pred.get('confidence', 0) * 100, 2)}%\n"
         
            ticket_id = generate_ticket_id()
            now_ticket = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            route = None
            if 'source_station' in slots and 'destination_station' in slots:
                route = f"{slots['source_station']} → {slots['destination_station']}"
            route = route or slots.get('station_name') or 'Unknown Route'

            train = slots.get('train') or slots.get('train_number') or slots.get('train_number_or_name') or 'Unknown Train'
            passenger = slots.get('passenger_name') or slots.get('passenger') or 'Unknown Passenger'
            email = slots.get('email') or 'passenger@email.com'
            pnr = slots.get('pnr')
            if pnr == "Not Available":
                pnr = None

            # Duplicate check to prevent continuous ticket generation in test runs
            is_test = (passenger.startswith("Test") or passenger == "Test Passenger" or "smoke" in session_id.lower() or "test" in session_id.lower())
            if is_test:
                cursor.execute(
                    "SELECT id FROM tickets WHERE passenger = ? AND type = ? AND description = ?",
                    (passenger, category, desc)
                )
                existing = cursor.fetchone()
                if existing:
                    ticket_id = existing['id']
                else:
                    cursor.execute(
                        "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (ticket_id, category, desc, route, train, priority, 'open', passenger, email, pnr, 'Unassigned', now_ticket, None, ai_suggestion, department, None)
                    )
            else:
                cursor.execute(
                    "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticket_id, category, desc, route, train, priority, 'open', passenger, email, pnr, 'Unassigned', now_ticket, None, ai_suggestion, department, None)
                )
            
            # Since ticket was created, remove any AI resolution logs for this session
            cursor.execute("DELETE FROM ai_resolved_conversations WHERE session_id = ?", (session_id,))
            conn.commit()

            TICKET_CONFIRMATION_MSG = {
                'en': "Thank you. Your {cat_name} complaint has been registered successfully.\n\nTicket ID: **{ticket_id}**\n\nDepartment: **{dept}**\nPriority: **{priority}**\n\nOur team will review your request shortly.",
                'hi': "धन्यवाद। आपकी {cat_name} शिकायत सफलतापूर्वक दर्ज कर ली गई है।\n\nटिकट आईडी (Ticket ID): **{ticket_id}**\n\nविभाग (Department): **{dept}**\nप्राथमिकता (Priority): **{priority}**\n\nहमारी टीम जल्द ही आपकी समस्या की समीक्षा करेगी।",
                'mr': "धन्यवाद. तुमची {cat_name} तक्रार यशस्वीरित्या नोंदवली गेली आहे.\n\nतिकीट आयडी (Ticket ID): **{ticket_id}**\n\nविभाग (Department): **{dept}**\nप्राधान्य (Priority): **{priority}**\n\nआमचे पथक लवकरच तुमच्या विनंतीचे पुनरावलोकन करेल."
            }

            cat_friendly = CATEGORY_FRIENDLY_NAMES.get(language, CATEGORY_FRIENDLY_NAMES['en']).get(category, category.replace('_', ' '))

            reply_text = TICKET_CONFIRMATION_MSG.get(language, TICKET_CONFIRMATION_MSG['en']).format(
                cat_name=cat_friendly,
                ticket_id=ticket_id,
                dept=department,
                priority=priority.title()
            )

            save_chat_message(session_id, 'assistant', reply_text)

            cursor.execute(
                "UPDATE chat_sessions SET category = NULL, slots = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps({}), now_str, session_id)
            )
            conn.commit()
            conn.close()

            return reply_text, category, True, ticket_id
            
        elif is_no:
            reply_text = {
                'en': "Ticket creation cancelled. Let me know if you need help with anything else!",
                'hi': "टिकट निर्माण रद्द कर दिया गया है। यदि आपको किसी अन्य चीज़ में सहायता चाहिए तो मुझे बताएं!",
                'mr': "तिकीट तयार करणे रद्द केले आहे. आपल्याला इतर कोणत्याही मदतीची आवश्यकता असल्यास मला सांगा!"
            }.get(language, "Ticket creation cancelled.")
            
            save_chat_message(session_id, 'assistant', reply_text)
            
            cursor.execute(
                "UPDATE chat_sessions SET category = NULL, slots = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps({}), now_str, session_id)
            )
            conn.commit()
            conn.close()
            
            return reply_text, None, False, None
            
        else:
            reply_text = {
                'en': "Please reply YES or NO to confirm ticket creation.",
                'hi': "कृपया टिकट निर्माण की पुष्टि करने के लिए हाँ (YES) या ना (NO) में उत्तर दें।",
                'mr': "कृपया तिकीट तयार करण्याची खात्री करण्यासाठी YES किंवा NO उत्तर द्या."
            }.get(language, "Please reply YES or NO to confirm ticket creation.")
            
            save_chat_message(session_id, 'assistant', reply_text)
            conn.close()
            return reply_text, category, False, None

    # 1. Language switch handling
    if user_lower in ['english', 'hindi', 'marathi', 'मराठी', 'हिंदी', 'मराठित बोला', 'हिंदी में बात करो']:
        if 'marathi' in user_lower or 'मराठी' in user_lower:
            language = 'mr'
            reply = "ठीक आहे, आता आपण मराठीत बोलूया. मी तुमची काय मदत करू?"
        elif 'hindi' in user_lower or 'हिंदी' in user_lower:
            language = 'hi'
            reply = "ठीक है, अब हम हिंदी में बात करेंगे। मैं आपकी क्या मदद कर सकता हूँ?"
        else:
            language = 'en'
            reply = "Sure, let's converse in English. How can I help you?"

        save_chat_message(session_id, 'assistant', reply)
        cursor.execute("UPDATE chat_sessions SET language = ?, updated_at = ? WHERE session_id = ?", (language, now_str, session_id))
        conn.commit()
        conn.close()
        return reply, category, False, None

    # 2. Determine intent
    intent = detect_intent(user_message)
    print("DETECTED INTENT =", intent)

    if intent == "casual":
        reply = get_casual_response(user_message)
        print("CASUAL RESPONSE =", reply)
        save_chat_message(session_id, 'assistant', reply)
        conn.close()
        return reply, None, False, None

    # Handle EMERGENCY intent immediately, bypass normal troubleshooting
    if intent == "emergency" or category == "emergency":
        reply_text = {
            'en': "🚨 **EMERGENCY ASSISTANCE** 🚨\n\n**Emergency Helplines**:\n- Railway Security / Helpline: **139**\n- Emergency Services: **112**\n\n**Emergency Guidance**:\n• Contact the onboard TTE or Train Captain immediately.\n• Pull the emergency alarm chain if there is active danger.\n• Locate the nearest railway police (RPF/GRP) staff.\n\nDid this solve your problem?\n1. Yes, problem solved\n2. Need more assistance\n3. Create support ticket\n\nReply with 1, 2, or 3.",
            'hi': "🚨 **आपातकालीन सहायता** 🚨\n\n**आपातकालीन हेल्पलाइन**:\n- रेलवे पूछताछ/सहायता: **139**\n- आपातकालीन सेवा: **112**\n\n**आपातकालीन मार्गदर्शन**:\n• तुरंत ऑनबोर्ड टीटीई या ट्रेन कैप्टन से संपर्क करें।\n• सक्रिय खतरे के मामले में, ट्रेन को रोकने के लिए आपातकालीन अलार्म चेन खींचें।\n• ट्रेन में निकटतम रेलवे पुलिस (RPF/GRP) स्टाफ को ढूंढें।\n\nक्या इससे आपकी समस्या हल हो गई?\n1. हाँ, समस्या हल हो गई\n2. और सहायता चाहिए\n3. सहायता टिकट बनाएं\n\n1, 2, या 3 के साथ उत्तर दें।",
            'mr': "🚨 **आपत्कालीन मदत** 🚨\n\n**आपत्कालीन हेल्पलाईन**:\n- रेल्वे चौकशी/मदत: **139**\n- आपत्कालीन सेवा: **112**\n\n**आपत्कालीन मार्गदर्शन**:\n१. तात्काळ ऑनबोर्ड टीटीई किंवा ट्रेन कॅप्टनशी संपर्क साधा.\n२. सक्रिय धोका असल्यास, ट्रेन थांबवण्यासाठी आपत्कालीन अलार्म चेन ओढा.\n३. ट्रेनमधील जवळच्या रेल्वे सुरक्षा रक्षक (RPF/GRP) कर्मचाऱ्यांशी संपर्क करा.\n\nयाने तुमची समस्या मिटली का?\n१. होय, समस्या मिटली\n२. अधिक मदत हवी आहे\n३. सपोर्ट तिकीट तयार करा\n\n१, २, किंवा ३ मध्ये उत्तर द्या।"
        }.get(language, "🚨 EMERGENCY ASSISTANCE 🚨\n\nHelpline: 139\nEmergency Services: 112\n\nDid this solve your problem?\n1. Yes, problem solved\n2. Need more assistance\n3. Create support ticket")

        slots = {'awaiting_initial_menu_selection': True}
        cursor.execute("UPDATE chat_sessions SET category = 'emergency', slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
        conn.commit()
        save_chat_message(session_id, 'assistant', reply_text)
        conn.close()
        return reply_text, "emergency", False, None

    # Handle STATUS intent
    if intent == "status":
        pnr_match = re.search(r'\b\d{10}\b', user_message)
        ticket_match = re.search(r'\bTK-\d{4,6}\b', user_message, re.IGNORECASE)
        if ticket_match:
            tk_id = ticket_match.group(0).upper()
            cursor.execute("SELECT status, priority, department, created_at FROM tickets WHERE id = ?", (tk_id,))
            row = cursor.fetchone()
            if row:
                reply = f"Your ticket **{tk_id}** is currently **{row['status'].upper()}**.\nDepartment: **{row['department']}**\nPriority: **{row['priority'].upper()}**\nCreated: {row['created_at']}"
            else:
                reply = f"I couldn't find any ticket with ID **{tk_id}**. Please verify the ticket ID."
        elif pnr_match:
            pnr = pnr_match.group(0)
            cursor.execute("SELECT id, status, department, created_at FROM tickets WHERE pnr = ? ORDER BY created_at DESC LIMIT 1", (pnr,))
            row = cursor.fetchone()
            if row:
                reply = f"Ticket **{row['id']}** associated with PNR **{pnr}** is currently **{row['status'].upper()}**.\nDepartment: **{row['department']}**\nCreated: {row['created_at']}"
            else:
                reply = f"No support ticket found for PNR **{pnr}**. If you are facing an issue, please describe it and I will help you file a ticket."
        else:
            reply = "Please provide your **10-digit PNR number** or **Ticket ID (e.g. TK-1001)** so I can fetch the status for you."
        save_chat_message(session_id, 'assistant', reply)
        conn.close()
        return reply, None, False, None

    # Handle FAQ intent
    if intent == "faq":
        text_lower = user_message.lower()
        if "refund" in text_lower or "cancel" in text_lower:
            reply = "ℹ️ **Refund & Cancellation Policy**:\n\n1. Refunds for online cancelled tickets are credited to the original booking account within **3-5 working days**.\n2. Cancellation charges depend on the ticket status (e.g., Confirmed, RAC, Waitlisted) and when you cancel before departure."
        elif "tatkal" in text_lower:
            reply = "ℹ️ **Tatkal Booking Rules**:\n\n1. Booking opens daily at **10:00 AM** for AC classes and **11:00 AM** for non-AC classes.\n2. No refund is granted for cancellation of confirmed Tatkal tickets, except in specific delay/diversion scenarios."
        elif "status" in text_lower or "track" in text_lower or "running" in text_lower:
            reply = "ℹ️ **Train Tracking**:\n\nYou can view live train statuses, schedules, and delays in the **Train Status** section on the main Dashboard of RailAI."
        else:
            reply = "ℹ️ **Frequently Asked Questions**:\n\nI can help you with rules regarding **Refunds**, **Cancellations**, and **Tatkal Bookings**. Please let me know what you would like to know!"
        save_chat_message(session_id, 'assistant', reply)
        conn.close()
        return reply, None, False, None

    # 3. Predict category if not already active in session
    is_new_category = False
    if not category:
        pred_res = predict_query(user_message)
        category = pred_res['category']
        slots = {}
        is_new_category = True

    # Determine first missing slot from previous session state (for context matching)
    prev_missing_slots = get_missing_slots(category, slots)
    first_prev_missing = prev_missing_slots[0] if prev_missing_slots else None

    # 4. Extract slots from the message
    if category in REQUIRED_SLOTS:
        # Smart pre-extraction for stations and PNR/dates from a combined message
        extracted_pnr = None
        extracted_date = None
        
        # 1. PNR extraction (exactly 10 digits)
        if 'pnr' in REQUIRED_SLOTS[category] and ('pnr' not in slots or not slots['pnr']):
            pnr_matches = re.findall(r'\b\d{10}\b', user_message)
            if pnr_matches:
                extracted_pnr = pnr_matches[0]
                slots['pnr'] = extracted_pnr
                
        # 2. Date extraction (word pattern or relative)
        date_slots = [s for s in REQUIRED_SLOTS[category] if s in ['journey_date', 'booking_date']]
        for ds in date_slots:
            if ds not in slots or not slots[ds]:
                date_pattern = r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b'
                date_match = re.search(date_pattern, user_message)
                if date_match:
                    extracted_date = date_match.group(0)
                    slots[ds] = extracted_date
                    break
                
                word_date_pattern = r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{0,4}\b'
                word_date_match = re.search(word_date_pattern, user_message, re.IGNORECASE)
                if word_date_match:
                    extracted_date = word_date_match.group(0)
                    slots[ds] = extracted_date
                    break
                    
        # 3. Station names extraction (if source or destination is missing)
        station_slots = [s for s in REQUIRED_SLOTS[category] if s in ['source_station', 'destination_station']]
        if station_slots and (not slots.get('source_station') or not slots.get('destination_station')):
            clean_text = user_message
            if extracted_pnr:
                clean_text = clean_text.replace(extracted_pnr, '')
            if extracted_date:
                clean_text = clean_text.replace(extracted_date, '')
                
            ignore_words = {
                "refund", "ticket", "delay", "cancel", "payment", "problem", "issue", "complaint", 
                "received", "failed", "lost", "yes", "no", "ok", "please", "help", "my", "is", "have", 
                "not", "for", "to", "from", "on", "in", "at", "a", "an", "the", "and", "or", "of", "with",
                "express", "rajdhani", "shatabdi", "duronto", "local", "mail", "passenger", "intercity", "garib rath"
            }
            raw_words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_text)
            station_words = []
            for w in raw_words:
                w_lower = w.lower()
                if w_lower not in ignore_words and w_lower not in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "june", "july", "sept", "january", "february", "march", "april", "august", "september", "october", "november", "december"]:
                    if is_valid_entity(w):
                        station_words.append(w.capitalize())
            
            if len(station_words) >= 2:
                if not slots.get('source_station'):
                    slots['source_station'] = station_words[0]
                if not slots.get('destination_station'):
                    slots['destination_station'] = station_words[1]

        # Check if user message is a simple direct answer (short, no structural keywords)
        is_simple_answer = False
        text_clean = user_message.strip()
        text_lower = text_clean.lower()
        words = text_clean.split()
        if len(words) <= 4 and not any(k in text_lower for k in ["from", "to", "pnr", "train", "seat", "coach", "txn"]):
            is_simple_answer = True

        for slot_name in REQUIRED_SLOTS[category]:
            if slot_name not in slots or not slots[slot_name]:
                if is_simple_answer and first_prev_missing and slot_name != first_prev_missing:
                    continue

                is_direct = (slot_name == first_prev_missing)
                val = extract_slot_value(user_message, slot_name, None, category, slots, is_direct_prompt=is_direct)
                if val:
                    slots[slot_name] = val

    print("UPDATED SLOTS =", slots)

    # Save updated session metadata
    cursor.execute("UPDATE chat_sessions SET category = ?, slots = ?, updated_at = ? WHERE session_id = ?", (category, json.dumps(slots), now_str, session_id))
    conn.commit()

    # 5. If is_new_category is True and category is not emergency, show the troubleshooting first flow
    if is_new_category and category != 'emergency':
        raw_causes = CATEGORY_PROBABLE_CAUSES.get(category, {}).get(language, CATEGORY_PROBABLE_CAUSES.get(category, {}).get('en', ''))
        causes_bullets = extract_bullets_only(raw_causes)
        
        raw_actions = TROUBLESHOOTING_STEPS.get(category, {}).get(language, TROUBLESHOOTING_STEPS.get(category, {}).get('en', ''))
        actions_bullets = extract_bullets_only(raw_actions)
        
        header_reasons = PROBLEM_SOLVING_HEADERS['possible_reasons'].get(language, PROBLEM_SOLVING_HEADERS['possible_reasons']['en'])
        header_actions = PROBLEM_SOLVING_HEADERS['suggested_actions'].get(language, PROBLEM_SOLVING_HEADERS['suggested_actions']['en'])
        
        # Determine the question and option set for this category
        q_text = PROBLEM_SOLVING_QUESTIONS.get(category, PROBLEM_SOLVING_QUESTIONS['default']).get(language, 'Did this solve your problem?')
        options_text = PROBLEM_SOLVING_OPTIONS.get(category, PROBLEM_SOLVING_OPTIONS['default']).get(language, '1. Yes')
        
        welcome_intro = CATEGORY_WELCOME_MESSAGES.get(language, CATEGORY_WELCOME_MESSAGES['en']).get(category, "I understand you are facing this issue.")
        
        reply_text = f"{welcome_intro}\n\n{header_reasons}\n{causes_bullets}\n\n{header_actions}\n{actions_bullets}\n\n{q_text}{options_text}"
        
        slots['awaiting_initial_menu_selection'] = True
        cursor.execute("UPDATE chat_sessions SET category = ?, slots = ?, updated_at = ? WHERE session_id = ?", (category, json.dumps(slots), now_str, session_id))
        conn.commit()
        save_chat_message(session_id, 'assistant', reply_text)
        conn.close()
        return reply_text, category, False, None

    # 6. Check all missing slots now
    missing_slots = get_missing_slots(category, slots)

    print("CATEGORY =", category)
    print("SLOTS =", slots)
    print("MISSING SLOTS =", missing_slots)

    # 7. If there are missing slots, prompt for them
    if missing_slots:
        prompt_intro = {
            'en': "Please provide:",
            'hi': "कृपया प्रदान करें:",
            'mr': "कृपया खालील माहिती द्या:"
        }.get(language, "Please provide:")
        
        # Special case for refund as in example
        if category == 'refund' and 'pnr' in missing_slots and 'journey_date' in missing_slots and len(missing_slots) == 2:
            if language == 'en':
                prompt_text = "Please provide your PNR number and journey date."
            elif language == 'hi':
                prompt_text = "कृपया अपना पीएनआर नंबर और यात्रा की तारीख प्रदान करें।"
            else:
                prompt_text = "कृपया आपला पीएनआर नंबर आणि प्रवासाची तारीख द्या."
        elif category == 'refund' and len(missing_slots) == 4:
            prompt_text = "Please provide your source station, destination station, PNR number, and journey date."
        else:
            bullets = "\n".join([f"• {SLOT_FRIENDLY_NAMES.get(language, SLOT_FRIENDLY_NAMES['en']).get(slot, slot.replace('_', ' ').title())}" for slot in missing_slots])
            prompt_text = f"{prompt_intro}\n{bullets}"

        save_chat_message(session_id, 'assistant', prompt_text)
        conn.close()
        return prompt_text, category, False, None

    # 8. All slots filled! Route based on deeper_assistance or ticket_requested flag
    if slots.get('ticket_requested'):
        slots.pop('ticket_requested', None)
        slots.pop('deeper_assistance', None)
        
        summary_lines = []
        for slot in REQUIRED_SLOTS.get(category, []):
            friendly = SUMMARY_SLOT_NAMES.get(language, SUMMARY_SLOT_NAMES['en']).get(slot, slot.replace('_', ' ').title())
            val = slots.get(slot, 'Not Provided')
            summary_lines.append(f"{friendly}: {val}")
        summary_text = "\n".join(summary_lines)

        cat_friendly = CATEGORY_FRIENDLY_NAMES.get(language, CATEGORY_FRIENDLY_NAMES['en']).get(category, category.replace('_', ' '))

        if language == 'hi':
            prompt_text = f"मैंने निम्नलिखित जानकारी एकत्र की है:\n\n{summary_text}\n\nयह एक {cat_friendly} संबंधित समस्या प्रतीत होती है।\n\nक्या आप चाहते हैं कि मैं एक सहायता टिकट बनाऊं? हाँ (YES) या ना (NO) में उत्तर दें।"
        elif language == 'mr':
            prompt_text = f"मी खालील माहिती गोळा केली आहे:\n\n{summary_text}\n\nही {cat_friendly} संबंधित समस्या असल्याचे दिसते।\n\nतुम्ही मला सपोर्ट तिकीट तयार करण्यास सांगू इच्छिता का? YES किंवा NO मध्ये उत्तर द्या।"
        else:
            prompt_text = f"I have collected the following information:\n\n{summary_text}\n\nThis appears to be a {cat_friendly}-related issue.\n\nWould you like me to create a support ticket? Reply YES or NO."

        slots['awaiting_ticket_confirmation'] = True
    elif slots.get('deeper_assistance') or True:
        # We always want to show personalized guidance first before offering ticket escalation
        s_guidance = ""
        if category == 'refund':
            src = slots.get('source_station', 'Unknown')
            dst = slots.get('destination_station', 'Unknown')
            pnr = slots.get('pnr', 'Unknown')
            j_date = slots.get('journey_date', 'Unknown')
            s_guidance = f"I have analyzed your refund request:\n\nSource: {src}\nDestination: {dst}\nPNR: {pnr}\nJourney Date: {j_date}\n\nPossible reasons:\n* Settlement delay\n* Cancellation verification\n* Payment gateway processing\n\nRecommended checks:\n* Verify cancellation status\n* Check original payment account\n* Confirm whether 7 working days have passed"
        else:
            s_guidance = STATUS_GUIDANCE.get(category, {}).get(language, STATUS_GUIDANCE.get('refund', {}).get(language, ''))
            
        if category == 'train_delay':
            src = slots.get('source_station', '')
            dst = slots.get('destination_station', '')
            alts = find_alternatives_in_dataset(src, dst)
            if alts:
                alt_text = {
                    'en': "\n\nAlternative trains available in local dataset:\n" + "\n".join([f"- {a}" for a in alts]),
                    'hi': "\n\nस्थानीय डेटासेट में उपलब्ध वैकल्पिक ट्रेनें:\n" + "\n".join([f"- {a}" for a in alts]),
                    'mr': "\n\nस्थानिक डेटासेटमधील पर्यायी ट्रेन्स:\n" + "\n".join([f"- {a}" for a in alts])
                }.get(language, "\n\nAlternative trains available:\n" + "\n".join([f"- {a}" for a in alts]))
                s_guidance += alt_text
        
        q_text = PROBLEM_SOLVING_QUESTIONS.get(category, PROBLEM_SOLVING_QUESTIONS['default']).get(language, 'Was this helpful?')
        o_text = PROBLEM_SOLVING_OPTIONS.get(category, PROBLEM_SOLVING_OPTIONS['default']).get(language, '1. Yes')
        prompt_text = f"{s_guidance}\n\n{q_text}{o_text}"
        
        slots.pop('deeper_assistance', None)
        slots['awaiting_helpfulness_confirmation'] = True

    cursor.execute("UPDATE chat_sessions SET slots = ?, updated_at = ? WHERE session_id = ?", (json.dumps(slots), now_str, session_id))
    conn.commit()
    conn.close()

    save_chat_message(session_id, 'assistant', prompt_text)
    return prompt_text, category, False, None