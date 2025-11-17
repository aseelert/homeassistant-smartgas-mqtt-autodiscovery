#!/usr/bin/env python3
import argparse
import json
import os
import ssl
import sys
import threading
import time

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

CONNECT_TIMEOUT_SECONDS = 20
STATE_TOPIC = "tele/gaszaehler/json"

# ---- Parse arguments ----
load_dotenv()


def str_to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


env_host = os.getenv("MQTT_HOST")
env_port = os.getenv("MQTT_PORT")
env_user = os.getenv("MQTT_USER")
env_password = os.getenv("MQTT_PASS")
env_ssl = str_to_bool(os.getenv("MQTT_SSL"), False)

parser = argparse.ArgumentParser(description="Publish SmartGas MQTT Discovery to Home Assistant")
parser.add_argument(
    "--host",
    default=env_host,
    required=not bool(env_host),
    help="MQTT broker host (overrides MQTT_HOST env var)"
)
parser.add_argument(
    "--port",
    type=int,
    default=int(env_port) if env_port else 1883,
    help="MQTT broker port (overrides MQTT_PORT env var)"
)
parser.add_argument(
    "--user",
    default=env_user,
    help="MQTT username (overrides MQTT_USER env var)"
)

parser.add_argument(
    "--password",
    default=env_password,
    help="MQTT password (overrides MQTT_PASS env var)"
)
parser.add_argument(
    "--ssl",
    dest="use_ssl",
    action="store_true",
    help="Enable TLS for the MQTT connection (overrides MQTT_SSL env var)"
)
parser.add_argument(
    "--no-ssl",
    dest="use_ssl",
    action="store_false",
    help="Disable TLS even if SSL env var is set"
)
parser.set_defaults(use_ssl=env_ssl)
args = parser.parse_args()


def normalize_reason_code(reason_code) -> int:
    """Return reason code as int, handling Paho ReasonCode objects."""
    try:
        return int(reason_code)
    except (TypeError, ValueError):
        if hasattr(reason_code, "value"):
            try:
                return int(reason_code.value)
            except (TypeError, ValueError):
                pass
        return reason_code


def connack_reason_message(rc_raw) -> str:
    rc = normalize_reason_code(rc_raw)
    reasons = {
        0: "Connection accepted",
        1: "Connection refused: unacceptable protocol version",
        2: "Connection refused: identifier rejected",
        3: "Connection refused: server unavailable",
        4: "Connection refused: bad user name or password",
        5: "Connection refused: not authorized",
        128: "Unspecified error",
        129: "Malformed packet",
        130: "Protocol error",
        131: "Implementation specific error",
        132: "Unsupported protocol version",
        133: "Client identifier not valid",
        134: "Bad user name or password",
        135: "Not authorized",
        136: "Server unavailable",
        137: "Server busy",
        138: "Banned",
        139: "Server shutting down",
        140: "Bad authentication method",
        141: "Keep alive timeout",
        142: "Session taken over",
        143: "Topic filter invalid",
        144: "Topic name invalid",
        145: "Receive maximum exceeded",
        146: "Topic alias invalid",
        147: "Packet too large",
        148: "Message rate too high",
        149: "Quota exceeded",
        150: "Administrative action",
        151: "Payload format invalid",
        152: "Retain not supported",
        153: "QoS not supported",
        154: "Use another server",
        155: "Server moved",
        156: "Shared subscriptions not supported",
        157: "Connection rate exceeded",
    }
    return reasons.get(rc, f"Connection failed with reason code {rc}")


def ensure_connected(client: mqtt.Client) -> None:
    connected = threading.Event()
    connection_result = {"rc": None}

    def handle_connect(_client, _userdata, _flags, reason_code, _properties):
        connection_result["rc"] = reason_code
        connected.set()

    client.on_connect = handle_connect

    try:
        client.connect(args.host, args.port, 60)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Could not reach MQTT broker at {args.host}:{args.port} -> {exc}")
        sys.exit(1)

    client.loop_start()

    if not connected.wait(CONNECT_TIMEOUT_SECONDS):
        print("[ERROR] Timed out waiting for MQTT CONNACK; broker unreachable or not responding.")
        sys.exit(1)

    rc = normalize_reason_code(connection_result["rc"])
    if rc != 0:
        print(f"[ERROR] MQTT broker rejected connection: {connack_reason_message(rc)}")
        if rc in (4, 5):
            print("       Check the username/password configured for the broker.")
        else:
            print("       Verify host, port, TLS settings, and broker availability.")
        sys.exit(1)

    print("[OK] MQTT connection established successfully.")


def mask_password(secret: str | None) -> str:
    if not secret:
        return "(none)"
    if len(secret) == 1:
        return f"{secret[0]}***{secret[0]}"
    return f"{secret[0]}***{secret[-1]}"


def report_connection_target():
    user_display = args.user or "(none)"
    password_display = mask_password(args.password)
    scheme = "mqtts" if args.use_ssl else "mqtt"
    print(
        "[INFO] MQTT target configuration: "
        f"scheme={scheme} host={args.host} port={args.port} user={user_display} password={password_display}"
    )


# ---- MQTT client setup ----
mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
if args.user and args.password:
    mqtt_client.username_pw_set(args.user, args.password)

if args.use_ssl:
    mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
    mqtt_client.tls_insecure_set(True)

report_connection_target()
ensure_connected(mqtt_client)

# ---- Define device info ----
device_info = {
    "identifiers": ["smartnetz_gasreader_5"],
    "name": "Smartnetz Gasreader 5",
    "manufacturer": "Smartnetz",
    "model": "Gasreader 5 (ESP32)",
    "sw_version": "Tasmota 14.5 (Smartnetz)",
    "configuration_url": "https://smartnetz.at/view_details.php?id=106",
}

# ---- Define all sensors for discovery ----
sensors = [
    {
        "name": "Zählerstand",
        "unique_id": "gaszaehler_zaehlerstand",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.gastotal }}',
        "unit_of_measurement": "m³",
        "device_class": "gas",
        "state_class": "total_increasing"
    },
    {
        "name": "Zählung seit Nullung",
        "unique_id": "gaszaehler_zaehlung_seit_nullung",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.value }}',
        "unit_of_measurement": "m³",
        "device_class": "gas",
        "state_class": "total_increasing"
    },
    {
        "name": "Verbrauch Volumen heute",
        "unique_id": "gaszaehler_verbrauch_volumen_heute",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.today_m3 }}',
        "unit_of_measurement": "m³",
        "device_class": "gas",
        "state_class": "total_increasing"
    },
    {
        "name": "Verbrauch Energie heute",
        "unique_id": "gaszaehler_verbrauch_energie_heute",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.today_kwh }}',
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing"
    },
    {
        "name": "Verbrauch Volumen gestern",
        "unique_id": "gaszaehler_verbrauch_volumen_gestern",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.yesterday_m3 }}',
        "unit_of_measurement": "m³",
        "device_class": "gas",
        "state_class": "total_increasing"
    },
    {
        "name": "Verbrauch Energie gestern",
        "unique_id": "gaszaehler_verbrauch_energie_gestern",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.yesterday_kwh }}',
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing"
    },
    {
        "name": "Verbrauch Volumen vorgestern",
        "unique_id": "gaszaehler_verbrauch_volumen_vorgestern",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.db_yesterday_m3 }}',
        "unit_of_measurement": "m³",
        "device_class": "gas",
        "state_class": "total_increasing"
    },
    {
        "name": "Verbrauch Energie vorgestern",
        "unique_id": "gaszaehler_verbrauch_energie_vorgestern",
        "state_topic": STATE_TOPIC,
        "value_template": '{{ value_json.db_yesterday_kwh }}',
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing"
    },
]

# ---- Function to publish discovery for each sensor ----
def publish_discovery():
    for s in sensors:
        payload = s.copy()
        # Add availability for HA
        payload["payload_available"] = "Online"
        payload["payload_not_available"] = "Offline"
        payload["device"] = device_info
        discovery_topic = f"homeassistant/sensor/{s['unique_id']}/config"
        info = mqtt_client.publish(discovery_topic, json.dumps(payload), retain=True)
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[OK] Published discovery for {s['name']} to {discovery_topic}")
        else:
            print(f"[WARN] Failed to publish {s['name']} config (rc={info.rc}).")


# ---- Publish once ----
publish_discovery()
mqtt_client.loop_stop()
mqtt_client.disconnect()
