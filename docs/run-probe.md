# Running probes without ASGI

For CLI scripts, cron jobs, or tests, use `run_probe` instead of mounting ASGI routes:

```python
import asyncio
from fast_healthchecks.integrations.base import Probe, run_probe
from fast_healthchecks.checks.function import FunctionHealthCheck

async def main():
    probe = Probe(
        name="readiness",
        checks=[FunctionHealthCheck(func=lambda: True, name="Ping")],
    )
    report = await run_probe(probe)
    print(report.healthy, report.results)

asyncio.run(main())
```

Optional parameters: `timeout` (seconds), `on_check_start`, `on_check_end` (callbacks).

## Hooks for metrics and tracing

`on_check_start` and `on_check_end` are optional async callbacks that run before and after each check. Use them to record metrics (e.g. duration, success/failure) or to create tracing spans.

- **on_check_start(probe_name, check_name, check_index)** — called once per check before it runs. You can start a span or timer here and store it (e.g. in a context var or dict keyed by check_index).
- **on_check_end(probe_name, check_name, check_index, result)** — called after the check completes with the `HealthCheckResult`. Use `result.healthy` and optionally `result.error_details` for metrics or span status.

Example: record check duration with a simple metrics callback (store start times by check index):

```python
import time
from fast_healthchecks.integrations.base import run_probe, Probe

starts: dict[int, float] = {}

async def on_start(probe_name: str, check_name: str, check_index: int) -> None:
    starts[check_index] = time.monotonic()

async def on_end(probe_name: str, check_name: str, check_index: int, result) -> None:
    duration = time.monotonic() - starts.get(check_index, time.monotonic())
    # e.g. metrics.histogram("healthcheck_duration_seconds", duration, tags=[check_name])
    print(f"{check_name} took {duration:.3f}s, healthy={result.healthy}")

report = await run_probe(probe, on_check_start=on_start, on_check_end=on_end)
```

For OpenTelemetry or other backends, create a span in `on_check_start` and end it in `on_check_end` with the result status.

## Timeout semantics

- **Probe-level timeout:** The only timeout in the public contract is the probe-level `timeout` argument to `run_probe`. There is no per-check timeout; when the probe timeout is exceeded, **all** pending checks are cancelled (asyncio cancels the gather).
- **One-check-hung vs others-done:** If one check hangs and the others complete, the probe still waits until the probe-level timeout; then either an error is raised or a report with failures is returned (see modes below). No "partial cancel" of only the hung check—cancel applies to the whole probe run.
- **Two modes only:**
  - **Mode A** (`on_timeout_return_failure=False`): On timeout, `run_probe` raises `asyncio.TimeoutError` and does **not** return a report.
  - **Mode B** (`on_timeout_return_failure=True`): On timeout, `run_probe` returns a `HealthCheckReport` with failed results for all checks (timed-out checks have `error_details` e.g. `"Probe timed out"`); `report.healthy` obeys `probe.allow_partial_failure`.
- **Where Mode B is used:** `ProbeAsgi` (and thus ASGI health routes) calls `run_probe(..., on_timeout_return_failure=True)` so that timeouts yield an HTTP response instead of raising.

## Probe logging (optional)

Structured logging for probe and check execution is **optional** and **disabled by default**. No external logging framework is required.

- **Abstraction:** Use `get_probe_logger()` / `set_probe_logger()` and `get_stdlib_probe_logger()` from `fast_healthchecks.logging`. The logger receives `log(level, msg, **extra)`; when using the stdlib adapter, `extra` is redacted (same keys as `utils.redact_secrets_in_dict`) so secrets never appear in log output.
- **Events:** When enabled, `run_probe` logs `probe_start` (probe name, checks count), and after completion `probe_end` (probe name, healthy, results summary). Per-check `check_start` / `check_end` (check name, index, healthy) are logged at DEBUG.
- **Enable:** Call `set_probe_logger(get_stdlib_probe_logger())` before running probes. Use `NullLogger()` or `set_probe_logger(NullLogger())` to disable (default).
