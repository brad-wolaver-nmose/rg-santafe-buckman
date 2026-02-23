# IS-05: MODFLOW Execution Wrapper

> **Tier 2 Implementation Specification** — A complete Claude Code session-sized prompt. Paste into a fresh session with Tier 1 domain docs available to get a working module back. Sequentially ordered with explicit dependencies.

**Status:** Final
**Author:** Claude Code (Anthropic)
**Created:** 2026-02-20
**Last Updated:** 2026-02-20

---

## 1. Session Goal

Implement `step3_run_modflow.sh` — a bash script that wraps MODFLOW96 execution via Wine with enhanced logging, timing, and automatic post-run verification.

---

## 2. Prerequisites

### Prior Specs (must be complete)
- IS-04: MODFLOW Input Update (`step2_update_modflow.py` must have generated `output/modflow/{year}/CY{year}.nam` and all referenced input files)

### Input Files (must exist)
| File | Path | Description |
|------|------|-------------|
| NAM file | `output/modflow/{year}/CY{year}.nam` | MODFLOW name file listing all input/output file paths |
| MODFLOW96 exe | `output/modflow/{year}/modflow96.exe` | MODFLOW96 executable (Win32, runs via Wine) |
| Verification script | `output/modflow/{year}/verify_modflow_run.py` | Post-run convergence/output checker (optional) |

### Domain Knowledge
- See DS-03 for MODFLOW model structure and stress period configuration
- MODFLOW96 is a legacy Fortran groundwater model (McDonald & Harbaugh, 1988)
- Runs under Wine on Linux/WSL because it is a 32-bit Windows executable

---

## 3. Context for Claude Code

MODFLOW96 is a finite-difference groundwater flow simulator. It reads a "name file" (`.nam`) that lists all input packages (well pumping, river boundaries, GHB boundaries, etc.) and output file paths. The model solves the groundwater flow equation iteratively for each stress period (month).

For the Buckman model:
- **50 stress periods** = 50 months of simulation (varying by year configuration)
- **Runtime:** 30-45 minutes on typical hardware
- **Input method:** MODFLOW96 reads the NAM filename from **stdin** (not command-line argument)
- **Output:** Binary flux files (`CY{year}_riv.flx`, `CY{year}_ghb.flx`) consumed by the FORTRAN post-processor in Step 4

### Key Equations (Inline)

```
Runtime reporting:
  RUNTIME = END_TIME - START_TIME (epoch seconds)
  MINUTES = RUNTIME / 60
  SECONDS = RUNTIME % 60
```

### Key Constants (Inline)

| Constant | Value | Units |
|----------|-------|-------|
| Typical runtime | 30-45 | minutes |
| Exit code success | 0 | - |
| NAM file pattern | `CY{YEAR}.nam` | - |
| Log file pattern | `{YEAR}_modflow_run.log` | - |

---

## 4. Requirements (Numbered, Testable)

| Req | Description | Acceptance Criterion |
|-----|-------------|---------------------|
| R1 | Parse `--year YYYY` argument (required), validate is numeric | `./step3_run_modflow.sh` without `--year` prints usage and exits 1; `./step3_run_modflow.sh --year abc` prints error about non-numeric value and exits 1 |
| R2 | Support `-h`/`--help` flag showing usage, description, and what the script does | `./step3_run_modflow.sh --help` prints help text and exits 0 |
| R3 | Check prerequisite: `output/modflow/{year}/` directory exists | Missing directory prints error with hint to run step2 first, exits 1 |
| R4 | Check prerequisite: Wine is installed (`command -v wine`) | Missing Wine prints install instructions, exits 1 |
| R5 | Check prerequisite: `CY{year}.nam` file exists in MODFLOW directory | Missing NAM file prints error with expected location, exits 1 |
| R6 | Execute MODFLOW96: `echo "CY{year}.nam" \| wine ./modflow96.exe` piping NAM filename to stdin | MODFLOW96 receives filename and begins solving |
| R7 | Capture all output to `{year}_modflow_run.log` using `tee` (stdout visible in real-time AND logged) | Log file created with MODFLOW output; user sees convergence info in terminal |
| R8 | Track runtime using epoch seconds (`date +%s` before and after), report minutes/seconds | Summary shows runtime in `Xm Ys` format |
| R9 | Check exit code via `${PIPESTATUS[1]}` (Wine/MODFLOW exit code from 3-command pipe). **Known Bug:** Both this spec and `step3_run_modflow.sh` (line 117) incorrectly use `PIPESTATUS[0]`, which captures `echo`'s exit code (always 0) instead of `wine`'s exit code. See Section 8 warning for details. | Non-zero exit code from MODFLOW reported as failure; script exits with that code |
| R10 | Auto-run `verify_modflow_run.py` if present; skip with warning if absent | Verification runs after successful MODFLOW completion; missing script produces warning, not error |
| R11 | Report next step: `python3 step4_generate_depletion_tables.py --year {YEAR}` | Success message includes exact command for next pipeline step |
| R12 | Use `set -euo pipefail` for strict error handling | Script fails fast on undefined variables, command errors, or pipe failures |

---

## 5. Worked Example

### Input

```bash
./step3_run_modflow.sh --year 2025
```

Working directory: project root (`/home/user/projects/rg/santafe/buckman/`)

### Execution Flow

```
Step 1: Parse arguments
  --year 2025 → YEAR="2025"
  Validate: "2025" =~ ^[0-9]+$ → passes

Step 2: Check prerequisites
  [[ -d "output/modflow/2025" ]] → true
  command -v wine → /usr/bin/wine (exists)
  cd output/modflow/2025/
  [[ -f "CY2025.nam" ]] → true

Step 3: Print banner
  "MODFLOW96 Execution - Year 2025"
  "Started: Fri Feb 20 10:30:00 MST 2026"

Step 4: Run MODFLOW96
  START_TIME=$(date +%s) → 1740069000
  echo "CY2025.nam" | wine ./modflow96.exe 2>&1 | tee "2025_modflow_run.log"
  EXIT_CODE=${PIPESTATUS[0]} → 0 (BUG: captures echo's exit code, not wine's; see Section 8)
  END_TIME=$(date +%s) → 1740071400
  RUNTIME = 1740071400 - 1740069000 = 2400 seconds

Step 5: Report runtime
  2400 / 60 = 40 minutes
  2400 % 60 = 0 seconds
  "Runtime: 40 minutes 0 seconds"

Step 6: Check exit code
  EXIT_CODE=0 → "MODFLOW96 completed successfully"

Step 7: Run verification
  python3 verify_modflow_run.py → exit 0
  "All checks passed!"

Step 8: Report next step
  "cd ../../.."
  "python3 step4_generate_depletion_tables.py --year 2025"
```

### Expected Output

```
==============================================================
MODFLOW96 Execution - Year 2025
Started: Fri Feb 20 10:30:00 MST 2026
==============================================================

Working directory: /home/user/projects/rg/santafe/buckman/output/modflow/2025

NAM file: CY2025.nam
Executable: modflow96.exe

Running MODFLOW96 (this will take 30-45 minutes)...
You can watch convergence behavior in real-time.
Press Ctrl+C to abort if you see problems.

--------------------------------------------------------------
[... 30-45 minutes of MODFLOW convergence output ...]
--------------------------------------------------------------

==============================================================
MODFLOW96 Execution Complete
Runtime: 40 minutes 0 seconds
Exit code: 0
==============================================================

MODFLOW96 completed successfully

Running post-execution verification...
[... verification output ...]

==============================================================
SUMMARY
==============================================================
MODFLOW runtime: 40m 0s
Log file: 2025_modflow_run.log

All checks passed!

Next Step:
  cd ../../..
  python3 step4_generate_depletion_tables.py --year 2025
```

---

## 6. Files to Create/Modify

| Action | Path | Description |
|--------|------|-------------|
| Create | `step3_run_modflow.sh` | Bash script wrapping MODFLOW96 execution via Wine |

---

## 7. Acceptance Criteria

```bash
# These commands must all pass:

# 1. Script is executable
test -x step3_run_modflow.sh

# 2. Help flag works
./step3_run_modflow.sh --help

# 3. Missing --year produces error
./step3_run_modflow.sh 2>&1 | grep -q "ERROR.*--year is required"

# 4. Non-numeric year produces error
./step3_run_modflow.sh --year abc 2>&1 | grep -q "ERROR.*must be a number"

# 5. Unknown option produces error
./step3_run_modflow.sh --foo 2>&1 | grep -q "ERROR.*Unknown option"

# 6. Shellcheck passes (if installed)
shellcheck step3_run_modflow.sh
```

Expected output: All checks exit 0 (help text displayed, errors captured correctly).

Note: Full execution testing requires Wine + MODFLOW96 + prepared model files, which takes 30-45 minutes. Dry-run testing validates argument parsing and prerequisite checks.

---

## 8. Known Gotchas

- [ ] **WARNING -- PIPESTATUS[0] bug (spec and code):** The command pipe is `echo "$NAM_FILE" | wine ./modflow96.exe 2>&1 | tee ...`. In this 3-command pipe, `PIPESTATUS[0]` captures `echo`'s exit code (always 0), `PIPESTATUS[1]` captures `wine`'s exit code (the desired one), and `PIPESTATUS[2]` captures `tee`'s exit code. Both this spec and the code (`step3_run_modflow.sh` line 117) incorrectly use `PIPESTATUS[0]`, meaning MODFLOW failures would never be detected via the PIPESTATUS check. The correct index is `PIPESTATUS[1]`. However, with `set -e` and `pipefail`, the script would still exit on wine failure before reaching the PIPESTATUS line.
- [ ] **PIPESTATUS must be read immediately** — `${PIPESTATUS[...]}` must be captured on the very next line after the pipe. Any intervening command between the pipe and the PIPESTATUS read will overwrite it.
- [ ] **`set -euo pipefail` and pipes** — With `pipefail`, the pipe returns the exit code of the last non-zero command. PIPESTATUS gives element-by-element access: `[0]` = echo, `[1]` = wine, `[2]` = tee. The correct element for Wine's exit code is `PIPESTATUS[1]`.
- [ ] **Wine stderr** — Wine may produce its own diagnostic messages on stderr (e.g., "fixme: ..." warnings). These are piped via `2>&1` and will appear in the log file. This is intentional for debugging.
- [ ] **Working directory** — The script `cd`s into `output/modflow/{year}/` and stays there. The verify script runs from that directory. The "next step" instructions tell the user to `cd ../../..` back to the project root.
- [ ] **30-45 minute runtime** — This is a long-running process. The `tee` ensures the user can watch convergence in real-time. Ctrl+C will abort. There is no timeout; the modeler is expected to monitor convergence.
- [ ] **MODFLOW96 stdin** — MODFLOW96 reads the NAM filename from stdin, NOT from a command-line argument. This is why we use `echo "CY{year}.nam" | wine ./modflow96.exe` instead of passing it as an argument.

---

## 9. Year-Chaining Behavior

| Data Element | Source for Year N | Source for Year N+1 |
|-------------|-------------------|---------------------|
| NAM file | `output/modflow/N/CYN.nam` (from step2) | `output/modflow/N+1/CY{N+1}.nam` (from step2) |
| MODFLOW exe | Same `modflow96.exe` (copied by step2) | Same `modflow96.exe` (copied by step2) |
| Output flux files | Generated by this step: `CYN_riv.flx`, `CYN_ghb.flx` | Generated by this step: `CY{N+1}_riv.flx`, `CY{N+1}_ghb.flx` |

No chaining between years at this step. Each year's MODFLOW run is fully independent given the input files from step2.

---

## 10. Verification

Single command to confirm the module works end-to-end:

```bash
# Dry-run test (no Wine/MODFLOW needed):
./step3_run_modflow.sh --year 9999 2>&1 | head -20
# Expected: "ERROR: Directory not found: output/modflow/9999"

# Full test (requires Wine + prepared model):
./step3_run_modflow.sh --year 2025
# Expected: 30-45 min runtime, log file created, verification passes
```

Expected result: Dry-run exits 1 with directory-not-found error. Full run creates `{year}_modflow_run.log` and reports success.

---

## 11. Cross-References

| Related Spec | Relationship |
|-------------|-------------|
| DS-03 | MODFLOW model structure, stress periods, boundary packages |
| IS-04 | Upstream dependency: generates MODFLOW input files and directory structure |
| IS-06 | Downstream dependency: post-processor reads flux files generated by this step |
