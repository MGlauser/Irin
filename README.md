# Uncharted 12V Battery Monitor

ESP32-C3 monitor for the 12V flooded lead-acid (50 Ah) accessory battery of a 2027 Subaru Uncharted GT,
reporting to HomeAssistant over WiFi.

**Purpose: alert when SOC drops below 50%**, in time to **run the car (15-30 min) or plug
it into the 240 V charger** for a scheduled charge; either lets the vehicle's DC-DC top up
the 12V. Everything else is supporting detail.

## Why this exists

The vehicle draws **~430 mA parked** (Subaru's pass threshold is <500 mA), which matches
widely reported owner experience of 12V trouble after a couple of days idle. On the 50 Ah
flooded battery that is roughly **2.4 days from full to 50%**. A 50% alert leaves 1-2 days of margin —
ample for the intended response.

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Design record — rationale, measurements, rejected options |
| `PARTS.md` | Bill of materials, wiring, divider math |
| `esphome/uncharted-battery.yaml` | Device firmware |
| `esphome/secrets.yaml.example` | Credential template |
| `ha_config/automations.yaml` | Core alerts (required) |
| `ha_config/automations_charger_optional.yaml` | External maintainer loop (optional) |
| `ha_config/configuration_snippets.yaml` | Helper sensors, recorder, tuning notes |

## Hardware summary

- **01Space ESP32-C3-0.42LCD** — 72×40 SSD1306 OLED, I2C on GPIO5/6
- **ADS1115** @ 0x48, A0 through a 47k/10k divider (5.7:1)
- **DHT22** on GPIO3, remote-mounted outside the sealed enclosure via 3-pin connector J2 (cable ≤1 m at 3.3 V)
- **MP1584EN** buck at 5.0 V into the board's 5V pin
- 5 A fuse at the battery post; optional P6KE18A TVS
- 3D printed enclosure, PETG or ASA

Always-on, sampling every 30 s. Deep sleep was evaluated and rejected — against 430 mA
of vehicle draw it saves ~1.6 hours out of ~70.

## Build sequence

### 1. Before parts arrive

Flash a bare board with only the `i2c` and `display` blocks.

- **Confirm SDA/SCL order.** Config assumes SDA=GPIO5 / SCL=GPIO6; sources conflict and
  the reverse is possible. `scan: true` should find 0x3C and 0x48.
- **Confirm the 72×40 model renders.** The panel is a centered window into a 128×64
  controller.

These are the two most likely time sinks and neither needs the ADC.

### 2. Bench

- Set the MP1584 output to 5.0 V before it touches the board
- Build the divider; verify no clipping to 16 V
- I2C scan finds both devices
- **Two-point calibration** at ~11.5 V and ~15 V against a good meter → update
  `calibrate_linear`
- Verify ±0.05 V near **12.22 V** (the flooded 50% point)
- Confirm mode switching and hysteresis at the 12.8/12.9 V boundary
- Simulate a DC-DC cycle to verify the rest gate holds SOC and then releases it
- 24 h stability run

### 3. Vehicle

- Direct to battery posts, not a downstream accessory circuit
- Fuse within ~6" of the positive terminal
- DHT22 outside the sealed volume
- Check WiFi RSSI at the mounting location

### 4. HomeAssistant

- Adopt the device; verify entity IDs match the automations
- Add core automations; **leave the DC-DC stall automation disabled** until tuned
- Extend recorder retention for voltage history
- Force a low reading to confirm the 50% alert fires
- Add a push notifier — a persistent notification alone is easy to miss

## Tuning — three values need real data

| Value | Where | How |
|---|---|---|
| `calibrate_linear` | ESPHome | Two-point against a meter |
| DC-DC stall threshold | `automations.yaml` | Observe normal cycle gap, double it |
| Charger float threshold | optional loop | Watch one charge cycle |

## Things that will bite you

- **SOC is only valid at rest.** The DC-DC cycles unpredictably; while it runs, voltage
  reads 14 V+ and a naive lookup reports 100% on a failing battery. SOC is gated behind
  30 min of rest *and* a dV/dt stability test. Raw voltage is never gated.
- **Match the SOC table to the chemistry.** This battery is flooded; AGM rests 0.10-0.15 V
  higher, so an AGM table would read it high and fire the 50% alert late (~35-40% actual).
  Swap the table if the battery is ever replaced with an AGM.
- **Divider ground goes to the ADS1115 GND pin, joined to power ground at one point.**
  A shared ground path puts load-dependent millivolts in series with A0, scaled up 5.7x
  at the battery (found on the bench: 15 mV -> ~86 mV error).
- **Surface charge reads high.** Do not shorten the rest gate to get more frequent
  updates — that biases SOC upward and fires the alert late.
- **Divider ratio is set by the ADS1115's VDD+0.3 = 3.6 V ceiling.** Power it from 3.3 V,
  not 5 V, or the 5.7:1 ratio no longer protects the input.
- **Median filtering can erase short DC-DC pulses.** Window is deliberately 3, not 5.

## Verification the design actually works

Once live, confirm that both remedies (running the car, a scheduled charge) genuinely run
the DC-DC long enough to recover the 12V, and how much SOC each gains. Most EVs run the
converter whenever the HV system is up; some cycle it only intermittently. The voltage
trace answers this in one session, and the scheduled-charge window can be lengthened if
an hour proves insufficient.
