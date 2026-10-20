# Sensor-service regression app

## Current T06 extension (eight tests passed)

On 2026-10-17 the owner supplied a successful test-app build (`0x2d320` image,
passing size check) alongside a successful normal-app build. AI reviewed that
output. The owner then flashed and ran the test app on COM11; AI reviewed
`8 Tests 0 Failures 0 Ignored`, `OK` in attachment
`b5a4f36b-b30e-4afa-a906-aa6fe92e2be7/Pasted text.txt`.

The app now runs eight tests: the original T05 lifecycle test, a snapshot-access
test that blocks simulated conversion in another task, and six T06 cases covering
AUTO thresholds/staleness, manual priority/fault latching, rejected temperatures,
active-low driver state/errors, two display pages/fault labels, and LCD row
cache/error isolation. Sensor calls and ESP-IDF GPIO/I2C functions use linker
wrappers; relay/LCD operations are simulated, while unrelated GPIO startup calls use the real SDK. The RTOS clock remains real.

The original T05 PASS below applies to the earlier revision, not these new changes.
The actual controller/display task scheduling and queue saturation are not
exercised by the six policy/driver/formatter cases. The normal app now contains
real GPIO/I2C drivers; the tests mock their SDK calls. Tests check LCD nibble
encoding, finite 50 ms timeouts, initialization cleanup/retry, row-cache reset and
first-error stop, plus relay OFF-before-output-enable and failed-write state.
This test PASS does not establish physical relay/LCD behavior.
Unity 64-bit support remains enabled in existing configuration and defaults.
AI did not run setup/build/test/flash commands for this extension.

The owner can compile from this directory with `idf.py build`. A successful build
does not execute assertions. Do not re-run `set-target` just to rebuild an already
configured ESP32-S3 test project. Preserve local build/configuration/dependency
files. Any device run is owner-led and separate from an AI compile/source edit.

## Earlier T05 evidence

This separate ESP-IDF/Unity app exercises the production service with simulated
sensor results and deterministic uptime. Linker wrappers replace both driver
initialization/read functions; the test code does not operate sensor GPIOs.
The normal application does not include these wrappers.

Cases cover startup, initialization failure, genuine zero at uptime zero,
independent sensor errors, filtering, NaN/infinity rejection, sample/capture timing,
snapshot immutability, default pH, the 59,999/60,000/60,001 ms stale boundary,
recovery and uptime past 32-bit milliseconds. NTU calibration is not validated.

In a VS Code ESP-IDF PowerShell terminal, the owner may compile this separate app:

```powershell
cd 'C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\firmware\tests'
$env:IDF_TARGET = "esp32s3"
idf.py set-target esp32s3
idf.py build
```

Building does not execute assertions. On 2026-10-17 the owner built, flashed and
ran this app on COM11. An initial run stopped because Unity 64-bit support was
disabled. After enabling it in sdkconfig and sdkconfig.defaults, the rerun passed:

```text
test_snapshot_lifecycle:PASS
1 Tests 0 Failures 0 Ignored
OK
```

AI reviewed the owner-supplied output; AI did not execute device/build commands.
This is one composite lifecycle test with simulated sensor inputs and service
time. It does not validate sensor accuracy, calibration or physical fault recovery.
The final test image is 170,976 bytes. The 2 MiB flash-header/8 MiB detected-size
mismatch remains recorded in [T05](../../../docs/status/tasks/T05.md).
Its generated build,
configuration and managed dependencies belong to this test project, not the
preserved baseline. After test-project work, return to `rebuild/firmware/` before
building the normal sensing application.

The subsequent owner-requested two-page LCD layout changes the existing display assertions. The earlier eight-test PASS predates that formatting change; owner rebuild/rerun is pending.

Owner subsequently reran the suite after the final degrees C / NTU / unitless pH and relay AUTO/MANUAL display change: all eight named tests PASS, 8 Tests 0 Failures 0 Ignored, OK. AI reviewed pasted output. This supersedes the layout regression-pending notes above; physical relay ON/fault transitions and task/queue scheduling remain outside these tests.
