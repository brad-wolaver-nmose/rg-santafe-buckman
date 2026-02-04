#!/usr/bin/env python3
"""
Stream Depletion Tables from MODFLOW Post-Processor

This script processes MODFLOW binary output files (CY2024_ghb.flx and CY2024_riv.flx)
using the sfmodflx_2245 post-processor to generate stream depletion tables for the
2024 Buckman Well Field annual report.

Scientific Basis:
- Superposition model: MODFLOW calculates depletions from 1988-2024 pumping
- Analytical residuals: Core (2003) provides pre-1988 pumping effects
- Unit conversion: cfs × days × 86400 / 43560 = acre-feet
"""

import shutil
import subprocess
import sys
from pathlib import Path


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Source directory containing MODFLOW flux output files
MODFLOW_OUTPUT_DIR: str = "./output/modflow/2024/modflow/"

# Destination directory for post-processor input/output
DEPLETIONS_DIR: str = "./output/modflow/2024/depletions/"

# Output directory for generated XLSX tables
OUTPUT_DIR: str = "./output/depletion/"

# Validation directory
VALIDATION_DIR: str = "./validation/"

# Processing year
YEAR: int = 2024

# Flux file names (MODFLOW binary output)
RIV_FLUX_FILE: str = "CY2024_riv.flx"
GHB_FLUX_FILE: str = "CY2024_ghb.flx"


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

def copy_flux_files() -> bool:
    """
    Copy MODFLOW flux files to the post-processor directory.

    Scientific Basis:
    - sfmodflx_2245.exe reads flux files from its working directory
    - Flux files contain monthly boundary condition flows (river and GHB)
    - Files must be accessible to post-processor for depletion calculation

    Assumptions:
    1. Source flux files exist in MODFLOW_OUTPUT_DIR
    2. Destination directory DEPLETIONS_DIR exists
    3. Post-processor sfmodflx_2245.exe is in DEPLETIONS_DIR

    Returns:
        True if both files copied successfully, False otherwise

    Raises:
        None - prints forensic error messages and returns False on failure

    Example:
        >>> success = copy_flux_files()
        Copying flux files to post-processor directory...
          CY2024_riv.flx: 31484640 bytes -> output/modflow/2024/depletions/
          CY2024_ghb.flx: 31484640 bytes -> output/modflow/2024/depletions/
        Flux files copied successfully.
        >>> success
        True
    """
    print("Copying flux files to post-processor directory...")

    source_dir = Path(MODFLOW_OUTPUT_DIR)
    dest_dir = Path(DEPLETIONS_DIR)

    # List of files to copy: (filename, description)
    flux_files = [
        (RIV_FLUX_FILE, "river boundary flux"),
        (GHB_FLUX_FILE, "general head boundary flux"),
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

# Output filename prefix (post-processor creates file with this name)
OUTPUT_FILE_PREFIX: str = "CY2024"


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


def run_post_processor() -> bool:
    """
    Execute sfmodflx_2245.exe via Wine with automated input.

    Scientific Basis:
    - sfmodflx_2245 is a Fortran-based post-processor for MODFLOW flux files
    - It reads river (RIV) and general head boundary (GHB) flux files
    - Calculates stream depletions by summing boundary condition flows
    - Output file contains monthly cfs values for each model cell and stream

    Assumptions:
    1. Wine is installed and functional
    2. sfmodflx_2245.exe exists in DEPLETIONS_DIR
    3. Flux files (CY2024_riv.flx, CY2024_ghb.flx) are in DEPLETIONS_DIR
    4. Post-processor expects three stdin inputs: riv_file, ghb_file, output_prefix

    Returns:
        True if post-processor ran successfully, False otherwise

    Raises:
        None - prints forensic error messages and returns False on failure

    Example:
        >>> success = run_post_processor()
        Running post-processor via Wine...
          Command: wine sfmodflx_2245.exe
          Working directory: output/modflow/2024/depletions/
          Inputs: CY2024_riv.flx, CY2024_ghb.flx, CY2024
        Post-processor completed successfully.
          Output file: CY2024 (1234567 bytes)
        >>> success
        True
    """
    print("Running post-processor via Wine...")

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

    depletions_dir = Path(DEPLETIONS_DIR)

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
    riv_path = depletions_dir / RIV_FLUX_FILE
    ghb_path = depletions_dir / GHB_FLUX_FILE

    if not riv_path.exists():
        print_error(
            "RIV flux file not found in depletions directory",
            str(riv_path.resolve()),
            "File does not exist",
            f"{RIV_FLUX_FILE} copied to depletions directory",
            "Run copy_flux_files() before run_post_processor()"
        )
        return False

    if not ghb_path.exists():
        print_error(
            "GHB flux file not found in depletions directory",
            str(ghb_path.resolve()),
            "File does not exist",
            f"{GHB_FLUX_FILE} copied to depletions directory",
            "Run copy_flux_files() before run_post_processor()"
        )
        return False

    # Prepare stdin input for post-processor
    # Format: three lines - riv file, ghb file, output prefix
    stdin_input = f"{RIV_FLUX_FILE}\n{GHB_FLUX_FILE}\n{OUTPUT_FILE_PREFIX}\n"

    print(f"  Command: wine {POST_PROCESSOR_EXE}")
    print(f"  Working directory: {depletions_dir}/")
    print(f"  Inputs: {RIV_FLUX_FILE}, {GHB_FLUX_FILE}, {OUTPUT_FILE_PREFIX}")

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
        output_path = depletions_dir / OUTPUT_FILE_PREFIX
        if not output_path.exists():
            print_error(
                "Post-processor output file not created",
                str(output_path.resolve()),
                "File does not exist",
                f"{OUTPUT_FILE_PREFIX} created by post-processor",
                "Post-processor may have failed silently or used different output path"
            )
            print(f"\n  stdout:\n{result.stdout}")
            print(f"\n  stderr:\n{result.stderr}")
            return False

        output_size = output_path.stat().st_size
        print(f"Post-processor completed successfully.")
        print(f"  Output file: {OUTPUT_FILE_PREFIX} ({output_size:,} bytes)")

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


def parse_post_processor_output(file_path: str | None = None) -> ParsedData:
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
        file_path: Path to post-processor output file. If None, uses default
                   DEPLETIONS_DIR/OUTPUT_FILE_PREFIX

    Returns:
        Nested dict: {year: {identifier: {month: value_cfs}}}
        - year: Integer year (1988, 1989, ..., 2024, ...)
        - identifier: Cell key "LAY_ROW_COL" or stream name
        - month: Three-letter lowercase month name
        - value_cfs: Flow in cubic feet per second

    Raises:
        None - prints forensic error messages and returns empty dict on failure

    Example:
        >>> data = parse_post_processor_output()
        Parsing post-processor output...
          File: output/modflow/2024/depletions/CY2024
          Years parsed: 37 (1988-2024)
          Sample 2024 R POJOAQUE jan: 0.083581 cfs
        >>> data[2024]["R POJOAQUE"]["jan"]
        0.083581
    """
    from pathlib import Path
    import re

    if file_path is None:
        file_path = str(Path(DEPLETIONS_DIR) / OUTPUT_FILE_PREFIX)

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
                cell_key = f"{lay}_{row}_{col}"
                parsed_data[current_year][cell_key] = {}
                for i, month in enumerate(MONTH_NAMES):
                    parsed_data[current_year][cell_key][month] = float(values[i])
            continue

        # Check for stream summary row
        stream_match = stream_pattern.match(line)
        if stream_match:
            stream_name = stream_match.group(1).strip()
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
    "RIV  TOTAL",   # Total river depletions (note: double space in source file)
    "LC SPRINGS",   # La Cienega Springs
]


def extract_stream_depletions_2024(
    parsed_data: ParsedData,
) -> dict[str, list[float]]:
    """
    Extract 2024 monthly stream depletions from parsed data.

    Scientific Basis:
    - Post-processor calculates depletions for each stream reach
    - Monthly values are in cubic feet per second (cfs)
    - These represent superposition model results from 1988-2024 pumping
    - Must be converted to acre-feet and combined with Core (2003) residuals

    Assumptions:
    1. parsed_data contains 2024 year with stream data
    2. All 12 months are present for each stream
    3. Stream names match exactly (including whitespace)

    Args:
        parsed_data: Nested dict from parse_post_processor_output()
                    Format: {year: {identifier: {month: value_cfs}}}

    Returns:
        Dict mapping stream name to list of 12 monthly cfs values [jan..dec]
        Example: {"R POJOAQUE": [0.083581, 0.081234, ...]}

    Raises:
        None - prints forensic error messages and returns empty dict on failure

    Example:
        >>> data = parse_post_processor_output()
        >>> depletions = extract_stream_depletions_2024(data)
        Extracting 2024 stream depletions...
          R POJOAQUE: jan=0.083581, ..., dec=0.086123, annual_mean=0.084562 cfs
          ...
        >>> depletions["R POJOAQUE"][0]  # January value
        0.083581
    """
    print("Extracting 2024 stream depletions...")

    # Check for 2024 data
    if 2024 not in parsed_data:
        print_error(
            "Year 2024 not found in parsed data",
            "extract_stream_depletions_2024()",
            f"Years available: {sorted(parsed_data.keys())[:5]}...",
            "2024 present in parsed data",
            "Post-processor output may not include 2024 or parsing failed",
        )
        return {}

    year_data = parsed_data[2024]
    stream_depletions: dict[str, list[float]] = {}

    # Extract each stream's monthly values
    for stream_name in STREAM_NAMES:
        if stream_name not in year_data:
            print_error(
                f"Stream '{stream_name}' not found in 2024 data",
                "extract_stream_depletions_2024()",
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
                    "extract_stream_depletions_2024()",
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


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """
    Main entry point for stream depletion table generation.

    Returns:
        Exit code: 0 if successful, 1 if any errors occurred
    """
    print(f"=== Stream Depletion Table Generator for {YEAR} ===")
    print()

    # US-001: Copy flux files
    if not copy_flux_files():
        print("\nFailed at US-001: Copy flux files")
        return 1

    print("\n=== US-001 Complete ===\n")

    # US-002: Run post-processor via Wine
    if not run_post_processor():
        print("\nFailed at US-002: Run post-processor")
        return 1

    print("\n=== US-002 Complete ===\n")

    # US-003: Parse post-processor output
    parsed_data = parse_post_processor_output()
    if not parsed_data:
        print("\nFailed at US-003: Parse post-processor output")
        return 1

    print("\n=== US-003 Complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
