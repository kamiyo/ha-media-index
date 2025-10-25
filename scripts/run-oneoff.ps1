<#
    run-oneoff.ps1

    Purpose:
    - A single, reusable PowerShell script that the assistant will overwrite for one-off commands
      (queries, log fetches, quick checks) so the user only needs to approve running this file once.

    Usage pattern (assistant):
    1. Overwrite this file with the exact one-off command(s) to run.
    2. Save the file and notify the user (or run it if pre-approved).
    3. When executed, the script should return exit code 0 on success and non-zero on failure.

    Security:
    - Do NOT place secrets in this file. Use environment variables or secure stores instead.
    - This file is intended to be overwritten by the assistant and run as a single-step helper.
#>

param()

Set-StrictMode -Version Latest

Write-Output "run-oneoff: starting"

# ---- ONE-OFF COMMAND GOES HERE (assistant will overwrite this file before running) ----

Write-Output "run-oneoff: no-op (no commands written)"

# ---- END ---------------------------------------------------------------------------

Write-Output "run-oneoff: complete"
exit 0
