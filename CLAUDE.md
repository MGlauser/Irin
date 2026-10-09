# Irin — Uncharted 12V Battery Monitor

ESP32-C3 device that monitors the 12V accessory battery of a 2027 Subaru Uncharted GT
and reports to HomeAssistant over WiFi.

## Project name: Irin

**Irin** is the open-source project name (chosen 2026-10-06); the Uncharted install is
its prototype instance. The name is from the Book of Enoch: Aramaic *ʿirin* (עִירִין,
singular *ʿir*), "watchers", literally "the wakeful ones" who do not sleep. It is the
word for the Watchers of 1 Enoch 1–36 (*The Book of the Watchers*, extant in Aramaic in
the Dead Sea Scrolls) and of Daniel 4:13 ("a watcher and a holy one"). Meant in the
sense of the **holy** Watchers who kept their post (1 Enoch 20: Uriel, Raphael, Raguel,
Michael, Saraqael, Gabriel, Remiel), not the fallen ones. It also names the design:
always-on, deep sleep deliberately rejected (see Power budget).

**Naming convention:** project branding (repo, README, KiCad project `hardware/irin.*`,
footprint library `Irin`, `esphome/irin.yaml`) says Irin. The *instance* keeps its
names: ESPHome `device_name: uncharted-batt`, `friendly_name: "Uncharted 12V"`, HA
entity IDs `*.uncharted_12v_*`, secrets `uncharted_*`, HA dashboard "Uncharted". Do not
rename the instance: ESPHome entity unique IDs derive from these names, so a rename
creates new HA entities and orphans the recorded history. On the HA Pi the config is
still `/config/esphome/uncharted-batt.yaml` (same content as `esphome/irin.yaml`).

> **Audience:** the owner is a veteran electronics/manufacturing engineer and Extra Class
> ham. Write at peer level. Do not explain soldering, meter use, or basic circuit theory.
> Document only what requires lookup: board-specific pinouts and quirks, absolute-max
> ratings, EV/DC-DC behavior, battery chemistry curves, ESPHome/HA specifics.

## Requirements

**PRIMARY: alert when SOC drops below 50%.** This is what the project is for. Everything
else is supporting detail.

Remediation is manual and simple: **run the car OR plug in the charger.** Either one
brings the HV system up so the vehicle's own DC-DC tops up the 12V on the
manufacturer's profile:
- **Run the car** (READY mode) for 15-30 min. Subaru's software shuts the car off after
  an idle period the owner cannot change, so one session is time-limited and may restore
  only ~10-20% SOC; repeat if a fresh post-run SOC is still at or below 50%.
- **Plug into the 240 V wall charger** and run a scheduled charge (1-2 h). Not subject to
  the idle cutoff, if the DC-DC runs for the whole charge session (see the empirical
  check below).

**Lead time is the design constraint.** The vehicle's parasitic draw has **not been
measured**; the owner has observed the resting voltage drop ~0.1 V over a day (see Power
budget). If that rate holds, 50% SOC leaves several days to flat. One or two days is
enough to walk out and run the car or plug in, so 50% is the correct trigger. Confirm
the rate from Irin's own data (rested SOC readings over a multi-day sit) before
revisiting the threshold.

Secondary:

1. **Chart raw voltage continuously**, including while the DC-DC runs. Published
   unconditionally, never gated. Diagnostic and confirms remediation is working.
2. **DC-DC stall detection** — a diagnostic on vehicle health, not the primary alert.
3. Absolute voltage precision is not a goal in itself. It matters only insofar as it
   supports the 50% decision (±0.05 V suffices).

**Empirical check once live:** confirm that each remedy actually runs the DC-DC long
enough to meaningfully recover the 12V, and measure the SOC gained per 15-30 min run of
the car versus per scheduled charge. Most EVs run the converter whenever the HV system
is up; some cycle it only intermittently. The voltage trace answers this in one session
each, and the scheduled-charge window can be lengthened if an hour proves insufficient.

Consequence: **voltage and SOC are two independent signals with different rules.**
Voltage is raw and always-on. SOC is derived, gated, and only meaningful at rest.

## Hardware (confirmed)

**Board: 01Space ESP32-C3-0.42LCD** (sold under many SKUs, e.g. EC16911681-3;
also listed as "ESP32-C3 SuperMini 0.42 OLED"). User has 3 of these.

| Item | Detail |
|---|---|
| MCU | ESP32-C3, RISC-V single core @ 160 MHz |
| Flash / SRAM | 4 MB / 400 KB |
| Display | 0.42" OLED, **72x40**, SSD1306, I2C |
| OLED I2C pins | **GPIO5 / GPIO6** — see "Pin gotchas" below |
| Exposed GPIO | 0-10, 20, 21 |
| Safe pins (no boot duty) | GPIO0, GPIO1, GPIO3, GPIO10 |
| Strapping pins — avoid | GPIO2, GPIO8, GPIO9 |
| Extras | WS2812 RGB LED, Qwiic connector, boot pushbutton, ceramic antenna |
| USB | On-chip USB-serial (no external UART bridge) |

### Pin gotchas — read before writing any pin config

1. **ADC1 only.** Only GPIO0-GPIO4 (ADC1) work while WiFi is active. ADC2 returns
   garbage once the radio is up. **Prefer GPIO3 or GPIO4** for the voltage divider
   (GPIO2 is a strapping pin; GPIO0/GPIO1 work but GPIO3 is the cleanest).
2. **OLED SDA/SCL order is unverified.** Sources conflict: the Zephyr board definition
   says SDA=GPIO5 / SCL=GPIO6; working Arduino code for the same board says the
   reverse. The *pair* {5, 6} is confirmed. **Run an I2C scan first** and expect the
   SSD1306 at 0x3C.
   Note: espboards.dev claims GPIO8/GPIO9 — believed incorrect for this variant.
3. **72x40 display needs manual offsets.** The SSD1306 controller is natively 128x64;
   the panel is a centered 72x40 window. U8g2 has no 72x40 constructor. Use the
   128x64 constructor with **x offset = 30, y offset = 12**. Without this the screen
   stays blank or shows garbage.
4. **Disable the WS2812 RGB LED.** Pure parasitic draw in a battery-powered application.

## Measurement chain

**ADS1115** (16-bit I2C ADC) is recommended, though no longer strictly required.

Since 50% SOC is the only decision point, the accuracy target is **+/-0.05 V** (the
SOC table steps 12.06 / 12.20 / 12.32 across 40/50/60%). That is loose enough that the
C3's internal ADC could work with heavy averaging and a multi-point calibration curve.

**Decided: use the ADS1115.** User already owns HiLetgo ADS1115 modules (3-pack,
ASIN B07VPFLSMX), so it is free. It shares the OLED's I2C bus at **0x48** (OLED is
0x3C) and needs no extra GPIO.

Wiring: HiLetgo module has no Qwiic connector — cable from the ESP32's Qwiic port to
its through-holes. **ADDR to GND** (0x48). **VDD at 3.3 V**, which sets the VDD+0.3
input ceiling the divider ratio is sized against. See PARTS.md.

### Power supply

**MP1584EN buck module set to 5.0 V, into the board's 5V pin.** Ordered (5-pack).

Rationale: always-on dissipation, not efficiency — against the vehicle's own draw
(~0.1 V/day observed, on the order of 200 mA; see Power budget) the regulator's own
consumption is irrelevant, so the choice is driven by heat in a sealed
enclosure and by keeping the board's onboard protection and USB flashing intact.

Rejected: back-feeding 3V3 (bypasses onboard protection, blocks USB coexistence, buys
nothing here); LM2596 modules (5-10 mA Iq, and hotter).

### Input protection

```
Battery+ --[5A fuse]--+--[divider tap]--> ADS1115 A0
                      |
                      +--[TVS 18V]--+   (standard)
                      |             |
                      +-------------+--> MP1584 --> 5 V
                                    |
Battery- ----------------------------+--> GND
```

- **Fuse protects the 18 GA harness against a chassis short**, not the 150 mA load.
  5 A is correct for 18 GA; Micro2 blade fuses are scarce below 5 A regardless.
- **TVS, P6KE18A** (unidirectional) — standard, fitted on every board (2026-10-08). The "18" is the nominal breakdown, not
  the standoff: VRWM 15.3 V, VBR 17.1-18.9 V, Vc 25.2 V at 24 A. Stays off through
  14.4 V charging and the 16 V design max (below VBR min), clamps below the MP1584's
  30 V abs max. Load dump is not a factor on an EV, but inductive switching is.
  **Orientation:** banded end (cathode, square pad on the DO-15 footprint) to 12vPROT,
  anode to GND, i.e. reverse-biased in normal service. Fitted backwards it is a forward
  diode across the supply and blows F1.
- **100 uF electrolytic + 0.1 uF ceramic** at the buck input

**Reverse polarity: no series diode; D1 is the crowbar** (decided 2026-10-08, once kits
for other builders came up; was "deliberately omitted, owner-built and wired once"). A
reversed hookup forward-biases D1 across the input and blows F1, holding the board near
-1 V while it does. No series diode drop, so the divider tap needs no correction and the
front end stays fuse, TVS and divider. It only works with the fuse upstream (it is, in
the harness). After a reversal, replace the fuse and check D1: its 100 A forward surge
rating should survive a 5 A Micro2 clearing, but that is not guaranteed.

### Voltage divider

Design for **16 V max input** — the DC-DC runs ~14.0-14.5 V and transients go higher.
Do not let the divider clip in the charging range; clipped charging data defeats
requirement #1.

**CRITICAL — ADS1115 input limit.** Powered from the Qwiic bus at 3.3 V, the ADS1115's
absolute maximum analog input is **VDD + 0.3 V = 3.6 V**. A 4:1 divider would present
4.0 V at 16 V (and 3.6 V at normal 14.4 V charging) — exceeding the rating and risking
damage. The ratio must be at least ~5.5:1.

- Ratio **5.7:1**: **R1 = 47k, R2 = 10k** (as built, measured 46.5k / 9.85k = 5.721:1).
  Originally 470k/100k; dropped 10x on 2026-10-05 for lower source impedance (~8.1 kohm
  vs ~82 kohm): less ADS1115 input-impedance error and noise pickup, at ~220 uA divider
  current, which is negligible against the vehicle's own draw. The ratio, and therefore
  the levels and headroom, is unchanged.
- Resulting levels: 12.22 V -> 2.14 V | 14.4 V -> 2.52 V | 16 V -> **2.80 V** (safe)
- Headroom: tolerates ~20.6 V before reaching the 3.6 V limit
- **PGA gain 1** (FSR +/-4.096 V) -> 125 uV/bit = **0.71 mV at the battery**. Far finer
  than the +/-0.05 V requirement.
- **Cap across R2: as built, 2 x 1000 pF mica in parallel (2 nF)**, chosen for low leakage
  (replaced the original 0.1 uF). With the ~8.1 kohm Thevenin source the corner is
  ~10 kHz; the ADS1115 digital filter and the ESPHome median do the real smoothing
- **1% metal film is sufficient.** Calibration cancels initial tolerance entirely; what
  matters is tempco. Use the same series for both resistors so their tempco largely
  cancels in the ratio. 0.1% is not required.
- **Analog ground: R2/C1 return to the ADS1115 GND pin**, and that node meets power
  ground at exactly one point. Found on the bench 2026-10-06: with the divider on one
  ground rail and the ADS1115 on the other, ~15 mV of load-dependent rail-to-rail drop
  sat in series with A0, which is ~86 mV at the battery after the 5.7:1 scale-up. It
  drifted overnight by ~30 mV at the battery, and calibration had absorbed part of it as a
  fake ~0.6% "gain error". The rule is for wired builds (breadboard, perfboard), where
  ground conductors have tens of mohm or more. On the PCB, R2/C1 ground goes straight
  to the solid B.Cu GND plane (decided 2026-10-08): at ~0.5 mohm/square, with the
  divider corner away from the buck and ESP32 return currents, the offset is microvolts,
  so a separate analog return buys nothing.
- The ADS1115's ~6.4 Mohm input impedance adds ~0.13% gain error at this source
  impedance (was ~1.3% at 470k/100k); **calibration absorbs it**, so calibrate rather
  than recompute

## Sampling strategy — adaptive, keyed on voltage

Charting DC-DC cycles conflicts with aggressive deep sleep: those cycles can last only
a few minutes, so a 15-minute sample interval **aliases** and would misrepresent how
often the converter actually runs.

Resolve it by switching modes on the measured voltage itself:

| Condition | Mode | Interval | Rationale |
|---|---|---|---|
| **> 12.9 V** (DC-DC active) | Stay awake | 15-30 s | Converter is actively charging — the power cost of monitoring is irrelevant here |
| **< 12.9 V** (resting) | Sleep / back off | 5-15 min | The only regime where the device's own draw matters |

The expensive mode is exactly the mode in which expense is free. High-resolution
charging curves and a low resting footprint fall out of one rule.

Note the hysteresis requirement: use a deadband (e.g. enter fast mode above 12.9 V,
exit below 12.8 V) so the device does not oscillate between modes at the boundary.

## SOC estimation

### Critical: this vehicle is an EV

The Uncharted has **no alternator**. The 12V battery is charged by a DC-DC converter
off the traction pack, and that converter cycles on and off unpredictably **even while
parked**.

**Voltage-based SOC is only valid at rest.** While the DC-DC runs you will read 14 V+,
and a naive lookup reports 100% on a battery that may be failing.

**Required gating logic (applies to SOC only — never to raw voltage):**
- Only recompute SOC after voltage has stayed **below 12.9 V for 30+ minutes**
- **Additionally require voltage stability: dV/dt < ~1 mV/min over 15 min.** Elapsed
  time alone is not a reliable rest indicator (see surface charge below).
- Otherwise hold and report the last valid resting SOC, plus a staleness timestamp
- The sub-50% alert triggers on the gated SOC value, never the instantaneous one
- **Raw voltage continues publishing throughout** — the gate suppresses SOC updates,
  not telemetry

Without this gate the low-battery alert will likely never fire when it matters.

### Surface charge — why the gate must not be shortened

If the DC-DC cycles every few hours while parked (cycle period not yet observed), clean
rest windows may be **rare** and SOC will often be stale. That is acceptable; staleness is
reported via timestamp.

Do **not** shorten the gate to force more frequent updates. Lead-acid surface charge takes
1-4 hours to dissipate and reads **high** — inflating SOC and firing the alert **late**,
the one direction that costs the battery. Prefer the dV/dt stability test over a
shorter timer.

Note the parasitic load itself does not distort readings: even 500 mA on a 50 Ah battery
is C/100, causing a few mV of sag. Negligible.

### Resting voltage -> SOC — **flooded lead-acid (Pb), 50 Ah**

Battery: **flooded lead-acid, 12 V, 50 Ah** (stock; confirmed 2026-10-05, NOT AGM as
originally assumed). Use the flooded table below, as implemented in the firmware.

| Voltage (25 degC, rested) | SOC |
|---|---|
| 12.70 | 100% |
| 12.58 | 90% |
| 12.48 | 80% |
| 12.38 | 70% |
| 12.30 | 60% |
| **12.22** | **50%  <- alert threshold** |
| 12.12 | 40% |
| 12.02 | 30% |
| 11.90 | 20% |
| 11.75 | 10% |
| 11.60 | 0% |

**Why the chemistry matters:** AGM rests ~0.10-0.15 V higher than flooded. An AGM table on
this flooded battery would read it high and fire the 50% alert late (at roughly 35-40%
actual SOC), the direction that damages the battery. If the battery is ever replaced
with an AGM, swap the table.

**50% is the correct threshold** — lead-acid cycle life degrades sharply below 50% depth
of discharge, and a flooded battery left partially discharged sulfates. The alert point
is chemistry-driven, not arbitrary.

Published tables vary by ~0.05 V between manufacturers. If a spec sheet for the actual
battery is available, prefer its numbers.

### Temperature compensation

Flooded lead-acid open-circuit voltage drifts about **-0.7 mV/degC per cell, ~-0.004 V/degC
for the 12 V battery** (`temp_coeff: 0.004` in the firmware). This is NOT the 3-5
mV/degC/cell charger setpoint compensation, which would over-correct cold readings and
suppress the 50% alert in winter. Across -20 degC to +40 degC the drift is ~0.24 V, more
than the AGM-vs-flooded offset, so it is not negligible.

Effect, uncorrected: a cold battery reads low and reports well below true SOC. That errs
safe, but produces false alerts in winter — exactly when the user is most likely to
distrust and then ignore the alerting. **Implemented:** the firmware corrects to 25 degC
before the lookup.

**Priority: low.** This is second-order, and it backs up the SOC alert, which itself
backs up the DC-DC-stall alert. The bias errs safe (reads low when cold). Skipping it
is defensible.

**Decided: DHT22 / AM2302 on GPIO3** (2-pack ordered). Measures air, so it tracks the
seasonal term but lags the battery's thermal mass on diurnal swings. Acceptable given
the low priority.

**Decided (2026-10-05): sensor REMOTE, outside the enclosure** on a 3-wire cable to
board connector **J2** (JST-XH 3-pin: 1=VCC 2=DATA 3=GND), entering through a cable
gland. Supersedes the earlier inside-the-enclosure decision: remoting removes the
~5-15 degC self-heating offset from the buck + ESP32 while keeping the box sealed.
The data pull-up is on the sensor module.

**For now (2026-10-08): sensor INSIDE the first PCB enclosure**, plugged into J2 and
hot-glued to the box wall, so the box needs only one cable entry (the 12 V leads).
Accepted trade-off: the board dissipates ~0.12 W, so the sensor reads a few degC
above ambient (check it against a thermometer once installed). The error errs safe: reading
warm under-corrects a cold battery, so SOC reads low and the alert fires early. J2 and
the remote option stay on the board; going remote later is a cable and a gland.

**Cable-length limit:** at 3.3 V supply the AM2302 datasheet limits the cable to
**~1 m** (line drop). Longer runs need the sensor on 5 V, which then puts the data
line's pull-up and the ESP32's 3.3 V-only GPIO in conflict. Keep the run under 1 m.

`update_interval: 300s`. Occasional NaN from WiFi interrupt jitter is expected and
harmless at this timescale.

DHT11 was rejected — its 0-50 degC range excludes exactly the conditions the correction
exists for. Accuracy was never the constraint (±2 degC suffices); range was.

Correct to 25 degC before the SOC lookup.

## Power budget — 50 Ah flooded

**Vehicle parasitic draw: NOT measured.** An earlier "~430 mA" figure in these docs was
never measured on this car and has been removed (2026-10-08); do not reintroduce it or
anything derived from it. (Subaru's pass threshold is reportedly <500 mA.)

**Observed: resting voltage dropped ~0.1 V over one day** (owner, car parked and off).
On the flooded table near full, 0.1 V is ~8-10% SOC, i.e. roughly 4-5 Ah/day, or on the
order of 200 mA averaged. That is an estimate from two voltage readings, not a current
measurement, and surface charge can skew it. Irin will measure it properly: the decline
in gated SOC between rested readings over a multi-day sit. A clamp meter on the negative
lead with the car asleep is the direct check.

Usable capacity before the alert: **25 Ah** (100% -> 50%). At ~10%/day that is
roughly **5 days to 50%** (estimate, from the observed rate).

The monitor's share is small whatever the car's draw turns out to be: 10 mA always-on
is 0.24 Ah/day, ~1% of the usable 25 Ah per day, and ~5% of the estimated ~4.8 Ah/day
vehicle loss. Deep sleep (0.5 mA) would save ~0.23 Ah/day.

**Measured on the bench (2026-10-05):** ~10 mA average at 12 V input with WiFi connected,
OLED lit and ESPHome default WiFi light power-save; brief excursions to ~21 mA during
WiFi transmit. Matches the 10 mA always-on assumption above.

**Away from home WiFi (measured 2026-10-06): ~40 mA at 12 V, stable**, with the fallback
AP up and the STA retrying (bench test: wrong WiFi password, phone joined to the AP).
The AP cannot power-save. Cost: on a long sit away from home (e.g. a week at an
airport) the extra 30 mA is 0.72 Ah/day, ~3% of the usable 25 Ah per day; at the
estimated ~10%/day vehicle loss that is a few hours less lead time out of ~5 days. Day trips cost ~0.25 Ah extra and the drive home recharges it. Long sits in
the home garage are on WiFi at ~10 mA. The AP is the WiFi-password rescue.

### Verdict: run always-on. Do not implement deep sleep.

The difference between deep sleep and always-on is ~0.23 Ah/day, about 1% of the
usable capacity per day and a small fraction of the vehicle's own loss — irrelevant. **Dropped as unnecessary:** deep sleep, TPL5110, static-IP/BSSID wake
optimization, WiFi connect timeouts for power reasons, and the *power* rationale for
adaptive sampling.

Keep adaptive sampling only if desired for chart resolution. Otherwise sample every
30 s continuously. The OLED blanks 2 min after boot, a BOOT-button press or the end of a
charge, to limit burn-in of the static layout (saves ~0.5 mA as a side effect).

### The drain rate is still an open measurement

The observed ~0.1 V/day suggests ~5 days from full to 50%. **Widely reported owner
experience is that these vehicles develop 12V problems after sitting a few days**, so
the failure mode is real even though this car's rate is not yet pinned down.

**This sets the alert's lead time.** The device is an early-warning system for a known
failure mode with a fuse of a few days. A 50% SOC alert leaves time to run the car or
plug it in — which is exactly the required response, so the SOC alert is sufficient on
its own and remains primary. Replace the estimates here with measured numbers once Irin
has logged a multi-day sit.

DC-DC stall detection is retained as a *diagnostic*: it distinguishes "owner hasn't run
or plugged in the car" from "the vehicle's converter has stopped working." Useful for a warranty
conversation, not needed for the day-to-day alert. Its threshold can be set loosely
after the first week of data.

## HomeAssistant integration

Entities to expose:

| Entity | Type | Notes |
|---|---|---|
| Battery voltage | sensor (V) | **Always published**, ungated. Primary charting signal. |
| Battery SOC | sensor (%) | Gated to resting state; holds last valid value |
| SOC last-updated | timestamp | Staleness indicator for the gated SOC |
| Charging | binary_sensor | Voltage > 12.9 V (off < 12.8 V). On this car, the DC-DC running — a free "contactors closed" signal. Named generically (was "DC-DC Active", renamed 2026-10-06) so the config reuses for any charge source |
| Time Since Charging | sensor (h) | Hours since Charging was last on; the DC-DC-stall diagnostic |
| Away report | 7 sensors + text summary | Built 2026-10-06. While HA is unreachable (car away from home WiFi, HA down) the device tracks duration, min voltage, min gated SOC, time below `soc_alert_pct`, charging time and events; published on reconnect if the gap was >= `away_min_sec` (30 min). In-progress counters live in restored globals folded from RAM every 5 min (flash wear; a reboot mid-trip loses at most 5 min). Note: with the fallback `ap:` configured, ESPHome never does the no-WiFi reboot, so the device runs uninterrupted while away; the last report is a separate restored set so a short gap can't wipe it. HA's recorder can't be backfilled from ESPHome, so this is a summary, not history (options B/C, statistics import or InfluxDB, deferred). Cannot alert while away. |
| Status page | `web_server` v3, page script served from flash (`js_include`) | Added 2026-10-06 for in-car checks: the device is strapped to the battery in a closed box, so the OLED/BOOT button are out of reach. Join fallback AP `irin-Sunny`, open http://192.168.4.1 (user `irin`, fallback password). Works because web_server registers its handler at setup, before the captive portal's handler (added when the AP starts), so it wins `/`; the portal still serves every other GET (OS login probes, /wifi; it has no real /wifi route, any unclaimed path gets the setup page). The portal is active only while the AP is up, so on the LAN /wifi just shows the status page (seen 2026-10-06). **WiFi Setup link** (2026-10-06): `local: true` serves a fixed page and ignores js_include, so instead `js_include: irin_www.js` + `js_url: ""` serves ESPHome's stock v3 script (extracted from the installed package by `esphome/www/build_www.py`) with `www/wifi_link.js` appended. The link shows only when `/config.json` answers with `aps`, i.e. the portal is up (on the LAN, unclaimed paths get an empty reply). Must match the ESPHome version that builds the firmware (2026.9.1 at creation); regenerate after upgrades and copy irin_www.js to the Pi next to the YAML. irin_www.js is gitignored (mostly ESPHome frontend code, license unclear: ESPHome is MIT except GPLv3 for .h/.cpp, and it ships inside a .h). ~47 KB flash. |
| WiFi RSSI | sensor | Diagnostic — signal strength from inside the vehicle |
| Last seen | timestamp | Detects a dead or out-of-range device |

### Remediation

**Primary — manual, no hardware.** On a 50% alert, **run the car (15-30 min, limited by
Subaru's idle auto-shutoff) OR plug into the 240 V wall charger** and run a scheduled
charge (1-2 h). Either way the vehicle's own DC-DC tops up the 12V on the manufacturer's
profile. Nothing to build, nothing to fail. If a fresh post-remedy SOC is still at or
below 50%, repeat.

### OPTIONAL — automated external 12V maintainer

Everything below is a **backup path** for stretches when nobody can run or plug in the
car for weeks (e.g. the owner is away). Not required for the primary use case; do not build it
before the alert itself is proven working.

HA-switched 110 V AC plug feeding a smart battery maintainer clamped to the 12V.

**Control loop terminates on charger power draw, not SOC.** While charging, voltage
sits at ~14 V, no rest window accumulates, and gated SOC never updates — a SOC-based
loop would latch on permanently. A power-monitoring plug gives a directly observable
"reached float" signal instead.

- **Start:** gated SOC < 70% — preventive, above the 50% damage threshold
- **Stop:** plug power < ~15 W for 30 min (charger in float)
- **Backstop:** hard 24 h maximum on-time

**Charger: NOCO 3.5 A, in its standard 12V (flooded) mode** (on hand). No purchase needed — the $140 Subaru
unit offers nothing extra for terminal charging.

Backup: Harley-Davidson 3.5 A. **Measured float ~13.2 V** — it is a true maintainer
despite the branding, and safe left connected. 13.2 V is an appropriate float for a
flooded battery (it was only marginal under the earlier AGM assumption), so it is a
fully usable alternative. Worth having given the automation depends on one charger
staying alive.

**Safety requirement — the charger must be safe left on indefinitely.** This
automation will eventually fail with the plug on (HA restart, upgrade, disabled
automation). The safe state must be "charger on forever does no harm."

**MUST TEST — power-cycle mode recovery.** NOCO behavior is model-dependent. Set 12V
(flooded) mode, start charging, pull the cord, reapply power, and observe with no button press:

| Result | Verdict |
|---|---|
| Resumes in 12V (flooded) | Use as designed |
| Resumes in another mode (e.g. AGM) | Check its voltages suit flooded before relying on it |
| Sits in standby | Switched-plug control unusable with this unit |

If it fails: do NOT simply leave the charger on permanently. A continuously floated
battery sits at charging voltage forever, making **SOC unmeasurable and DC-DC stall
detection masked** — a healthy battery with zero visibility into whether the vehicle
is faulty. Instead, switch the plug on a *schedule* (e.g. off 2 h each morning) to
create a daily observation window.

Switching the charger is what makes the battery observable, not merely maintained.

**Charge time:** 3.5 A into 50 Ah is C/14 — gentle and appropriate for flooded. From 50%
(~25 Ah) expect **8-10 h** with absorption taper. The 24 h backstop suits this; an
8 h timeout would truncate a full charge.

**Two thresholds, two purposes:** 70% triggers remediation; 50% remains an *alert*
meaning the remediation is not keeping up.

**Watch the intervention rate.** Automated charging masks the underlying vehicle
defect. Occasional activation is normal storage behavior; frequent activation means
the car needs service — track and alert on frequency while under warranty.

**Interaction handled:** `ext_charger_on` (imported from HA) suppresses DC-DC
detection while the maintainer runs. Without it, external charging would reset the
DC-DC idle timer and mask a genuine converter stall.

### Alerting

1. **DC-DC has not run in N hours** (primary, *leading* indicator). With only a few days
   of margin, waiting for SOC to cross 50% is a lagging signal. If the converter
   stops cycling, that is the actual failure and it is visible hours earlier. Implement
   as a threshold on the `Time Since Charging` sensor. Set N from the observed cycle
   period once real data exists.
2. **Gated SOC < 50%** (secondary), with a `for:` duration to suppress transients.
3. **Device unavailable** — so a silent failure is distinguishable from a healthy
   battery.
- Long-term statistics on voltage for battery-health trending
- If MQTT: topics under `subaru_uncharted/battery/...`, use MQTT discovery.
  If ESPHome: native API, no broker required.

## Open decisions

1. **Firmware framework** — ESPHome (YAML, native HA integration, no MQTT broker,
   built-in ADS1115 / SSD1306 components, OTA) vs. Arduino + PlatformIO with MQTT vs.
   ESP-IDF. ESPHome is recommended; the only custom logic needed is the resting gate
   and the SOC lookup, both of which map onto lambdas / `calibrate_linear`.
2. **DC-DC-stall alert threshold** — cannot be set until the normal cycle period is
   observed. Expect to set it after the first week of data.
3. **Battery location** — under-hood vs. rear. Drives WiFi margin.

**Resolved:**
- Battery: flooded lead-acid (Pb), 50 Ah (confirmed 2026-10-05; was assumed AGM 60 Ah)
- Remediation: run the car (15-30 min) OR plug in and run a scheduled charge
- Power: MP1584EN buck to 5 V, always-on, no deep sleep
- ADC: ADS1115 at 0x48 on the OLED I2C bus, 47k/10k divider (was 470k/100k)
- Temp: DHT22 on GPIO3 via J2 (3-pin); inside the box for now (2026-10-08), remote option kept, cable ≤1 m
- Enclosure: 3D printed, PETG or ASA (both on hand)

## PCB mechanical (for the enclosure model)

The enclosure is printed to fit the board, not the other way round. Values from
`hardware/irin.kicad_pcb` as of 2026-10-08; re-check them if the outline or holes move.

| Item | Value |
|---|---|
| Board outline | **78.5 x 69.0 mm** (KiCad Edge.Cuts rectangle (9.5, 16.5) to (88.0, 85.5)) |
| Mounting holes | 4x M3, **3.2 mm** drill, no plating/pad (MountingHole_3.2mm_M3) |
| Hole inset | **3.5 mm** from the edge on both axes, all four corners |
| Hole spacing (centre to centre) | **71.5 x 62.0 mm** |
| Hole centres from the board's lower-left corner | (3.5, 3.5), (75.0, 3.5), (3.5, 65.5), (75.0, 65.5) |

The pattern is symmetric, so KiCad's Y-down versus OpenSCAD's Y-up does not matter.
**No USB cutout** (owner decision, 2026-10-08): the box stays sealed; firmware goes
in by OTA, or with the lid off. Rev B keeps the ~19 mm of clear board below U2's USB
end (USB-C at U2's bottom end, confirmed by the owner 2026-10-08; the ceramic antenna is
at the opposite end, toward J2, under the "U2 antenna keepout" rule area) so a cable can
be plugged in with the lid off; the box wall on that side must leave room for the plug
body and the cable bend. **One cable entry: the 12 V leads to J1**, a 5.08 mm
2-pin screw terminal at the middle of the top edge, wire openings facing that edge
(pins at KiCad y 22.0, x 55.1 = + and 50.0 = -, i.e. ~40.5-45.6 mm from the left edge
and 5.5 mm below the top edge; the terminal body's entry face is ~0.9 mm in from the edge). The DHT22 stays
inside for now (see Temperature compensation), so no J2 entry.

## Firmware versioning

`irin_version` substitution at the top of `esphome/irin.yaml` (semver; started at
**0.3.0** on 2026-10-07). It feeds `esphome: project:` (`mglauser.irin`, shown on HA's
device page) and the **Firmware** template text_sensor (diagnostic, status page Diagnostics
group): "Irin X.Y.Z, ESPHome <ver>, built <time>", published once from on_boot.

**Check on every firmware change (for Claude):** before committing a change to
`esphome/irin.yaml` (or `esphome/www/`, which ships in the firmware) that changes
behavior, bump `irin_version` in the same commit and add a line to the README
Changelog. PATCH for a fix that doesn't change what the device reports; MINOR for new or
changed entities, behavior, or default tunables; while 0.x, breaking changes (entity
renames, new required secrets, wiring) are also MINOR. Comment-only edits and docs,
dashboard, HA-config or hardware-file changes do not bump. After pushing, tag the commit
`vX.Y.Z` and push the tag, with the owner's OK as for any push. Confirm the device
picked up the build from the Firmware sensor (its build time changes on every install).
1.0.0 is planned for the installed, enclosed reference build with proven alerts.

## Bench-before-vehicle checklist

- [x] I2C works with SDA=GPIO5 / SCL=GPIO6; SSD1306 (0x3C) + ADS1115 (0x48) both respond (2026-10-05)
- [x] OLED renders correctly (ESPHome "SSD1306 72x40" model handles the offsets)
- [x] Divider (47k/10k, 1% metal film) two-point calibrated against a DVM at 11.50 V and
      15.00 V on the bench. Redone 2026-10-06 after the analog-ground fix (see Voltage divider): fitted
      gain 5.7211 matches the measured resistor ratio 5.7208; constant offset ~-7 mV at A0
- [x] **No clipping verified up to 16 V**: 16.00 V reads 16.00 V (2026-10-06)
- [x] Reading accuracy at **12.22 V** (flooded 50% point): reads 12.22 V (2026-10-06)
- [x] DC-DC detection hysteresis verified at the 12.8/12.9 V boundary (2026-10-05)
- [x] Always-on current measured: ~10 mA at 12 V (deep sleep not used)
- [ ] WiFi reconnect and connect-timeout paths tested (power-cycle the AP)
- [x] Resting gate verified by simulating a DC-DC charge cycle on the bench: held SOC through
      14.4 V, fresh 50% at 12.22 V after rest, timestamped once HA time was available (2026-10-06)
- [ ] Entities appear in HA; alert automation fires on a forced low reading
- [x] Away report: AP off > 30 min (charge/rest on the bench supply meanwhile), AP on,
      summary posts; AP off < 30 min leaves the previous report in place (2026-10-06:
      14 min gap discarded; 0.6 h gap posted "SOC min 42%, 0.6 h below 50%, 1 charge")
- [x] Fallback AP `irin-Sunny` comes up on a wrong WiFi password; captive-portal rescue
      restores WiFi; away current ~40 mA at 12 V (2026-10-06)
- [x] Status page loads on the LAN behind auth, live updates (2026-10-06)
- [x] WiFi Setup link absent on the LAN; page still live-updates (2026-10-07)
- [ ] Status page via the fallback AP at http://192.168.4.1; WiFi Setup link appears above OTA Update and opens the setup page
- [ ] 24+ hour stability run before installation

## Safety

- Fuse the 12V input at **2-5 A**, as close to the battery terminal as practical
- Reverse-polarity protection on the input
- Regulated buck converter (12V -> 5V); confirm it tolerates 16 V and load-dump transients
- Weatherproof enclosure; keep away from heat and moving parts
- Ground to chassis for accurate readings
- **Confirm 12V-system work does not require high-voltage-system precautions on this
  EV** before touching anything under the hood
