# Native Windows qualification (W1–W4) for the restricted Stage A/B alpha

The steps below run **on a real Windows machine**. A Linux run of these scripts reports NO-GO
and is not Windows qualification. The scripts change nothing outside the development directory
you name. They never use `setx`, the registry (beyond read-only checks), global `pip` installs
or elevation.

## What the cross-platform code now does (W0, tested on Linux)

| Hazard | Behaviour now |
|---|---|
| Server environment | Built by `hostenv.minimal_os_env`. On Windows it contains `SYSTEMROOT`/`WINDIR` (Python sockets and asyncio need them), a `PATH` of the system directories, `PATHEXT` and a private `TEMP`/`TMP`. Nothing else is inherited from the host. |
| Private directories and files | POSIX uses mode bits plus an owner check. NTFS uses `icacls`: inheritance is removed, and only the current user and SYSTEM have full control. The result is read back as SDDL and verified. Verification failure stops the pilot. |
| Store root (`bridge.HostConfig`) | On Windows, only a drive-letter path on a **fixed local drive** is accepted. Refused: UNC shares, `\\?\` paths, mapped network, removable or unknown drives, alternate data streams, reserved device names, and names ending in a dot or space. Any junction, symlink or other reparse point in the path is refused, as before. An ancestor that cannot be inspected is a configuration error. |
| Correction record | The record file and every ancestor must be free of symlinks, junctions and reparse points. |
| Agent CLI | `claude` is resolved through `PATH`/`PATHEXT`. The prompt goes in on stdin and the contract from a file, so no free text reaches `cmd.exe` when the CLI is a `claude.cmd` launcher. Arguments containing cmd metacharacters are refused. |
| Server exit | After every pilot session, the harness waits up to 15 s for every `server.py` process to exit. If processes cannot be listed, or one remains, the pilot stops. The alpha workflow counts an unavailable process listing as a failed check. |
| Text | Agent output is decoded as UTF-8, not the console code page. Receipts redact Windows paths in both separator forms, case-insensitively. |

## W1: preflight (stop on NO-GO)

1. Use a normal, non-elevated PowerShell. Create an empty development directory on a fixed local
   NTFS drive, outside OneDrive and away from any stable Agent Memory installation or data, for
   example `D:\am-win-dev`.
2. Clone the branch into it: `git clone --branch product/mcp-ab-agent-pilot-no-ci <repo> D:\am-win-dev\agent-memory`.
3. Recommended: keep the pilot agent's Claude Code configuration separate.

       $env:CLAUDE_CONFIG_DIR = "D:\am-win-dev\claude-config"
       claude

   This sets the variable for the current shell only. Log in once in that window, then close it.
4. Run the preflight with any installed Python 3.11 or later:

       py -3.12 D:\am-win-dev\agent-memory\integrations\agent-memory-mcp\windows\preflight.py `
         --dev-dir D:\am-win-dev --claude-config-dir D:\am-win-dev\claude-config [--stable-path <stable install or data>]

   It checks all ten required properties and writes `preflight.json`. **Any FAIL is NO-GO: stop
   there and report the failing property.**

## W2 + W3: runtime qualification and real-agent pilot

    py -3.12 D:\am-win-dev\agent-memory\integrations\agent-memory-mcp\windows\qualify.py `
      --dev-dir D:\am-win-dev --python 3.11 --python 3.12

For each Python version, the runner does the following:
1. Creates a separate `venv-<version>` inside the development directory and installs only the
   clone and `mcp==2.3.0`.
2. Runs, with `AGENT_MEMORY_*` removed and a private TEMP:
   - the MCP suites, including the native NTFS junction, symlink and ACL negatives in
     `tests/test_windows_native.py` (**any skip there is not a pass**);
   - the public-facade lifecycle tests;
   - the Stage A/B alpha workflow;
   - the 16-session real-agent pilot.
3. Re-checks the preflight baseline. The base interpreters' packages, the user and machine
   environment variables, and the default Claude Code configuration must all be unchanged.

The support-model variable is never set. No Stage C code path is enabled.

## W4: evidence

The runner writes redacted evidence to
`reports/validation/mcp-windows-qualification/py<version>-<head>/`: `summary.json` with the
decision and every step, logs, pilot receipts and the redacted preflight. Before committing it
with `[skip ci]`:
- review the receipts;
- check the S06 receipt for the attribution defect (a derived conclusion under "From memory").

**GO FOR RESTRICTED WINDOWS INTERNAL ALPHA** requires both Python versions to be GO, a GO
preflight, and no skipped native security test. Anything else is NO-GO, with the failing step
named in `summary.json`.

## Known gaps to watch on the first native run

- **Python launcher:** a Microsoft Store Python, or an app-execution alias for `python`, is not a
  supported base interpreter. Use python.org installs, found by `py -0p`.
- **Symlink capability:** symlink creation needs Developer Mode or the symlink privilege. Without
  it, those tests skip as "capability unavailable" and the run is NO-GO. Junction tests need no
  privilege.
- **Local security software:** antivirus or indexing can hold the SQLite file briefly after a
  server exits. The alpha workflow records `temp_store_removed`; the pilot leaves its run
  directory for inspection.
- **Claude Code on Windows:** the MCP server launch has not yet been observed for stdout
  contamination or for how the CLI merges the server environment. The pilot's discovery and
  persistence checks are the evidence for that.
