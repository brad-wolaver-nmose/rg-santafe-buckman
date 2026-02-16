#!/usr/bin/env python3
"""
Stream Depletion Tables from MODFLOW Post-Processor

This script processes MODFLOW binary output files (CY{year}_ghb.flx and CY{year}_riv.flx)
using the sfmodflx_2245 post-processor to generate stream depletion tables for the
Buckman Well Field annual report.

Scientific Basis:
- Superposition model: MODFLOW calculates depletions from 1988-{year} pumping
- Analytical residuals: Core (2003) provides pre-1988 pumping effects
- Unit conversion: cfs × days × 86400 / 43560 = acre-feet

Year-agnostic: Pass --year to process any year (default: 2024).
"""

import shutil
import subprocess
import sys
from pathlib import Path


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Output directory for generated XLSX tables
OUTPUT_DIR: str = "./output/depletion/"

# Validation directory
VALIDATION_DIR: str = "./validation/"

# Default processing year
DEFAULT_YEAR: int = 2024


# =============================================================================
# YEAR-PARAMETERIZED PATH FUNCTIONS
# =============================================================================

def get_modflow_output_dir(year: int) -> str:
    """Return MODFLOW output directory for given year.

    Directory structure:
    - 2024 and earlier: output/modflow/{year}/modflow/ (legacy nested)
    - 2025 and later: output/modflow/{year}/ (flat, new standard)
    """
    if year <= 2024:
        return f"./output/modflow/{year}/modflow/"
    return f"./output/modflow/{year}/"


def get_depletions_dir(year: int) -> str:
    """Return post-processor working directory for given year.

    Directory structure:
    - 2024 and earlier: output/modflow/{year}/depletions/ (legacy nested)
    - 2025 and later: output/modflow/{year}/ (flat, new standard)
    """
    if year <= 2024:
        return f"./output/modflow/{year}/depletions/"
    return f"./output/modflow/{year}/"


def get_flux_files(year: int) -> tuple[str, str]:
    """Return (riv_flux_file, ghb_flux_file) for given year."""
    return f"CY{year}_riv.flx", f"CY{year}_ghb.flx"


def get_output_file_prefix(year: int) -> str:
    """Return output file prefix for given year."""
    return f"CY{year}"


# Legacy constants for backward compatibility (used if year not passed)
YEAR: int = DEFAULT_YEAR
MODFLOW_OUTPUT_DIR: str = get_modflow_output_dir(DEFAULT_YEAR)
DEPLETIONS_DIR: str = get_depletions_dir(DEFAULT_YEAR)
RIV_FLUX_FILE: str = get_flux_files(DEFAULT_YEAR)[0]
GHB_FLUX_FILE: str = get_flux_files(DEFAULT_YEAR)[1]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def print_error(what_failed: str, location: str, actual: str, expected: str, context: str) -> None:
    """
    Print forensic-quality error message following CLAUDE.md standards.

    Prints error information in a structured 5-element format for debugging.

    Args:
        what_failed: Description of what operation failed
        location: Where the failure occurred (file path, function name, etc.)
        actual: The actual value that was encountered
        expected: The expected value or condition
        context: Physical interpretation or additional context
    """
    print(f"ERROR: {what_failed}")
    print(f"  Location: {location}")
    print(f"  Actual: {actual}")
    print(f"  Expected: {expected}")
    print(f"  Physical context: {context}")


# =============================================================================
# US-001: Copy Flux Files to Post-Processor Directory
# =============================================================================

def copy_flux_files(year: int | None = None) -> bool:
    """
    Copy MODFLOW flux files to the post-processor directory.

    Scientific Basis:
    - sfmodflx_2245.exe reads flux files from its working directory
    - Flux files contain monthly boundary condition flows (river and GHB)
    - Files must be accessible to post-processor for depletion calculation

    Assumptions:
    1. Source flux files exist in MODFLOW output directory for the year
    2. Destination directory (depletions dir) exists
    3. Post-processor sfmodflx_2245.exe is in depletions directory

    Args:
        year: Processing year. If None, uses DEFAULT_YEAR.

    Returns:
        True if both files copied successfully, False otherwise

    Raises:
        None - prints forensic error messages and returns False on failure

    Example:
        >>> success = copy_flux_files(2024)
        Copying flux files to post-processor directory...
          CY2024_riv.flx: 31484640 bytes -> output/modflow/2024/depletions/
          CY2024_ghb.flx: 31484640 bytes -> output/modflow/2024/depletions/
        Flux files copied successfully.
        >>> success
        True
    """
    if year is None:
        year = DEFAULT_YEAR

    print(f"Copying flux files to post-processor directory for year {year}...")

    source_dir = Path(get_modflow_output_dir(year))
    dest_dir = Path(get_depletions_dir(year))
    riv_flux_file, ghb_flux_file = get_flux_files(year)

    # List of files to copy: (filename, description)
    flux_files = [
        (riv_flux_file, "river boundary flux"),
        (ghb_flux_file, "general head boundary flux"),
    ]

    # Check source directory exists
    if not source_dir.exists():
        print_error(
            "Source directory not found",
            str(source_dir.resolve()),
            "Directory does not exist",
            "Directory containing MODFLOW flux output files",
            "MODFLOW model must be run first to generate flux files"
        )
        return False

    # Check destination directory exists
    if not dest_dir.exists():
        print_error(
            "Destination directory not found",
            str(dest_dir.resolve()),
            "Directory does not exist",
            "Directory containing sfmodflx_2245.exe post-processor",
            "Post-processor directory must be set up before copying files"
        )
        return False

    # Check if source and destination are the same directory (flat structure)
    same_dir = source_dir.resolve() == dest_dir.resolve()
    if same_dir:
        print("  Source and destination are same directory (flat structure)")

    # Copy each flux file
    for filename, description in flux_files:
        source_path = source_dir / filename
        dest_path = dest_dir / filename

        # Check source file exists
        if not source_path.exists():
            print_error(
                f"Source flux file not found",
                str(source_path.resolve()),
                "File does not exist",
                f"{description} file from MODFLOW run",
                f"MODFLOW must generate {filename} before post-processing"
            )
            return False

        # Skip copy if same directory (file already in place)
        if same_dir:
            file_size = source_path.stat().st_size
            print(f"  {filename}: {file_size:,} bytes (already in place)")
            continue

        # Copy file
        try:
            shutil.copy2(source_path, dest_path)
            file_size = dest_path.stat().st_size
            print(f"  {filename}: {file_size:,} bytes -> {dest_dir}/")
        except OSError as e:
            print_error(
                f"Failed to copy flux file",
                str(source_path.resolve()),
                f"OS error: {e}",
                f"Successful copy to {dest_dir}",
                f"Check file permissions and disk space"
            )
            return False

    # Verify both files exist after copy
    for filename, description in flux_files:
        dest_path = dest_dir / filename
        if not dest_path.exists():
            print_error(
                "Flux file missing after copy",
                str(dest_path.resolve()),
                "File does not exist",
                "File should exist after shutil.copy2()",
                "Filesystem error - file may have been deleted"
            )
            return False

    print("Flux files copied successfully.")
    return True


# =============================================================================
# US-002: Run Post-Processor via Wine
# =============================================================================

# Post-processor executable name
POST_PROCESSOR_EXE: str = "sfmodflx_2245.exe"

# Legacy output filename prefix (for backward compatibility)
OUTPUT_FILE_PREFIX: str = get_output_file_prefix(DEFAULT_YEAR)


def check_wine_installed() -> bool:
    """
    Check if Wine is installed on the system.

    Returns:
        True if Wine is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["wine", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  Wine version: {result.stdout.strip()}")
            return True
        return False
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        return False


def run_post_processor(year: int | None = None) -> bool:
    """
    Execute sfmodflx_2245.exe via Wine with automated input.

    Scientific Basis:
    - sfmodflx_2245 is a Fortran-based post-processor for MODFLOW flux files
    - It reads river (RIV) and general head boundary (GHB) flux files
    - Calculates stream depletions by summing boundary condition flows
    - Output file contains monthly cfs values for each model cell and stream

    Assumptions:
    1. Wine is installed and functional
    2. sfmodflx_2245.exe exists in depletions directory
    3. Flux files (CY{year}_riv.flx, CY{year}_ghb.flx) are in depletions directory
    4. Post-processor expects three stdin inputs: riv_file, ghb_file, output_prefix

    Args:
        year: Processing year. If None, uses DEFAULT_YEAR.

    Returns:
        True if post-processor ran successfully, False otherwise

    Raises:
        None - prints forensic error messages and returns False on failure

    Example:
        >>> success = run_post_processor(2024)
        Running post-processor via Wine...
          Command: wine sfmodflx_2245.exe
          Working directory: output/modflow/2024/depletions/
          Inputs: CY2024_riv.flx, CY2024_ghb.flx, CY2024
        Post-processor completed successfully.
          Output file: CY2024 (1234567 bytes)
        >>> success
        True
    """
    if year is None:
        year = DEFAULT_YEAR

    print(f"Running post-processor via Wine for year {year}...")

    # Check if Wine is installed
    print("  Checking Wine installation...")
    if not check_wine_installed():
        print_error(
            "Wine is not installed",
            "System PATH",
            "wine command not found",
            "Wine installed and accessible via PATH",
            "Install Wine with: sudo apt-get install wine"
        )
        print("\n  Installation instructions:")
        print("    Ubuntu/Debian: sudo apt-get install wine")
        print("    Fedora: sudo dnf install wine")
        print("    macOS: brew install wine-stable")
        return False

    depletions_dir = Path(get_depletions_dir(year))
    riv_flux_file, ghb_flux_file = get_flux_files(year)
    output_file_prefix = get_output_file_prefix(year)

    # Check post-processor executable exists
    exe_path = depletions_dir / POST_PROCESSOR_EXE
    if not exe_path.exists():
        print_error(
            "Post-processor executable not found",
            str(exe_path.resolve()),
            "File does not exist",
            f"{POST_PROCESSOR_EXE} in depletions directory",
            "Post-processor must be placed in depletions directory before running"
        )
        return False

    # Check flux files exist in depletions directory
    riv_path = depletions_dir / riv_flux_file
    ghb_path = depletions_dir / ghb_flux_file

    if not riv_path.exists():
        print_error(
            "RIV flux file not found in depletions directory",
            str(riv_path.resolve()),
            "File does not exist",
            f"{riv_flux_file} copied to depletions directory",
            "Run copy_flux_files() before run_post_processor()"
        )
        return False

    if not ghb_path.exists():
        print_error(
            "GHB flux file not found in depletions directory",
            str(ghb_path.resolve()),
            "File does not exist",
            f"{ghb_flux_file} copied to depletions directory",
            "Run copy_flux_files() before run_post_processor()"
        )
        return False

    # Prepare stdin input for post-processor
    # Format: three lines - riv file, ghb file, output prefix
    stdin_input = f"{riv_flux_file}\n{ghb_flux_file}\n{output_file_prefix}\n"

    print(f"  Command: wine {POST_PROCESSOR_EXE}")
    print(f"  Working directory: {depletions_dir}/")
    print(f"  Inputs: {riv_flux_file}, {ghb_flux_file}, {output_file_prefix}")

    # Run the post-processor
    # Use ./ prefix to ensure Wine runs the local exe, not a system path
    try:
        result = subprocess.run(
            ["wine", f"./{POST_PROCESSOR_EXE}"],
            input=stdin_input,
            capture_output=True,
            text=True,
            cwd=str(depletions_dir.resolve()),
            timeout=300  # 5 minute timeout
        )

        # Check for errors
        if result.returncode != 0:
            print_error(
                "Post-processor failed",
                f"wine {POST_PROCESSOR_EXE}",
                f"Exit code: {result.returncode}",
                "Exit code: 0",
                "Post-processor encountered an error during execution"
            )
            print(f"\n  stdout:\n{result.stdout}")
            print(f"\n  stderr:\n{result.stderr}")
            return False

        # Verify output file was created
        output_path = depletions_dir / output_file_prefix
        if not output_path.exists():
            print_error(
                "Post-processor output file not created",
                str(output_path.resolve()),
                "File does not exist",
                f"{output_file_prefix} created by post-processor",
                "Post-processor may have failed silently or used different output path"
            )
            print(f"\n  stdout:\n{result.stdout}")
            print(f"\n  stderr:\n{result.stderr}")
            return False

        output_size = output_path.stat().st_size
        print(f"Post-processor completed successfully.")
        print(f"  Output file: {output_file_prefix} ({output_size:,} bytes)")

        return True

    except subprocess.TimeoutExpired:
        print_error(
            "Post-processor timed out",
            f"wine {POST_PROCESSOR_EXE}",
            "Exceeded 300 second timeout",
            "Completion within timeout",
            "Post-processor may be stuck or processing very large files"
        )
        return False
    except OSError as e:
        print_error(
            "Failed to execute post-processor",
            f"wine {POST_PROCESSOR_EXE}",
            f"OS error: {e}",
            "Successful Wine execution",
            "Check Wine installation and file permissions"
        )
        return False


# =============================================================================
# US-003: Parse Post-Processor Output Structure
# =============================================================================

# Type alias for parsed data: {year: {identifier: {month: value_cfs}}}
# identifier is either "LAY_ROW_COL" (e.g., "1_9_14") or stream name (e.g., "R POJOAQUE")
ParsedData = dict[int, dict[str, dict[str, float]]]

# Month names in output file order
MONTH_NAMES: list[str] = ["jan", "feb", "mar", "apr", "may", "jun",
                          "jul", "aug", "sep", "oct", "nov", "dec"]


def parse_post_processor_output(
    file_path: str | None = None,
    year: int | None = None
) -> ParsedData:
    """
    Parse the sfmodflx_2245 post-processor output file.

    Scientific Basis:
    - sfmodflx_2245 outputs monthly cfs values for each model cell and stream
    - Data is organized by year blocks starting with "YEAR: NNNN"
    - Cell rows have format "LAY ROW COL" followed by 12 monthly values
    - Stream summary rows have format "0  STREAM_NAME" followed by 12 monthly values

    Assumptions:
    1. File follows standard sfmodflx_2245 output format
    2. Year blocks are separated by header lines starting with "1 PUMPAGE EFFECT"
    3. All 12 months are present for each cell/stream in each year
    4. Values are in cubic feet per second (cfs)

    Args:
        file_path: Path to post-processor output file. If None, constructs from year.
        year: Processing year for default path construction. If None, uses DEFAULT_YEAR.

    Returns:
        Nested dict: {year: {identifier: {month: value_cfs}}}
        - year: Integer year (1988, 1989, ..., 2024, ...)
        - identifier: Cell key "LAY ROW COL" (space-separated) or stream name
        - month: Three-letter lowercase month name
        - value_cfs: Flow in cubic feet per second

    Raises:
        None - prints forensic error messages and returns empty dict on failure

    Example:
        >>> data = parse_post_processor_output(year=2024)
        Parsing post-processor output...
          File: output/modflow/2024/depletions/CY2024
          Years parsed: 37 (1988-2024)
          Sample 2024 R POJOAQUE jan: 0.083581 cfs
        >>> data[2024]["R POJOAQUE"]["jan"]
        0.083581
    """
    from pathlib import Path
    import re

    if year is None:
        year = DEFAULT_YEAR

    if file_path is None:
        file_path = str(Path(get_depletions_dir(year)) / get_output_file_prefix(year))

    print("Parsing post-processor output...")

    path = Path(file_path)
    if not path.exists():
        print_error(
            "Post-processor output file not found",
            str(path.resolve()),
            "File does not exist",
            "Output file from sfmodflx_2245.exe",
            "Run post-processor before parsing output"
        )
        return {}

    # Read file content
    try:
        content = path.read_text()
    except OSError as e:
        print_error(
            "Failed to read post-processor output file",
            str(path.resolve()),
            f"OS error: {e}",
            "Successfully read file",
            "Check file permissions"
        )
        return {}

    print(f"  File: {file_path}")

    # Parse the content
    parsed_data: ParsedData = {}
    current_year: int | None = None

    # Pattern for year header: "YEAR: NNNN"
    year_pattern = re.compile(r"YEAR:\s+(\d{4})")

    # Pattern for cell row: "    LAY ROW COL  val val val..."
    # Cell rows start with spaces, then 3 integers
    cell_pattern = re.compile(r"^\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.\s-]+)$")

    # Pattern for stream summary row: "0  STREAM_NAME  val val val..."
    # Stream rows start with "0  " then the stream name
    stream_pattern = re.compile(r"^0\s+([A-Z][A-Z\s]+?)\s{2,}([\d\.\s-]+)$")

    lines = content.split("\n")
    for line in lines:
        # Check for year header
        year_match = year_pattern.search(line)
        if year_match:
            current_year = int(year_match.group(1))
            if current_year not in parsed_data:
                parsed_data[current_year] = {}
            continue

        # Skip if we haven't found a year yet
        if current_year is None:
            continue

        # Check for cell row
        cell_match = cell_pattern.match(line)
        if cell_match:
            lay = int(cell_match.group(1))
            row = int(cell_match.group(2))
            col = int(cell_match.group(3))
            values_str = cell_match.group(4).strip()
            values = values_str.split()

            if len(values) >= 12:
                cell_key = f"{lay} {row} {col}"
                parsed_data[current_year][cell_key] = {}
                for i, month in enumerate(MONTH_NAMES):
                    parsed_data[current_year][cell_key][month] = float(values[i])
            continue

        # Check for stream summary row
        stream_match = stream_pattern.match(line)
        if stream_match:
            stream_name = stream_match.group(1).strip()
            # Normalize multiple spaces to single space (e.g., "RIV  TOTAL" -> "RIV TOTAL")
            stream_name = re.sub(r"\s+", " ", stream_name)
            values_str = stream_match.group(2).strip()
            values = values_str.split()

            if len(values) >= 12:
                parsed_data[current_year][stream_name] = {}
                for i, month in enumerate(MONTH_NAMES):
                    parsed_data[current_year][stream_name][month] = float(values[i])
            continue

    # Print summary
    if parsed_data:
        years = sorted(parsed_data.keys())
        print(f"  Years parsed: {len(years)} ({years[0]}-{years[-1]})")

        # Print sample 2024 values for verification
        if 2024 in parsed_data:
            if "R POJOAQUE" in parsed_data[2024]:
                sample_val = parsed_data[2024]["R POJOAQUE"]["jan"]
                print(f"  Sample 2024 R POJOAQUE jan: {sample_val:.6f} cfs")
            if "RIO GRANDE" in parsed_data[2024]:
                sample_val = parsed_data[2024]["RIO GRANDE"]["jan"]
                print(f"  Sample 2024 RIO GRANDE jan: {sample_val:.6f} cfs")
    else:
        print_error(
            "No data parsed from post-processor output",
            str(path.resolve()),
            "Empty parsed data",
            "At least one year of data",
            "File may be empty or in unexpected format"
        )

    return parsed_data


# =============================================================================
# US-004: Extract 2024 Stream Depletions
# =============================================================================

# Stream names as they appear in post-processor output
STREAM_NAMES: list[str] = [
    "R POJOAQUE",   # Rio Pojoaque-Nambe tributary
    "R TESUQUE",    # Rio Tesuque tributary
    "RIO GRANDE",   # Rio Grande main stem
    "RIV TOTAL",    # Total river depletions (normalized from double space in source file)
    "LC SPRINGS",   # La Cienega Springs
]


def extract_stream_depletions(
    parsed_data: ParsedData,
    year: int | None = None,
) -> dict[str, list[float]]:
    """
    Extract monthly stream depletions from parsed data for a given year.

    Scientific Basis:
    - Post-processor calculates depletions for each stream reach
    - Monthly values are in cubic feet per second (cfs)
    - These represent superposition model results from 1988-{year} pumping
    - Must be converted to acre-feet and combined with Core (2003) residuals

    Assumptions:
    1. parsed_data contains the target year with stream data
    2. All 12 months are present for each stream
    3. Stream names match exactly (including whitespace)

    Args:
        parsed_data: Nested dict from parse_post_processor_output()
                    Format: {year: {identifier: {month: value_cfs}}}
        year: Year to extract. If None, uses DEFAULT_YEAR.

    Returns:
        Dict mapping stream name to list of 12 monthly cfs values [jan..dec]
        Example: {"R POJOAQUE": [0.083581, 0.081234, ...]}

    Raises:
        None - prints forensic error messages and returns empty dict on failure

    Example:
        >>> data = parse_post_processor_output(year=2024)
        >>> depletions = extract_stream_depletions(data, year=2024)
        Extracting 2024 stream depletions...
          R POJOAQUE: jan=0.083581, ..., dec=0.086123, annual_mean=0.084562 cfs
          ...
        >>> depletions["R POJOAQUE"][0]  # January value
        0.083581
    """
    if year is None:
        year = DEFAULT_YEAR

    print(f"Extracting {year} stream depletions...")

    # Check for target year data
    if year not in parsed_data:
        print_error(
            f"Year {year} not found in parsed data",
            "extract_stream_depletions()",
            f"Years available: {sorted(parsed_data.keys())[:5]}...",
            f"{year} present in parsed data",
            f"Post-processor output may not include {year} or parsing failed",
        )
        return {}

    year_data = parsed_data[year]
    stream_depletions: dict[str, list[float]] = {}

    # Extract each stream's monthly values
    for stream_name in STREAM_NAMES:
        if stream_name not in year_data:
            print_error(
                f"Stream '{stream_name}' not found in {year} data",
                "extract_stream_depletions()",
                f"Identifiers: {list(year_data.keys())[:10]}...",
                f"'{stream_name}' present in year data",
                "Stream name may have different formatting in output file",
            )
            return {}

        stream_data = year_data[stream_name]
        monthly_values: list[float] = []

        # Extract values in month order
        for month in MONTH_NAMES:
            if month not in stream_data:
                print_error(
                    f"Month '{month}' not found for stream '{stream_name}'",
                    "extract_stream_depletions()",
                    f"Months available: {list(stream_data.keys())}",
                    f"All 12 months present",
                    "Parsing may have missed some months",
                )
                return {}
            monthly_values.append(stream_data[month])

        stream_depletions[stream_name] = monthly_values

        # Print verification output
        annual_mean = sum(monthly_values) / 12
        print(
            f"  {stream_name}: jan={monthly_values[0]:.6f}, "
            f"dec={monthly_values[11]:.6f}, "
            f"annual_mean={annual_mean:.6f} cfs"
        )

    print(f"  Extracted {len(stream_depletions)} streams successfully.")
    return stream_depletions


# Backward compatibility alias for old function name
def extract_stream_depletions_2024(parsed_data: ParsedData) -> dict[str, list[float]]:
    """Deprecated: Use extract_stream_depletions(parsed_data, year=2024) instead."""
    return extract_stream_depletions(parsed_data, year=2024)


# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

def check_prerequisites(year: int) -> bool:
    """
    Check required inputs exist before processing.

    Validates that all required input files are present before starting
    the depletion table workflow. Provides clear error messages with hints.

    Args:
        year: Year to process (e.g., 2024, 2025)

    Returns:
        True if all prerequisites are met, False otherwise
    """
    depletions_dir = Path(get_depletions_dir(year))
    modflow_dir = Path(get_modflow_output_dir(year))
    riv_flux, ghb_flux = get_flux_files(year)

    # Print checklist-style directory structure detection
    print("\n" + "="*70)
    print(f"STEP 3: GENERATE DEPLETION TABLES - YEAR {year}")
    print("="*70)

    # Detect structure
    if year <= 2024:
        structure = "NESTED (output/modflow/{year}/modflow/)"
    else:
        structure = "FLAT (output/modflow/{year}/)"
    print(f"📋 Directory Structure: {structure}")
    print(f"  - MODFLOW output: {modflow_dir}")
    print(f"  - Depletions dir: {depletions_dir}")

    # Check file sizes
    import os
    print(f"\n📋 Flux Files:")
    riv_path = modflow_dir / riv_flux
    ghb_path = modflow_dir / ghb_flux
    if riv_path.exists() and ghb_path.exists():
        riv_size = os.path.getsize(riv_path) / (1024*1024)
        ghb_size = os.path.getsize(ghb_path) / (1024*1024)
        print(f"  ✓ {riv_flux}: {riv_size:.1f} MB")
        print(f"  ✓ {ghb_flux}: {ghb_size:.1f} MB")
    else:
        print(f"  ⚠ Flux files not found (will fail later)")

    print("\n📦 Outputs (after completion):")
    print(f"  - TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx")
    print(f"  - TABLE_4_Rio_Grande_Otowi_{year}.xlsx")
    print(f"  - TABLE_5_La_Cienega_Springs_{year}.xlsx")

    print("\n➡️  Next Step:")
    print(f"  python3 step5_verify_workflow.py --year {year}")
    print("="*70 + "\n")

    # Check MODFLOW output directory exists
    if not modflow_dir.exists():
        print_error(
            "MODFLOW output directory not found",
            str(modflow_dir),
            "Directory does not exist",
            f"MODFLOW output for {year}",
            f"Run 'python3 step2_update_modflow.py --year {year}' then './step3_run_modflow.sh --year {year}'"
        )
        return False

    # Check flux files exist
    for flux_file in [riv_flux, ghb_flux]:
        flux_path = modflow_dir / flux_file
        if not flux_path.exists():
            print_error(
                f"Flux file not found: {flux_file}",
                str(flux_path),
                "File does not exist",
                "MODFLOW flux output file",
                f"Run MODFLOW96 with CY{year}.nam to generate flux files"
            )
            return False

    # Check depletions directory exists
    if not depletions_dir.exists():
        print_error(
            "Depletions directory not found",
            str(depletions_dir),
            "Directory does not exist",
            f"Depletions working directory for {year}",
            f"Create directory and copy sfmodflx_2245.exe post-processor"
        )
        return False

    # Check post-processor exists
    exe_path = depletions_dir / "sfmodflx_2245.exe"
    if not exe_path.exists():
        print_error(
            "Post-processor not found",
            str(exe_path),
            "File does not exist",
            "sfmodflx_2245.exe in depletions directory",
            "Copy post-processor executable to depletions directory"
        )
        return False

    return True


# =============================================================================
# MAIN ENTRY POINT (US-015)
# =============================================================================

def main(year: int | None = None) -> int:
    """
    Main entry point for stream depletion table generation.

    This function orchestrates the complete workflow:
    1. Copy flux files to post-processor directory (US-001)
    2. Run post-processor via Wine (US-002)
    3. Parse post-processor output (US-003)
    4. Extract stream depletions (US-004)
    5. Extract Otowi cell depletions (US-005)
    6. Load Core (2003) residuals (US-006)
    7. Generate Table 3 data (US-008)
    8. Generate Table 4 data (US-009)
    9. Generate Table 5 data (US-010)
    10. Write Table 3 XLSX (US-011)
    11. Write Table 4 XLSX (US-012)
    12. Write Table 5 XLSX (US-013)
    13. Validate against validation files (US-014)

    Args:
        year: Processing year. Default: 2024 (uses global YEAR constant).

    Returns:
        Exit code: 0 if all validations pass, 1 if any errors occurred
    """
    from pathlib import Path

    import stream_depletions as sd

    if year is None:
        year = DEFAULT_YEAR

    print(f"=== Stream Depletion Table Generator for {year} ===")
    print()

    # Check prerequisites before processing
    if not check_prerequisites(year):
        return 1

    # Create output directory if not exists
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir.resolve()}")
    print()

    # US-001: Copy flux files
    if not copy_flux_files(year):
        print("\nFailed at US-001: Copy flux files")
        return 1

    print("\n=== US-001 Complete ===\n")

    # US-002: Run post-processor via Wine
    if not run_post_processor(year):
        print("\nFailed at US-002: Run post-processor")
        return 1

    print("\n=== US-002 Complete ===\n")

    # US-003: Parse post-processor output
    parsed_data = parse_post_processor_output(year=year)
    if not parsed_data:
        print("\nFailed at US-003: Parse post-processor output")
        return 1

    print("\n=== US-003 Complete ===\n")

    # US-004: Extract stream depletions
    stream_depletions = extract_stream_depletions(parsed_data, year=year)
    if not stream_depletions:
        print("\nFailed at US-004: Extract stream depletions")
        return 1

    print("\n=== US-004 Complete ===\n")

    # US-005: Extract Otowi cell depletions
    try:
        above_cfs, below_cfs = sd.extract_otowi_depletions(parsed_data, year)
        sd.print_otowi_verification(above_cfs, below_cfs)
    except KeyError as e:
        print_error(
            "Failed to extract Otowi depletions",
            "extract_otowi_depletions()",
            str(e),
            "All Otowi cells present in parsed data",
            "Check cell coordinates match post-processor output"
        )
        return 1

    print("\n=== US-005 Complete ===\n")

    # US-006: Load Core (2003) residuals
    sd.print_residual_verification(year)

    print("\n=== US-006 Complete ===\n")

    # US-008: Generate Table 3 data
    try:
        table3_data = sd.generate_table3_data(parsed_data, year)
        sd.print_table3_verification(table3_data, year)
    except KeyError as e:
        print_error(
            "Failed to generate Table 3 data",
            "generate_table3_data()",
            str(e),
            "R POJOAQUE and R TESUQUE in parsed data",
            "Check stream names match post-processor output"
        )
        return 1

    print("\n=== US-008 Complete ===\n")

    # US-009: Generate Table 4 data
    try:
        table4_data = sd.generate_table4_data(parsed_data, year)
        sd.print_table4_verification(table4_data, year)
    except KeyError as e:
        print_error(
            "Failed to generate Table 4 data",
            "generate_table4_data()",
            str(e),
            "All required cells and streams in parsed data",
            "Check cell coordinates and stream names"
        )
        return 1

    print("\n=== US-009 Complete ===\n")

    # US-010: Generate Table 5 data
    try:
        table5_data = sd.generate_table5_data(parsed_data, year)
        sd.print_table5_verification(table5_data, year)
    except KeyError as e:
        print_error(
            "Failed to generate Table 5 data",
            "generate_table5_data()",
            str(e),
            "LC SPRINGS in parsed data",
            "Check La Cienega Springs data in post-processor output"
        )
        return 1

    print("\n=== US-010 Complete ===\n")

    # US-011: Write Table 3 XLSX
    table3_path = output_dir / f"TABLE_3_Rio_Pojoaque_Tesuque_{year}.xlsx"
    try:
        sd.write_table3_xlsx(parsed_data, table3_path)
        print(f"Table 3 written to: {table3_path}")
    except Exception as e:
        print_error(
            "Failed to write Table 3 XLSX",
            str(table3_path),
            str(e),
            "Successfully create Excel file",
            "Check openpyxl installation and file permissions"
        )
        return 1

    print("\n=== US-011 Complete ===\n")

    # US-012: Write Table 4 XLSX
    table4_path = output_dir / f"TABLE_4_Rio_Grande_Otowi_{year}.xlsx"
    try:
        sd.write_table4_xlsx(parsed_data, table4_path, year)
        print(f"Table 4 written to: {table4_path}")
    except Exception as e:
        print_error(
            "Failed to write Table 4 XLSX",
            str(table4_path),
            str(e),
            "Successfully create Excel file",
            "Check openpyxl installation and file permissions"
        )
        return 1

    print("\n=== US-012 Complete ===\n")

    # US-013: Write Table 5 XLSX
    table5_path = output_dir / f"TABLE_5_La_Cienega_Springs_{year}.xlsx"
    try:
        sd.write_table5_xlsx(table5_path)
        print(f"Table 5 written to: {table5_path}")
    except Exception as e:
        print_error(
            "Failed to write Table 5 XLSX",
            str(table5_path),
            str(e),
            "Successfully create Excel file",
            "Check openpyxl installation and file permissions"
        )
        return 1

    print("\n=== US-013 Complete ===\n")

    # US-014: Validate generated tables against validation files
    table3_validation = Path(VALIDATION_DIR) / "TABLE 3 - Rio Pojoaque-Nambe & Rio Tesuque.xlsx"
    table4_validation = Path(VALIDATION_DIR) / "TABLE 4 - Rio Grande, above below Otowi.xlsx"

    print("=== Validating Generated Tables ===\n")

    validation_results = sd.validate_all_tables(
        table3_validation,
        table4_validation,
        table3_data,
        table4_data,
        table5_data,
        year
    )

    sd.print_validation_results(validation_results)

    print("\n=== US-014 Complete ===\n")

    # Print final summary
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"\nYear processed: {year}")
    print("\nGenerated files:")
    print(f"  - {table3_path}")
    print(f"  - {table4_path}")
    print(f"  - {table5_path}")
    print(f"\nValidation status: {validation_results['overall_status']}")

    overall_status = validation_results['overall_status']
    if overall_status == 'OK':
        print("\nAll validations passed!")
        return 0
    elif overall_status == 'OK_WITH_SKIPPED':
        print("\nValidations passed. Some tables were skipped (no reference data for this year).")
        return 0
    else:
        print("\nSome validations failed - see details above.")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate stream depletion tables from MODFLOW post-processor output"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=DEFAULT_YEAR,
        help=f"Processing year (default: {DEFAULT_YEAR})"
    )

    args = parser.parse_args()
    sys.exit(main(args.year))
