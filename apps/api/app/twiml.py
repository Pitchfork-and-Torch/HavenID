from __future__ import annotations

from xml.sax.saxutils import escape


def _say(text: str) -> str:
    return f'<Say voice="Polly.Joanna">{escape(text)}</Say>'


def gather(public_url: str, prompt: str = "Press 1 to continue.") -> str:
    action = f"{public_url.rstrip('/')}/voice/gather"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather action="{escape(action)}" method="POST" numDigits="1" timeout="8">'
        f"{_say(prompt)}"
        "</Gather>"
        f"{_say('Goodbye.')}"
        "<Hangup/>"
        "</Response>"
    )


def reject_silent() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>'


def reject_polite(message: str = "This number is not accepting your call. Goodbye.") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response>{_say(message)}<Hangup/></Response>"
    )


def hangup_accept() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response>{_say('Connecting is not available on this trial line. Goodbye.')}<Hangup/></Response>"
    )


def forward(numbers: list[str], simultaneous: bool) -> str:
    inner = "".join(f"<Number>{escape(n)}</Number>" for n in numbers if n)
    timeout = 24 if simultaneous else 18
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Dial timeout="{timeout}">{inner}</Dial></Response>'
    )


def voicemail(public_url: str) -> str:
    action = f"{public_url.rstrip('/')}/voice/recording"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say('Please leave a message after the tone.')}"
        f'<Record action="{escape(action)}" method="POST" maxLength="90" playBeep="true"/>'
        "</Response>"
    )


def record_screen(public_url: str) -> str:
    action = f"{public_url.rstrip('/')}/voice/screen"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say('Please say your name after the tone.')}"
        f'<Record action="{escape(action)}" method="POST" maxLength="6" playBeep="true"/>'
        "</Response>"
    )


def for_decision(action: str, *, public_url: str, forwards: list[str], simultaneous: bool) -> str:
    if action == "reject_silent":
        return reject_silent()
    if action == "reject_polite":
        return reject_polite()
    if action == "challenge":
        return gather(public_url)
    if action == "forward":
        return forward(forwards, simultaneous)
    if action == "voicemail":
        return voicemail(public_url)
    return hangup_accept()
