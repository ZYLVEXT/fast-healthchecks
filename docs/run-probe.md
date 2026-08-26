# Running probes without ASGI

For CLI scripts, cron jobs, or tests, use `run_probe` instead of mounting ASGI routes:

```python
import asyncio
from fast_healthchecks.execution import Probe, run_probe
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

Optional parameters: `timeout` (seconds), `max_concurrency` (parallel-mode cap on simultaneously running checks, default 8, `None` = unlimited), `on_check_start`, `on_check_end` (callbacks).

## Hooks for metrics and tracing

`on_check_start` and `on_check_end` are optional async callbacks that run before and after each check. Use them to record metrics (e.g. duration, success/failure) or to create tracing spans.

- **on_check_start(check, check_index)** — called once per check before it runs. You can start a span or timer here and store it (e.g. in a context variable or dictionary keyed by `check_index`).
- **on_check_end(check, check_index, result)** — called after the check completes with the `HealthCheckResult`. Use `result.healthy` and `result.error` for metrics or span status.

Providing either hook switches that probe run to sequential execution so callback ordering is deterministic.

Example: record check duration with a simple metrics callback (store start times by check index):

```python
import time
from fast_healthchecks.checks.types import Check
from fast_healthchecks.execution import Probe, run_probe
from fast_healthchecks.models import HealthCheckResult

starts: dict[int, float] = {}

async def on_start(_check: Check, check_index: int) -> None:
    starts[check_index] = time.monotonic()

async def on_end(check: Check, check_index: int, result: HealthCheckResult) -> None:
    duration = time.monotonic() - starts.get(check_index, time.monotonic())
    check_name = getattr(check, "_name", type(check).__name__)
    print(f"{check_name} took {duration:.3f}s, healthy={result.healthy}")

report = await run_probe(probe, on_check_start=on_start, on_check_end=on_end)
```

For OpenTelemetry or other backends, create a span in `on_check_start` and end it in `on_check_end` with the result status.

## Timeout semantics

- **Probe-level timeout:** The only timeout in the public contract is the probe-level `timeout` argument to `run_probe`. There is no per-check timeout; when the probe timeout is exceeded, **all** pending checks are cancelled (asyncio cancels the gather).
- **One-check-hung vs others-done:** If one check hangs and the others complete, the probe still waits until the probe-level timeout; then either an error is raised or a report with failures is returned (see modes below). No "partial cancel" of only the hung check—cancel applies to the whole probe run.
- **Two modes only:**
  - **Mode A** (`on_timeout_return_failure=False`): On timeout, `run_probe` raises `asyncio.TimeoutError` and does **not** return a report.
  - **Mode B** (`on_timeout_return_failure=True`): On timeout, `run_probe` returns a failed `HealthCheckReport`; each result has a structured `PROBE_TIMEOUT` error.
- **Where Mode B is used:** `ProbeAsgi` (and thus ASGI health routes) calls `run_probe(..., on_timeout_return_failure=True)` so that timeouts yield an HTTP response instead of raising.

## Probe logging (optional)

Structured logging for probe and check execution is **optional** and **disabled by default**. No external logging framework is required.

- **Abstraction:** Use `get_probe_logger()` / `set_probe_logger()` and `get_stdlib_probe_logger()` from `fast_healthchecks.logging`. The logger receives `log(level, msg, **extra)`; when using the stdlib adapter, `extra` is redacted (same keys as `utils.redact_secrets_in_dict`) so secrets never appear in log output.
- **Events:** When enabled, `run_probe` logs `probe_start` (probe name, checks count), and after completion `probe_end` (probe name, healthy, results summary). Per-check `check_start` / `check_end` (check name, index, healthy) are logged at DEBUG.
- **Enable:** Call `set_probe_logger(get_stdlib_probe_logger())` before running probes. Use `NullLogger()` or `set_probe_logger(NullLogger())` to disable (default).
