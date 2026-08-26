# Probe options

| Parameter | Description |
|-----------|-------------|
| `name` | Probe identifier (e.g. `"liveness"`, `"readiness"`, `"startup"`). |
| `checks` | List of health checks to run. |
| `summary` | Custom description for the probe (used in responses). If omitted, a default is generated from `name`. |
| `default_check_timeout_ms` | Reserved legacy field; it does not alter execution. Use `RunPolicy.probe_timeout_ms` for a probe-wide timeout. |

To customize HTTP responses, pass `options=build_probe_route_options(...)` to `HealthcheckRouter` or `health()`. Build options with:

| Parameter | Description |
|-----------|-------------|
| `success_handler` | Handler for healthy responses. Receives `ProbeAsgiResponse`, returns response body (or `None` for empty). |
| `failure_handler` | Handler for unhealthy responses. Same signature as `success_handler`. |
| `success_status` | HTTP status for healthy (default: `204` No Content). |
| `failure_status` | HTTP status for unhealthy (default: `503`). |
| `debug` | Include check details in responses (default: `False`). |
| `prefix` | URL prefix for probe routes (default: `"/health"`). |
| `timeout` | Max seconds for all checks; on exceed returns failure (default: `None` = no limit). |

Example: `HealthcheckRouter(Probe(...), options=build_probe_route_options(debug=True, prefix="/health"))`.

### Debug mode

With `debug=True`, unhealthy responses bypass the failure handler by design and dump the full report, including each `error.message` (`"<ExceptionType>: <message>"`). Error metadata is redacted by key, but messages are free text and may name internal hosts or dependency details. Keep `debug=False` (the default) on endpoints reachable from outside the deployment; enable it only for internal diagnostics.

## RunPolicy Options

When using [`ProbeRunner`][ProbeRunner] directly, you can customize execution behavior with `RunPolicy`:

| Parameter | Description |
|-----------|-------------|
| `mode` | Controls probe-timeout handling: `"strict"` raises `HealthCheckTimeoutError`; `"reporting"` returns a failed report. Ordinary failed checks remain failed in both modes. Default: `"strict"`. |
| `execution` | Controls check execution within one probe: `"parallel"` or `"sequential"`. Default: `"parallel"`. |
| `probe_timeout_ms` | Timeout in milliseconds for one `runner.run(probe)` call. Default: `None`. |
| `health_evaluation` | Controls evaluation strategy: `"all_required"` (all probes must pass) or `"partial_allowed"` (some probes can fail without failing overall). Default: `"all_required"`. |
| `max_concurrency` | Caps how many checks run at once in parallel mode. `None` removes the cap. Default: `8`. |

Example:

```python
from fast_healthchecks import ProbeRunner, RunPolicy

policy = RunPolicy(mode="strict", execution="parallel", probe_timeout_ms=5000)

async with ProbeRunner(policy) as runner:
    report = await runner.run(probe)
```
