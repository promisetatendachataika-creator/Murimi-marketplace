"""
Sending WhatsApp messages.

Test mode (the default, like the Hub): nothing is sent; the message is printed in the
server window, so you can copy the code. Real sending needs a Meta WhatsApp Business
account; we switch it on later with WHATSAPP_MODE=live in .env (costs money: check first).
"""
import logging

from django.conf import settings

log = logging.getLogger(__name__)


def send_code(phone, code, purpose):
    words = "confirm your number" if purpose == "register" else "reset your password"
    text = f"Murimi Market: your code to {words} is {code}. It works for 10 minutes. Never share it."
    mode = getattr(settings, "WHATSAPP_MODE", "test")
    if mode == "test":
        # Printed so you can see it in the PowerShell window running the server.
        print(f"\n[WhatsApp test mode] To {phone}: {text}\n", flush=True)
        log.info("WhatsApp test mode: code sent to %s", phone)
        return True
    raise NotImplementedError("Live WhatsApp sending isn't set up yet (needs a Meta account).")
