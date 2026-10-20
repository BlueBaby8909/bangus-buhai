# Rebuild firmware

This area is reserved for the replacement ESP-IDF firmware.

- Source target: ESP32-S3.
- Recorded framework baseline: ESP-IDF 6.0.2-dirty; the isolated prototype build passed with configuration notifications (see T04).
- The existing firmware remains preserved in ../../firmware.
- T01 does not copy credentials, certificates or local sdkconfig files.
- T04 verifies the toolchain, components and build starting point.
- Build evidence and hardware limits are recorded in [T04](../../docs/status/tasks/T04.md).

## T04 specimen removed

On 2026-10-17 the owner explicitly requested deletion of `baseline/`, and AI
removed that directory only after checking its exact resolved path. No archive
was made. Its prototype copy, local dependency snapshot, generated build and
raw build/hash evidence are no longer available at that path. The historical
[T04 record](../../docs/status/tasks/T04.md) retains the recorded result and
limits, but the removed raw artifacts cannot be rechecked in place. The original
`../../firmware/` and this replacement project were not deleted or changed by
the removal. The replacement has no dependency on the removed specimen.

## T05 replacement sensing application

The project at this directory's root is the new sensing application.
`main/` starts one sensing task on a two-second schedule;
`components/sensor_service/` owns filtering, independent sensor errors and
consistent reading copies. Use this root for replacement work.

In the owner's ESP-IDF PowerShell terminal:

```powershell
cd 'C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\firmware'
$env:IDF_TARGET = "esp32s3"
idf.py build
```

The service returns acquisition errors per metric; `ESP_OK` from a service read
only means it produced a snapshot. Consumers must check `has_value` before using
`value`. Unknown internal times/ages are `-1` and must map to JSON null in a future
wire adapter, never to negative JSON ages or numeric zero. No JSON/UTC/network
integration is implemented here. Times are 64-bit boot-relative milliseconds.

Temperature uses the DS18B20 operating range (-55 through 125 C) for input
validation, not hatchery policy. The EMA is seeded from the first successful
sample and reseeded after a stale gap; failed/non-finite samples do not update it
or last-success time. Temperature is stale at age >=60,000 ms, including when
`get_latest` is called without a new acquisition. Invalid, missing and stale
metrics have `has_value=false`, even if historical sample-age metadata remains.

The retained prototype NTU polynomial and 2.28 voltage scale are unverified
calibration. Converted turbidity therefore remains `unverified`, with unknown
last-valid NTU age; ADC calibration is not NTU calibration. This does not detect
every analog sensor disconnection or validate physical sensor accuracy. Default
pH is 7.80 (`BB_PH_DEFAULT=780`), `source=default`, `validity=unverified`, with
unknown sample ages. No turbidity/pH stale timeout or biological limit is invented.

Initialize the service once before tasks start; only the sensing task owns sensor
driver access. T06 shortens the snapshot mutex to state updates/copies; conversion
occurs outside it. The added `sensor_service_try_get_latest` bounds control/display
lock waiting without changing the original getter API. The earlier T05 pass is
historical evidence; rerun the extended regressions after this integration change.
No networking or new watchdog configuration is included. Test code and evidence limits are
in [the regression app](tests/README.md) and [T05](../../docs/status/tasks/T05.md).
No replacement build, tests or device operation were run by AI for this slice.

## T06 relay and LCD integration (unloaded-demo scope complete)

The owner confirmed that the relay accepts a 3.3 V control signal and that LCD
SDA/SCL are at 3.3 V, with 5 V system power. These are owner confirmations, not
AI measurements. The replacement retains the working prototype's GPIO wiring,
LCD backpack mapping and expected address.

Keep three components, each with one header, one C source and CMakeLists.txt:

- `relay_driver`: active-low GPIO 3, preload HIGH before output enable, return
  GPIO errors, and report state only after successful operations. A failed
  operation marks state unknown, not OFF. State describes the GPIO command,
  not contact feedback or connected equipment operation.
- `relay_control`: one writer task, AUTO/MANUAL policy and state queries. It checks
  temperature every 250 ms. AUTO uses ON >=32.5 C / OFF <=31 C demo rules; manual
  mode persists until explicit AUTO. Bad/missing/stale temperature forces an OFF
  request and cancels remembered manual ON. Output errors cancel remembered ON too.
  Queue submission means accepted, not applied; an eight-entry full queue returns
  ESP_ERR_TIMEOUT without dropping earlier requests. Pure policy helpers stay
  in this same source/header for regression tests.
- `lcd_display`: GPIO 4 SDA / GPIO 5 SCL, 0x27, 100 kHz, prototype PCF8574 nibble
  mapping. Includes initialization, page formatting and changed-row writes.
  Each transaction has a 50 ms timeout. Startup/update errors propagate; failed
  initialization releases device/bus handles, with failed cleanup retried before
  reallocating. Ordinary updates write changed 16-character rows and never clear
  the entire screen. Separate port and display-service components were removed.

`main.c` starts the sensing and control tasks and contains the lower-priority
LCD task. Display refresh is once per second; two pages rotate every three
seconds: Temp/Relay and Turbidity/pH. Temperature uses the LCD degree glyph and C;
turbidity uses NTU (label shortened to Turb). pH is unitless. Relay state includes
AUTO/MANUAL. Owner requested removal of the asterisk and DEFAULT screen labels;
the underlying unverified conversion and default pH remain unchanged.
Faults pin the temperature/relay page. Unknown
relay state cannot appear as OFF; a reported ON during a temperature fault is
shown as ON UNSAFE. Display failures retry after five seconds and do not stop
sensing/control. The relay remains unloaded. No MQTT command delivery, new
calibration, partition change or watchdog reconfiguration was added.

Settings are in `main/Kconfig.projbuild`; ESP-IDF will incorporate the new defaults
on the owner's next build. No generated sdkconfig was edited by AI. Manual requests
currently use the C API; no button, serial command or network UI is implied.

The test app now mocks ESP-IDF GPIO/I2C APIs directly; it tests initialization
cleanup, timeout/encoding behavior and OFF-before-enable ordering as well as the
policy, page formatting, stale/failure/recovery and original sensor regressions.
All eight cases passed in owner-run COM11 output reviewed on 2026-10-17.
Unrelated SDK GPIO startup calls retain the real SDK
behavior; the configured relay pin and LCD I2C operations are simulated.

**AI has not built, run or flashed this revision.** T06 is complete within its documented unloaded-demo limits: owner-run builds and
final eight tests passed, and the owner confirmed LCD and relay operation.
See [T06](../../docs/status/tasks/T06.md) and [tests](tests/README.md). The prior
T05 PASS is evidence for its earlier revision, not this changed source.

## T07 Wi-Fi setup and service commands (build/device checks pending)

The replacement uses NimBLE, protocomm Security 2 and the public
network_provisioning 1.2.4 protocol handlers. It deliberately does not use the
manager's early credential-write flow. Wi-Fi candidates stay in RAM until an IP
arrives within 30 seconds; then one versioned NVS blob (`bb_wifi/active`) is
written and committed. Failed/cancelled trials restore the saved network.
Single-blob NVS update design still requires the planned power-interruption tests;
these implementation choices are not hardware qualification evidence.

Before the next build, run from this firmware folder:

```powershell
python components/wifi_manager/tools/prepare_setup.py --device-id BB-14C19FC68C60
idf.py -p COM11 build flash monitor
```

The first command creates/reuses setup material under
`C:\Users\Kent Christian\BangusBuhai-Secrets\t07`. It does not install packages,
print the setup password, modify device certificates, or rotate existing valid
setup credentials. `wifi-setup.json` contains the phone username/password and
BLE device name `PROV_C68C60`; `wifi-setup-qr.json` is a private QR payload, not a
rendered QR image. Use a Security-2-capable Espressif BLE provisioning client
and its manual username/password/SSID controls where available. Phone-client
interoperability remains to be checked; do not downgrade security to work around it.
Keep these files private and backed up. Do not put the QR payload into a public QR
website. Only the salt/verifier and public device binding enter the firmware via
`wifi_setup_material.h`; the CMake include directory is outside the repository.
To rotate setup credentials deliberately, preserve the existing material first,
generate a new set in a new external directory and build with
`-DBB_WIFI_SETUP_DIR=<that-directory>`. Reflash that firmware before using the new
phone credentials. Losing setup material does not erase saved Wi-Fi settings.

The USB Serial/JTAG port is now the primary console, matching the owner's COM11
connection. At the `bb>` prompt:

| Command | Effect |
|---|---|
| `wifi status` | Connection/setup state; cached scan SSIDs, channels, RSSI and truncation count; no passwords |
| `wifi setup` | Open/reopen a five-minute BLE setup window |
| `wifi forget CONFIRM` | Remove only replacement Wi-Fi key `bb_wifi/active`, stop its connection and open setup |

First boot without a saved record opens setup once. Expiry leaves it closed until
USB reopens it. Saved-network outages/authentication errors never erase credentials
or automatically open setup. After a successful trial, BLE closes after a short
five-second status-response grace period (or sooner if the phone disconnects).
Disconnecting the phone before success cancels the trial. Setup timeout cancels
an unfinished trial too. Scans retain up to 64 APs; manual entry is independent
of the scan list. Missing iPhone hotspot cause is still unverified.

Forgetting does not erase the prototype's separate SDK Wi-Fi settings, device
certificates, identity, setup verifier or unrelated NVS keys. This firmware only
loads its own `bb_wifi/active` record. Physical flash extraction protection remains
outside this checkpoint: the saved password is not encrypted at rest by this change.

Owner checks after building: first provisioning and reboot; wrong-password
replacement; successful replacement; phone cancellation and power loss during a
trial; five-minute expiry/reopening; confirmed forgetting; saved-network outage
and restoration; continued local operation with LCD/relay connected. Re-run the
existing eight regressions. No MQTT integration or completed T07 claim is implied.
