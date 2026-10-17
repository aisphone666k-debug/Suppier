# Handoff Note - 2026-09-30

## Diagnostic Summary: Main.py Startup Diagnostics & Web Server Lifecycle

### 1. Root Cause Analysis
- **Symptom**: User reported that running `uv run python main.py` appeared to freeze/hang and never finished.
- **Root Cause**:
  1. Cold start DLL scan: FastEmbed imports `onnxruntime` native libraries (`onnxruntime.dll` 18.4 MB and `onnxruntime_pybind11_state.pyd` 19.1 MB), which takes ~24.8 seconds on Windows during first load while Windows Defender scans native code.
  2. Silent initialization: `create_app()` was previously run at module level with zero console feedback, giving the perception of a stuck terminal.
  3. Web server lifecycle: `main.py` is an HTTP server (Uvicorn) that intentionally runs indefinitely listening for incoming web requests on port 8000; it does not exit back to the terminal prompt.

### 2. Changes Made
- `main.py`: Added explicit unbuffered status output (`flush=True`) at the very start of the script so users immediately know models are loading. Added explicit notice stating the web app is running at `http://localhost:8000` and can be stopped with `Ctrl+C`.
- `docs/NOTES.md`: Appended Section 7 documenting the full 10-point RCA and verification benchmarks.

### 3. Verification & Test Proof (Rule 10 & 16)
- Benchmarked `create_app()`: completes in ~5.14s once warm.
- Unit and Integration Tests: 86/86 passed cleanly (`uv run pytest tests/unit tests/integration`).
- E2E Playwright test runner verified (requires `playwright install chromium` if headless browser testing is desired).

### 4. Next Steps
- User can run `uv run python main.py` and access the application at `http://localhost:8000`.
