# URL check and SSRF protection

**Use only trusted URLs from application configuration.** Do not pass user-controlled input to `UrlHealthCheck` or to `validate_url_ssrf` / `validate_host_ssrf_async`; otherwise you risk SSRF and DNS rebinding.

## Behaviour

- **Schemes:** Only `http` and `https` are allowed by default. Validation is done by `validate_url_ssrf` (and by `UrlHealthCheck` at construction). Custom schemes are not permitted for the URL check.
- **block_private_hosts:** When `True`:
  - **At construction:** The URL host (if it is a literal IP) is checked; loopback and private/reserved ranges are rejected. Hostnames are not resolved at construction time.
  - **At run time:** Before each request, the host is resolved via `validate_host_ssrf_async`. If the hostname resolves to any loopback, private, or reserved IP, the check fails with `HealthCheckSSRFError`. This mitigates DNS rebinding and internal hostnames that resolve to private IPs.
- **Localhost names:** The strings `localhost`, `localhost.`, `localhost6`, `localhost6.localdomain6` are rejected when `block_private_hosts=True` (whether or not they resolve).

## Edge cases

- **Empty or missing host:** URLs with no host (e.g. scheme-only or path-only) may pass scheme checks; validation skips host checks when host is empty.
- **Hostname vs IP:** Literal IPs are checked at init; hostnames are checked after resolution in `validate_host_ssrf_async`. Resolution is done at request time, so DNS changes between init and request are reflected.
- **Resolution failure:** If DNS resolution fails in `validate_host_ssrf_async`, the function returns without raising (the subsequent request may then fail). This avoids treating transient resolution errors as SSRF.

## API

- **validate_url_ssrf** (`fast_healthchecks.utils`): Validates scheme and, when `block_private_hosts=True`, rejects literal loopback/private IPs and localhost-like host names.
- **validate_host_ssrf_async** (`fast_healthchecks.utils`): Resolves the host and rejects if any resolved IP is loopback, private, or reserved. Used by `UrlHealthCheck` when `block_private_hosts=True` before each request.
- **HealthCheckSSRFError**: Raised when validation fails. See [API reference](api.md).
