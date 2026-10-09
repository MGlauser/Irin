# Parts List — Irin battery monitor (12V prototype)

Enough parts for **three complete units** once the remaining items land.

---

## On hand / ordered

| Item | Qty | Notes |
|---|---|---|
| ESP32-C3 0.42" OLED board (01Space design) | 3 | |
| HiLetgo ADS1115 16-bit 4-ch ADC (B07VPFLSMX) | 3 | Ordered, $11.89. No Qwiic connector. |
| MP1584EN buck module, adjustable | 5 | Ordered, $8.69. Set to 5.0 V. |
| DHT22 / AM2302 | 2 | Ordered, $7.99. On J2; **inside the box for now** (2026-10-08) — see below. |
| 18 GA micro fuse holders, inline | 6 | Ordered, $8.99. Confirm fuses included. |
| PETG / ASA filament | — | On hand. Enclosure printed in-house. |

---

## Still to order

### Check stock — not on the Amazon order

| Item | Qty | Notes |
|---|---|---|
| TVS, 18 V breakdown | 3 | **P6KE18A** — 600 W DO-15. VRWM 15.3 V, VBR 17.1-18.9 V, Vc 25.2 V at 24 A. MP1584 abs max is 30 V. Standard on the PCB (also the reverse-polarity crowbar). Banded end (cathode) to the + rail. |
| Micro blade fuses, 5 A | 3 | If not included with the holders |

**Reverse-polarity Schottky: dropped by decision.** Owner-built, wired once — not a
failure mode worth a diode or the 0.4 V it costs.

TVS is a different case and is fitted as standard (2026-10-08): it handles inductive
switching transients, and a reversed hookup forward-biases it and blows the fuse, which
protects kits built by others.

Source: [20PCS P6KE18A, DO-15 axial, unidirectional, 600 W](https://www.amazon.com/dp/B0FRMDHL9Q)

> **Suffix matters:** `P6KE18A` is unidirectional, `P6KE18CA` is bidirectional. Use the
> **A** on a ground-referenced DC rail — it clamps lower and there is no negative
> excursion to suppress. Many Amazon listings and assortments default to CA.

*Qwiic cable dropped: soldering GPIO5/6/3V3/GND to header pins beats fabricating a
JST SH 1 mm pigtail.*

### Likely already in stock

| Item | Qty | Notes |
|---|---|---|
| 47k 1% metal film | 3 | Divider R1 (measure before fitting — a mislabeled strip bit once) |
| 10k 1% metal film | 3 | Divider R2 — same series as R1 |
| 4.7k-10k | 3 | DHT22 data pullup (bare 4-pin part only; 3-pin modules have it) |
| 0.1 µF ceramic | 3 | Buck input (C3) |
| 1000 pF mica | 6 | Two in parallel across R2 (C1 = 2 nF) |
| 100 µF / 35 V electrolytic | 3 | Buck input bulk |
| JST-XH 3-pin header + housing/crimps, 3-core cable (≤1 m) | 3 | J2 remote DHT22 lead |
| 2-pin screw terminal, 5.08 mm pitch (KF301-2P / Phoenix MKDS 1,5-2-5.08 class) | 3 | J1, 12 V leads (PCB rev B) |
| Perfboard, 18 AWG wire, ring terminals, cable glands, heat shrink | — | |

Net new spend: **~$25-30**.

---

## Divider

**47k / 10k = 5.7:1** (unit 1 measured 46.5k / 9.85k = 5.72:1; was 470k/100k). Sized against the ADS1115's VDD+0.3 = 3.6 V ceiling at
VDD = 3.3 V.

| Battery | At A0 |
|---|---|
| 12.22 V (50% SOC, flooded) | 2.14 V |
| 14.4 V (DC-DC on) | 2.52 V |
| 16.0 V (design max) | 2.80 V |
| — 3.6 V limit reached at — | 20.6 V |

PGA gain 1 (±4.096 V FSR) → 125 µV/LSB = 0.71 mV at the battery.

2 nF (2 x 1000 pF mica) across R2. 1% is fine — calibration cancels initial tolerance, and same-series
parts cancel most tempco in the ratio.

---

## Connections

**ADS1115** — Qwiic from the ESP32 (red 3.3 V, black GND, blue SDA, yellow SCL) to the
module. ADDR to GND = 0x48; OLED is 0x3C.

**Power** — 5 V into the board's 5V pin. Efficiency is irrelevant against the
vehicle's own parked draw, and this keeps onboard protection plus USB for flashing.

**DHT22** — data on **GPIO3**. 4.7-10k pullup if using the bare 4-pin part. ESPHome
`update_interval: 300s`; expect occasional NaN from WiFi interrupt jitter, which is
harmless at this timescale.

> **Decided (2026-10-05): DHT22 remote-mounted outside the enclosure**, on a 3-wire
> cable to board connector J2 (JST-XH 3-pin, 1=VCC 2=DATA 3=GND) through a cable gland.
> Removes the self-heating offset of the earlier inside-mount. At 3.3 V supply the
> AM2302 datasheet limits the cable to ~1 m.
>
> **For now (2026-10-08): inside the first PCB enclosure**, plugged into J2 and glued to
> the wall, so the box has a single cable entry (12 V). Reads a few degC warm; errs safe.

**Fuse** — the fuse protects the 18 GA harness against a chassis short, not the 150 mA
load. 5 A against 18 GA is correct; Micro2 blade fuses are scarce below 5 A anyway.

**Front end** —

```
Battery+ ──[5A fuse]──┬──[47k/10k divider]────> ADS1115 A0
                      ├──[TVS 18V]──┐   (standard)
                      └─────────────┴──> MP1584 ──> 5 V
Battery- ──────────────────────────────────────────> GND
```

Straight to the battery posts, not a downstream accessory circuit.

---

## Open items

- [ ] Qwiic connector populated on the board? Else GPIO5/6/3V3/GND direct.
- [ ] 12V battery location — under hood vs. rear drives enclosure temp rating and WiFi margin
- [x] Battery chemistry: flooded lead-acid, 50 Ah (confirmed 2026-10-05; not AGM)
- [ ] WiFi RSSI at the mounting location (ceramic chip antenna; a metal bay is worst case)
- [x] Temperature sensor: DHT22/AM2302 on J2, inside the box for now (DS18B20 not used)
