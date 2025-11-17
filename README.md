# Home Assistant SmartGas MQTT Auto-Discovery

This script publishes MQTT discovery configuration for Home Assistant to automatically discover and configure sensors from the **Smartnetz Gasreader 5** device.

## Features

- 🔍 Automatic MQTT discovery for 8 gas meter sensors
- 🏠 Single device with multiple entities in Home Assistant
- 🔐 Supports MQTT authentication and TLS/SSL
- ⚙️ Environment variable configuration
- 📊 Tracks gas consumption (volume and energy) for today, yesterday, and day before yesterday

## Prerequisites

- Python 3.14+ (or Python 3.8+)
- MQTT broker (e.g., Mosquitto, Home Assistant MQTT add-on)
- Smartnetz Gasreader 5 device publishing to MQTT
- Home Assistant with MQTT integration enabled

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd homeassistant-smartgas-mqtt-autodiscovery
   ```

2. Create a virtual environment:
   ```bash
   python3.14 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
MQTT_HOST=192.168.1.100
MQTT_PORT=1883
MQTT_USER=your_username
MQTT_PASS=your_password
MQTT_SSL=false
```

**Environment Variables:**
- `MQTT_HOST` - MQTT broker hostname or IP address (required)
- `MQTT_PORT` - MQTT broker port (default: 1883)
- `MQTT_USER` - MQTT username (optional)
- `MQTT_PASS` - MQTT password (optional)
- `MQTT_SSL` - Enable TLS/SSL (default: false)

### Command Line Arguments

You can override environment variables with command-line arguments:

```bash
python enable_smartgas.py --host 192.168.1.100 --port 1883 --user myuser --password mypass --ssl
```

**Arguments:**
- `--host` - MQTT broker host (overrides `MQTT_HOST`)
- `--port` - MQTT broker port (overrides `MQTT_PORT`)
- `--user` - MQTT username (overrides `MQTT_USER`)
- `--password` - MQTT password (overrides `MQTT_PASS`)
- `--ssl` - Enable TLS (overrides `MQTT_SSL`)
- `--no-ssl` - Disable TLS even if `MQTT_SSL` is set

## Usage

1. Ensure your Smartnetz Gasreader 5 is connected and publishing to MQTT topic `tele/gaszaehler/json`

2. Run the script:
   ```bash
   python enable_smartgas.py
   ```

3. The script will:
   - Connect to your MQTT broker
   - Publish discovery configuration for all 8 sensors
   - Exit after successful publication

4. In Home Assistant:
   - Go to **Settings** → **Devices & Services** → **MQTT**
   - The device "Smartnetz Gasreader 5" should appear with 8 sensor entities

## Discovered Sensors

The script creates the following sensors in Home Assistant:

1. **Zählerstand** - Total gas meter reading (m³)
2. **Zählung seit Nullung** - Reading since reset (m³)
3. **Verbrauch Volumen heute** - Today's volume consumption (m³)
4. **Verbrauch Energie heute** - Today's energy consumption (kWh)
5. **Verbrauch Volumen gestern** - Yesterday's volume consumption (m³)
6. **Verbrauch Energie gestern** - Yesterday's energy consumption (kWh)
7. **Verbrauch Volumen vorgestern** - Day before yesterday's volume consumption (m³)
8. **Verbrauch Energie vorgestern** - Day before yesterday's energy consumption (kWh)

All sensors are grouped under a single device: **Smartnetz Gasreader 5**

## Expected MQTT Topic Format

The script expects your Gasreader 5 to publish JSON data to:
```
tele/gaszaehler/json
```

**Expected JSON format:**
```json
{
  "gastotal": "17970.20",
  "value": "11.80",
  "today_m3": "4.34",
  "today_kwh": "47.04",
  "yesterday_m3": "3.40",
  "yesterday_kwh": "36.85",
  "db_yesterday_m3": "-35.35",
  "db_yesterday_kwh": "-383.13"
}
```

## Troubleshooting

### Connection Issues

- **"Connection refused: bad user name or password"**
  - Verify your `MQTT_USER` and `MQTT_PASS` credentials
  - Check broker ACLs/permissions

- **"Timed out waiting for MQTT CONNACK"**
  - Verify `MQTT_HOST` and `MQTT_PORT` are correct
  - Check firewall/network connectivity
  - Ensure MQTT broker is running

- **"Not authorized" (reason code 135)**
  - Check MQTT broker ACLs
  - Verify user has publish permissions for `homeassistant/#` topics

### Discovery Not Appearing in Home Assistant

- Ensure MQTT integration is enabled in Home Assistant
- Check that discovery topics are published: `homeassistant/sensor/*/config`
- Verify the device is publishing to `tele/gaszaehler/json`
- Check Home Assistant logs for MQTT errors

### SSL/TLS Issues

- If using self-signed certificates, the script accepts them by default
- For production, consider using proper CA-signed certificates

## Device Information

- **Manufacturer:** Smartnetz
- **Model:** Gasreader 5 (ESP32)
- **Software:** Tasmota 14.5 (Smartnetz)
- **Product Page:** https://smartnetz.at/view_details.php?id=106

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
