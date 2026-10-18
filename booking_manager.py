import os
import json
import datetime
import uuid

EVENTS_FILE = os.path.join(os.path.dirname(__file__), "booking_events.json")
DISPUTES_FILE = os.path.join(os.path.dirname(__file__), "booking_disputes.json")

# Allowed Booking States
VALID_STATES = [
    "HOLD",
    "EXPIRED",
    "FUNDED",
    "RELEASED",
    "DISPUTE",
    "CANCELLED_REFUND",
    "CANCELLED_COMPENSATION"
]

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

def record_booking_event(booking_id: str, from_state: str, to_state: str, actor: str, notes: str = ""):
    """Stores every booking state transition with timestamp, actor, and details in booking_events."""
    events = load_json(EVENTS_FILE)
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "booking_id": booking_id,
        "from_state": from_state,
        "to_state": to_state,
        "actor": actor,  # 'tenant' | 'landlord' | 'admin' | 'system'
        "notes": notes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    events.append(event)
    save_json(EVENTS_FILE, events)
    return event

def get_booking_events(booking_id: str):
    events = load_json(EVENTS_FILE)
    return [e for e in events if e.get("booking_id") == booking_id]

def evaluate_cancellation(move_in_date_str: str, cancelled_at: datetime.datetime = None, is_landlord_fault: bool = False) -> dict:
    """
    Evaluates booking cancellation:
    - If landlord fault (fake photos, no key) -> 100% immediate refund to tenant, landlord blocked.
    - If cancelled 72+ hours before move_in_date -> 100% refund to tenant (CANCELLED_REFUND).
    - If cancelled < 72 hours before move_in_date -> hold goes to landlord as compensation (CANCELLED_COMPENSATION).
    """
    if is_landlord_fault:
        return {
            "result_state": "CANCELLED_REFUND",
            "refund_to_tenant": True,
            "compensation_to_landlord": False,
            "reason": "Uy egasi aybi (feyk rasm yoki kalit berilmadi). To'lov to'liq ijarachiga qaytariladi."
        }

    now = cancelled_at or datetime.datetime.now(datetime.timezone.utc)
    try:
        # Parse move_in_date (YYYY-MM-DD)
        move_in = datetime.datetime.strptime(move_in_date_str[:10], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        hours_diff = (move_in - now).total_seconds() / 3600.0

        if hours_diff >= 72.0:
            return {
                "result_state": "CANCELLED_REFUND",
                "refund_to_tenant": True,
                "compensation_to_landlord": False,
                "hours_before_move_in": hours_diff,
                "reason": f"Ko'chishga {round(hours_diff, 1)} soat (72+ soat) qolganda bekor qilindi. To'lov 100% ijarachiga qaytariladi."
            }
        else:
            return {
                "result_state": "CANCELLED_COMPENSATION",
                "refund_to_tenant": False,
                "compensation_to_landlord": True,
                "hours_before_move_in": hours_diff,
                "reason": f"Ko'chishga {round(hours_diff, 1)} soat (72 soatdan kam) qolganda bekor qilindi. Hold to'lovi uy egasiga kompensatsiya sifatida o'tkaziladi."
            }
    except Exception as e:
        return {
            "result_state": "CANCELLED_REFUND",
            "refund_to_tenant": True,
            "compensation_to_landlord": False,
            "reason": f"Sana tahlilida noaniqlik: {e}. Ijarachi foydasiga to'liq qaytariladi."
        }

def record_dispute(booking_id: str, opened_by: str, reason: str, evidence_photos: list = None):
    disputes = load_json(DISPUTES_FILE)
    dispute = {
        "dispute_id": f"disp_{uuid.uuid4().hex[:10]}",
        "booking_id": booking_id,
        "opened_by": opened_by,
        "reason": reason,
        "evidence_photos": evidence_photos or [],
        "status": "under_review",
        "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "deadline_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)).isoformat(),
        "resolution": None
    }
    disputes.append(dispute)
    save_json(DISPUTES_FILE, disputes)
    return dispute

def resolve_dispute(dispute_id: str, decision: str, notes: str = "", admin_actor: str = "admin"):
    """Decision: 'release_landlord' | 'refund_tenant' | 'split'"""
    disputes = load_json(DISPUTES_FILE)
    target = None
    for d in disputes:
        if d.get("dispute_id") == dispute_id:
            d["status"] = "resolved"
            d["resolution"] = {
                "decision": decision,
                "resolved_by": admin_actor,
                "resolved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "notes": notes
            }
            target = d
            break
    save_json(DISPUTES_FILE, disputes)
    return target
