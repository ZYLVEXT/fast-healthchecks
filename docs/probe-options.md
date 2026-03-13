# Probe options

| Parameter | Description |
|-----------|-------------|
| `name` | Probe identifier (e.g. `"liveness"`, `"readiness"`, `"startup"`). |
| `checks` | List of health checks to run. |
| `summary` | Custom description for the probe (used in responses). If omitted, a default is generated from `name`. |
| `allow_partial_failure` | If `True`, probe is healthy when at least one check passes. Default: `False`. |

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

## RunPolicy Options

When using [`ProbeRunner`][ProbeRunner] directly, you can customize execution behavior with `RunPolicy`:

| Parameter | Description |
|-----------|-------------|
| `mode` | Controls how probe failures affect overall health: `"strict"` (any failure marks failed) or `"reporting"` (failures reported but don't fail check). Default: `"strict"`. |
| `execution` | Controls probe execution: `"parallel"` (all probes run concurrently) or `"sequential"` (probes run one at a time). Default: `"parallel"`. |
| `probe_timeout_ms` | Timeout in milliseconds for each probe. If `None`, probes use their default timeout. Default: `None`. |
| `health_evaluation` | Controls evaluation strategy: `"all_required"` (all probes must pass) or `"partial_allowed"` (some probes can fail without failing overall). Default: `"all_required"`. |

Example:

```python
from fast_healthchecks import ProbeRunner, RunPolicy

policy = RunPolicy(
    mode="strict",
    execution="parallel",
    probe_timeout_ms=5000,
    health_evaluation="all_required"
)

async with ProbeRunner(policy) as runner:
    report = await runner.run(probe)
```
