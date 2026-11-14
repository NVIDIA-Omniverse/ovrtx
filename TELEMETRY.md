# Data Collection & Use

## Overview

OVRTX collects anonymous initialization data when the library initializes to help improve OVRTX. Collection is **enabled by default** and can be turned off without affecting OVRTX functionality.

## When collection happens

When OVRTX first initializes successfully in a process, it schedules one background send attempt. That is when `ovrtx_initialize()` succeeds in C, or when the first `ovrtx.Renderer` is created in Python; creating a renderer in C without a prior `ovrtx_initialize()` initializes OVRTX implicitly. Installing the wheel, importing `ovrtx`, or an unsuccessful initialization does not trigger a report. OVRTX reports at most once per process: creating additional renderers, or shutting OVRTX down completely (the last `ovrtx_shutdown()` or the last renderer being destroyed) and initializing it again, does not trigger additional reports. The attempt starts about one second after initialization. Delivery is best effort: there are no retries, and a short-lived process may exit before sending.

Other Omniverse libraries report separately under their own names. For example, an application using OVXR, which renders through OVRTX, sends one report for `ovxr` and one for `ovrtx`.

## What data is sent

The `LibraryStartup` event has two parameters: **library name and version**. The surrounding request also contains:

- A UTC timestamp, repeated in the event and request fields.
- The library version repeated in `clientVer`.
- A library build variant: `Release` or `iBeta` for a debug build. This describes the library build, not your application's build configuration.
- Fixed project and protocol values, including a project-wide `clientId`. That value identifies NVIDIA's telemetry project, not an individual user, device, or installation.
- Literal `undefined` values in unused identity, device, browser, and host-product fields, and literal `None` values in the protocol's consent fields. These placeholders are not values read from any account or device.

### Fields and expected values

The following tables list every value in the JSON request. Field paths such as `events[0].name` refer to the first and only event in the request. All values shown here are JSON strings. Version and time examples are illustrative, not fixed values.

#### Fixed and variable values

- **Built into the library:** the project/protocol fields, placeholder fields, and event name. `clientVariant` is set when the telemetry component is built (`Release` or `iBeta`), rather than detected from your application at runtime.
- **Library name and version:** the name is `ovrtx`; the version reflects the OVRTX library you are using.
- **Generated for each report:** the UTC timestamp, repeated in `events[0].ts` and `sentTs`.

#### Event and request information

| Field | Expected value | Meaning |
| --- | --- | --- |
| `events[0].name` | `"LibraryStartup"` | The event type; always the same. |
| `events[0].parameters.library` | `"ovrtx"`  | Library name. |
| `events[0].parameters.version` | Your OVRTX version, e.g. `"0.7.0"` | Version of the library being initialized. |
| `events[0].ts` | UTC time, e.g. `"2026-10-27T14:53:00.000Z"` | Time recorded when the report is prepared, with millisecond precision. |
| `sentTs` | Same value as `events[0].ts` | The same timestamp repeated for the telemetry protocol. |
| `clientVer` | Same value as `events[0].parameters.version` | Library version repeated for the telemetry protocol. |
| `clientId` | `"6697362192350625"` | Shared NVIDIA telemetry project ID; not an ID assigned to you or your device. |
| `clientType` | `"Native"` | Fixed client category. |
| `clientVariant` | `"Release"`; `"iBeta"` for a debug library build | Library build variant; not your application's build configuration. |
| `eventSchemaVer` | `"1.0"` | Fixed event-schema version. |
| `eventProtocol` | `"1.6"` | Fixed telemetry-protocol version. |
| `eventSysVer` | `"1.0"` | Fixed event-system version. |

#### Unused identity and device fields

The protocol includes the following fields, but OVRTX does not populate them with information about you or your system. Each contains the literal string `"undefined"`—not a hidden value or an identifier.

| Field | Expected value |
| --- | --- |
| `integrationId` | `"undefined"` |
| `browserType` | `"undefined"` |
| `userId` | `"undefined"` |
| `externalUserId` | `"undefined"` |
| `idpId` | `"undefined"` |
| `sessionId` | `"undefined"` |
| `deviceId` | `"undefined"` |
| `cpuArchitecture` | `"undefined"` |
| `deviceOS` | `"undefined"` |
| `deviceOSVersion` | `"undefined"` |
| `deviceType` | `"undefined"` |
| `deviceMake` | `"undefined"` |
| `deviceModel` | `"undefined"` |
| `productName` | `"undefined"` |
| `productVersion` | `"undefined"` |

#### Protocol consent fields

These fields contain the literal string `"None"`. They do not reflect consent settings read from any account or device.

| Field | Expected value |
| --- | --- |
| `gdprTechOptIn` | `"None"` |
| `gdprBehOptIn` | `"None"` |
| `gdprFuncOptIn` | `"None"` |
| `deviceGdprTechOptIn` | `"None"` |
| `deviceGdprBehOptIn` | `"None"` |
| `deviceGdprFuncOptIn` | `"None"` |

### Complete example request body

This illustrative release-build example uses library name `ovrtx`, version `0.7.0`, and a sample timestamp. Version and timestamp values vary with the actual library and invocation.

```json
{
  "clientId": "6697362192350625",
  "eventSchemaVer": "1.0",
  "eventProtocol": "1.6",
  "eventSysVer": "1.0",
  "integrationId": "undefined",
  "clientType": "Native",
  "clientVariant": "Release",
  "browserType": "undefined",
  "userId": "undefined",
  "externalUserId": "undefined",
  "idpId": "undefined",
  "sessionId": "undefined",
  "deviceId": "undefined",
  "cpuArchitecture": "undefined",
  "deviceOS": "undefined",
  "deviceOSVersion": "undefined",
  "deviceType": "undefined",
  "deviceMake": "undefined",
  "deviceModel": "undefined",
  "productName": "undefined",
  "productVersion": "undefined",
  "gdprTechOptIn": "None",
  "gdprBehOptIn": "None",
  "gdprFuncOptIn": "None",
  "deviceGdprTechOptIn": "None",
  "deviceGdprBehOptIn": "None",
  "deviceGdprFuncOptIn": "None",
  "events": [
    {
      "name": "LibraryStartup",
      "ts": "2026-10-27T14:53:00.000Z",
      "parameters": {
        "version": "0.7.0",
        "library": "ovrtx"
      }
    }
  ],
  "sentTs": "2026-10-27T14:53:00.000Z",
  "clientVer": "0.7.0"
}
```

### Destination and transport

The report is an HTTP POST to:

```text
http://6697362192350625.events.telemetry.data.nvidia.com/v1.1/events/json
```

**The connection uses unencrypted HTTP, not HTTPS.** The request can therefore be read by parties able to observe the network traffic. It does not use user credentials or an embedded secret.

The request also includes these HTTP headers. The user-agent is a fixed library string, not your browser's user-agent.

| Header | Expected value |
| --- | --- |
| `Host` | `6697362192350625.events.telemetry.data.nvidia.com` |
| `User-Agent` | `ovx-lib-startup/1` |
| `Accept` | `application/json` |
| `X-Event-Protocol` | `1.6` |
| `Content-Type` | `application/json;charset=utf-8` |
| `Content-Length` | Byte length of the JSON body; varies with the actual values. |
| `Connection` | `close` |

### Information added by the receiving service

As with any network request, the receiving service can see the connection's source IP address. It uses that address to derive approximate geographic and network information and whether the request originates from an NVIDIA network. The raw client IP address is not retained by the ingestion service.

Derived metadata can include country, region, city, timezone, estimated latitude/longitude, and network-provider information. These are IP-based estimates, not GPS coordinates read from your device; their accuracy varies. The service also adds processing metadata such as receipt time and processing datacenter. These fields are separate from the JSON sent by OVRTX.

For information about NVIDIA's handling of data, see the [NVIDIA Privacy Policy](https://www.nvidia.com/en-us/about-nvidia/privacy-policy/).

## Turn off data collection

Either of the following controls prevents the telemetry request without disabling OVRTX functionality.

### Environment variable

Set `NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED` to exactly `1` **before starting the application process**. This also turns off the reports of other Omniverse libraries that use the same mechanism, such as OVXR.

Preferred: set the variable for a single launch by putting it in front of the launch command. It applies to that process only:

```bash
NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1 ./your-app
```

Windows `cmd` can scope it to one launch the same way:

```bat
cmd /c "set NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1&& your-app.exe"
```

Windows PowerShell has no per-command prefix. The variable stays set for the rest of the PowerShell session and for every process launched from it, so remove it when you are done:

```powershell
$env:NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED = "1"
.\your-app.exe
Remove-Item Env:NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED
```

Exporting the variable in a shell (`export NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1`), or setting it in a shell profile or in system environment settings, turns off telemetry for every process launched from that shell or account until you unset it. Use that only if you want that effect.

Changing the environment variable from inside an already-running application is not a supported way to opt out. Use the programmatic control below instead, before OVRTX initializes.

### Programmatic control

Python:

```python
import ovrtx
ovrtx.library_telemetry_opt_out()
# Create your ovrtx.Renderer only after this call.
```

C/C++:

```c
ovrtx_library_telemetry_opt_out();
/* Call before ovrtx_initialize(), or before the first ovrtx_create_renderer()
   if the application does not call ovrtx_initialize(). */
```

Opt out before OVRTX initializes to prevent the report. An opt-out cannot retract a request that has already been sent. The programmatic control affects OVRTX only; other Omniverse libraries provide their own.

## Offline use and shutdown

Report delivery happens in the background; renderer creation does not wait for delivery. Offline or blocked delivery does not fail OVRTX initialization and does not produce a telemetry failure log.

If a platform DNS lookup is still in progress when OVRTX shuts down (the final `ovrtx_shutdown()`, which the Python package also calls at interpreter exit), shutdown can wait for the platform's resolver timeout. Disabling telemetry before initialization avoids this telemetry-related lookup and wait.
