from flask import Blueprint, request
from flask_jwt_extended import jwt_required
import os

try:
    from twilio.rest import Client  # type: ignore
    _HAS_TWILIO = True
except Exception:
    _HAS_TWILIO = False

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.post('/send')
@jwt_required()
def send_alert():
    data = request.get_json() or {}
    channel = (data.get('channel') or 'sms').lower()
    to = data.get('to')
    message = data.get('message') or ''

    # Twilio credentials via env
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    from_sms = os.getenv('TWILIO_FROM_NUMBER')
    from_wa = os.getenv('TWILIO_WHATSAPP_FROM')  # like 'whatsapp:+14155238886'

    if _HAS_TWILIO and sid and token and ((channel == 'sms' and from_sms) or (channel == 'whatsapp' and from_wa)):
        try:
            client = Client(sid, token)
            if channel == 'whatsapp':
                msg = client.messages.create(
                    body=message,
                    from_=from_wa,
                    to=f"whatsapp:{to}" if not str(to).startswith('whatsapp:') else to,
                )
            else:
                msg = client.messages.create(
                    body=message,
                    from_=from_sms,
                    to=to,
                )
            return {'status': 'queued', 'sid': msg.sid, 'channel': channel, 'to': to}
        except Exception as e:
            # Fallback to mock on error
            return {'status': 'mocked', 'channel': channel, 'to': to, 'message': message, 'error': str(e)}, 202

    # Mock sending if Twilio not configured
    return {'status': 'mocked', 'channel': channel, 'to': to, 'message': message}
