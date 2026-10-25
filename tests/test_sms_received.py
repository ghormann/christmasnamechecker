import json
import time

import pytest

import text_server

VALID = {"DOUG", "MARY"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(text_server.validator, "isValid", lambda s: s in VALID)
    text_server.mqtt.reset_mock()
    with text_server.data_lock:
        text_server.masterData["history"] = []
        text_server.masterData["blocked"] = []
        text_server.masterData["queue"] = []
        text_server.masterData["new_name_estimate"] = {"estimated_seconds": 240, "message": "in about 4 minutes"}
        text_server.masterData["timeinfo"]["displayHours"] = True
    return text_server.app.test_client()


def send_sms(client, body, phone="+15131234567"):
    return client.post("/sms", data={
        "Body": body,
        "From": phone,
        "FromCity": "CINCINNATI",
        "FromState": "OH",
        "FromCountry": "US",
        "FromZip": "45202",
    })


def published_all():
    return [c.args[0] for c in text_server.mqtt.publishSmsReceived.call_args_list]


def published_sms():
    msgs = published_all()
    assert len(msgs) == 1
    return msgs[0]


def test_approved_text_publishes_quote_and_location(client):
    send_sms(client, "Doug")
    sms = published_sms()
    assert sms["result"] == "approved"
    assert sms["name"] == "DOUG"
    assert sms["text"] == "Doug"
    assert sms["from"] == "+15131234567"
    assert sms["quoted_seconds"] == 240
    assert (sms["city"], sms["state"], sms["zip"], sms["country"]) == ("CINCINNATI", "OH", "45202", "US")


def test_one_message_per_name_with_invalid_rejected(client):
    send_sms(client, "Doug, Zxqv and Mary")
    msgs = published_all()
    assert [(m["name"], m["result"]) for m in msgs] == [
        ("DOUG", "approved"), ("MARY", "approved"), ("ZXQV", "rejected"),
    ]
    assert [m["quoted_seconds"] for m in msgs] == [240, 240, None]
    assert len({m["ts"] for m in msgs}) == 1
    assert all(m["text"] == "Doug, Zxqv and Mary" for m in msgs)


def test_approved_text_shares_ts_with_name_message(client):
    send_sms(client, "Doug")
    sms = published_sms()
    name_msg = json.loads(text_server.mqtt.publishName.call_args.args[0])
    assert name_msg["ts"] == sms["ts"]


def test_math_estimate_is_quoted_when_queue_is_long(client):
    with text_server.data_lock:
        text_server.masterData["queue"] = [{}] * 26
    send_sms(client, "Doug")
    assert published_sms()["quoted_seconds"] == 12 * 60


def test_math_estimate_never_quotes_zero_minutes(client):
    with text_server.data_lock:
        text_server.masterData["new_name_estimate"] = {"estimated_seconds": 0, "message": "now"}
    resp = send_sms(client, "Doug")
    assert published_sms()["quoted_seconds"] == 60
    assert b"0 minutes" not in resp.data


def test_outside_display_hours_has_no_quote(client):
    with text_server.data_lock:
        text_server.masterData["timeinfo"]["displayHours"] = False
    send_sms(client, "Doug")
    sms = published_sms()
    assert sms["result"] == "approved"
    assert sms["quoted_seconds"] is None


def test_rejected_text(client):
    send_sms(client, "Zxqv")
    sms = published_sms()
    assert sms["result"] == "rejected"
    assert sms["name"] == "ZXQV"
    assert sms["quoted_seconds"] is None


def test_text_with_no_words_is_still_counted(client):
    send_sms(client, "!!!")
    sms = published_sms()
    assert sms["result"] == "rejected"
    assert sms["name"] is None


def test_sender_over_limit_goes_low(client):
    with text_server.data_lock:
        text_server.masterData["history"] = [
            {"phone": "+15131234567", "valid": True, "nameCnt": 8, "ts": time.time()}
        ]
    send_sms(client, "Doug Zxqv")
    msgs = published_all()
    assert [(m["name"], m["result"]) for m in msgs] == [("DOUG", "low"), ("ZXQV", "rejected")]
    assert all(m["quoted_seconds"] is None for m in msgs)


def test_blocked_sender(client):
    with text_server.data_lock:
        text_server.masterData["blocked"] = [{"phone": "+15131234567", "ts": time.time(), "length": 30}]
    send_sms(client, "Doug Zxqv")
    msgs = published_all()
    assert [(m["name"], m["result"]) for m in msgs] == [("DOUG", "blocked"), ("ZXQV", "blocked")]
    assert all(m["quoted_seconds"] is None for m in msgs)
    text_server.mqtt.publishName.assert_not_called()
