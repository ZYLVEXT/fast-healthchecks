# URL check and SSRF protection

**Use only trusted URLs from application configuration.** Do not pass user-controlled input to `UrlHealthCheck` or to `validate_url_ssrf` / `validate_host_ssrf_async`; otherwise you risk SSRF and DNS rebinding.

## Behaviour

- **Schemes:** Only `http` and `https` are allowed by default. Validation is done by `validate_url_ssrf` (and by `UrlHealthCheck` at construction). Custom schemes are not permitted for the URL check.
- **Hostname:** Every URL must include a hostname.
- **block_private_hosts:** When `True`:
  - **At construction:** The URL host (if it is a literal IP) is checked; any non-global address is rejected. Hostnames are not resolved at construction time.
  - **At run time:** An HTTPX request hook validates and resolves the destination immediately before every outbound request, including redirect targets. If a hostname resolves to any non-global IP, the check fails with `HealthCheckSSRFError` before that request is sent.
- **Localhost names:** The strings `localhost`, `localhost.`, `localhost6`, `localhost6.localdomain6` are rejected when `block_private_hosts=True` (whether or not they resolve).

## Edge cases

- **Empty or missing host:** URLs with no host are rejected during construction.
- **Hostname vs IP:** Literal IPs are checked at init; hostnames are checked after resolution in `validate_host_ssrf_async`. Resolution is done at request time, so DNS changes between init and request are reflected.
- **Resolution failure:** DNS resolution failures are rejected before the request. With `block_private_hosts=True`, validation fails closed.
- **DNS rebinding:** HTTPX/httpcore performs its own DNS lookup when opening the connection, after the validation lookup. The request hook narrows this time-of-check/time-of-use window but cannot eliminate it. Treat `block_private_hosts` as defense in depth, keep URLs under trusted configuration, and enforce network-level egress restrictions when private-address access must be impossible.

## API

- **validate_url_ssrf** (`fast_healthchecks.utils`): Validates the scheme and hostname and, when `block_private_hosts=True`, rejects literal non-global IPs and localhost-like host names.
- **validate_host_ssrf_async** (`fast_healthchecks.utils`): Resolves the host and rejects resolution failures or any non-global IP. Used by `UrlHealthCheck` when `block_private_hosts=True` for every initial or redirected request.
- **HealthCheckSSRFError**: Raised when validation fails. See [API reference](api.md).
