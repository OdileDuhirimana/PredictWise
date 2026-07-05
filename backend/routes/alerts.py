from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError
import os

from ..schemas import SendAlertRequest
from ..utils.auth import roles_required
from ..utils.errors import error_response

try:
    from twilio.rest import Client  # type: ignore
    _HAS_TWILIO = True
except Exception:
    _HAS_TWILIO = False

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.post('/send')
@jwt_required()
# Blasting SMS/WhatsApp alerts to parents has real-world cost and
# disruption implications, so only admins may trigger it.
@roles_required('admin')
def send_alert():
    try:
        payload = SendAlertRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid alert details', 400, details=exc.errors())

    channel = payload.channel
    to = payload.to
    message = payload.message

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
        except Exception as exc:
            # The raw exception (e.g. a Twilio auth/config error) previously
            # leaked verbatim to the client via `str(e)` — an
            # information-disclosure risk on an endpoint that already
            # requires no more than "some admin's JWT" to reach. The real
            # detail is logged server-side (and captured by Sentry, if
            # configured) for debugging; the client gets a generic,
            # standard-envelope error instead. This is a genuine failure —
            # unlike the "Twilio not configured at all" branch below, which
            # is an expected/intentional demo-mode state, not an error — so
            # it returns 502 rather than a soft 202 "mocked" success.
            current_app.logger.warning('Twilio alert delivery failed: %s', exc)
            return error_response(
                'alert_delivery_failed',
                'Failed to send the alert through the configured provider.',
                502,
            )

    # Mock sending if Twilio not configured
    return {'status': 'mocked', 'channel': channel, 'to': to, 'message': message}
