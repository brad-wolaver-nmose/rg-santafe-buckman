#!/usr/bin/env python3
"""
Buckman Well Field PDF Data Ingestion Workflow

This script automates the ingestion of monthly meter report PDFs from the City
of Santa Fe for the Buckman Well Field. It uses OCR to extract pumping data,
validates the data through conversion checks, and produces structured CSV outputs
for subsequent analysis steps.

SYSTEM DEPENDENCIES:
- Tesseract OCR: sudo apt-get install tesseract-ocr
- Poppler: sudo apt-get install poppler-utils

PYTHON DEPENDENCIES:
- Install with: pip install -r requirements.txt
"""

import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from collections import Counter
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any
from pdf2image import convert_from_path
from PIL.Image import Image
import pytesseract
import pandas as pd


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# OCR confidence threshold: values below this are flagged as unreliable
# Tesseract returns confidence scores 0-100, with -1 meaning "invalid/no data"
OCR_CONFIDENCE_THRESHOLD = 80  # Lowered from 95 - too strict for mixed graphic/text documents

# Image cropping ratios for targeting specific regions of the PDF page
HEADER_CROP_RATIO = 0.35  # Top 35% of page contains header/date info (increased from 25%)
TABLE_CROP_RATIO = 0.50   # Bottom 50% of page contains well data table

# Line grouping tolerance for OCR table reconstruction
# Words within this many pixels vertically are considered same row
LINE_GROUPING_TOLERANCE_PX = 20

# PDF to image conversion resolution (DPI)
# 300 DPI provides good balance of OCR accuracy vs processing time
PDF_CONVERSION_DPI = 300

# Tolerance values for total verification
MG_VERIFICATION_TOLERANCE = 0.01   # 2 decimal places
AF_VERIFICATION_TOLERANCE = 0.001  # 3 decimal places

# Month abbreviations in calendar order (used across multiple functions)
MONTHS_ABBREV: Tuple[str, ...] = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)

# Month tuples for iteration: (numeric string, abbreviation)
MONTHS_ORDERED: Tuple[Tuple[str, str], ...] = (
    ("01", "JAN"), ("02", "FEB"), ("03", "MAR"), ("04", "APR"),
    ("05", "MAY"), ("06", "JUN"), ("07", "JUL"), ("08", "AUG"),
    ("09", "SEP"), ("10", "OCT"), ("11", "NOV"), ("12", "DEC"),
)


def check_system_dependencies() -> bool:
    """
    Check that required system dependencies are installed.

    This function verifies that Tesseract OCR and Poppler (for pdf2image)
    are installed and accessible in the system PATH. These are required
    for PDF processing and OCR functionality.

    Returns:
        True if all dependencies are available, False otherwise.
        Prints helpful installation instructions if dependencies are missing.
    """
    missing_deps = []

    # Check for Tesseract OCR
    try:
        # Try to get tesseract version - this will fail if not installed
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        missing_deps.append({
            "name": "Tesseract OCR",
            "package": "tesseract-ocr",
            "brew": "tesseract",
        })

    # Check for Poppler (pdftoppm command)
    try:
        result = subprocess.run(
            ["pdftoppm", "-v"],
            capture_output=True,
            timeout=5
        )
        # pdftoppm returns version info on stderr, exit code 0 or 99
    except FileNotFoundError:
        missing_deps.append({
            "name": "Poppler",
            "package": "poppler-utils",
            "brew": "poppler",
        })
    except subprocess.TimeoutExpired:
        pass  # Command exists but hung - unusual, assume OK

    if missing_deps:
        print("\n" + "=" * 60)
        print("ERROR: Missing System Dependencies")
        print("=" * 60)
        print("\nThe following required system packages are not installed:\n")

        for dep in missing_deps:
            print(f"  - {dep['name']}")

        print("\nTo install on Ubuntu/Debian:")
        print("  sudo apt-get install " + " ".join(d["package"] for d in missing_deps))

        print("\nTo install on macOS:")
        print("  brew install " + " ".join(d["brew"] for d in missing_deps))

        print("\n" + "=" * 60)
        return False

    return True


# Month mapping for year - used across multiple functions
MONTH_NAME_TO_NUMERIC = {
    "January": "01",
    "February": "02",
    "March": "03",
    "April": "04",
    "May": "05",
    "June": "06",
    "July": "07",
    "August": "08",
    "September": "09",
    "October": "10",
    "November": "11",
    "December": "12",
}

MONTH_NAME_TO_ABBREV = {
    "January": "JAN",
    "February": "FEB",
    "March": "MAR",
    "April": "APR",
    "May": "MAY",
    "June": "JUN",
    "July": "JUL",
    "August": "AUG",
    "September": "SEP",
    "October": "OCT",
    "November": "NOV",
    "December": "DEC",
}


def is_confident(confidence: int, threshold: int = OCR_CONFIDENCE_THRESHOLD) -> bool:
    """
    Check if an OCR confidence score meets the required threshold.

    Tesseract returns confidence scores as integers:
    - 0-100: Valid confidence percentage
    - -1: Invalid/no data (word not recognized)

    This helper function properly handles the -1 case, which would otherwise
    incorrectly pass a simple >= comparison with negative thresholds.

    Args:
        confidence: OCR confidence score from Tesseract (-1 to 100)
        threshold: Minimum acceptable confidence (default: OCR_CONFIDENCE_THRESHOLD)

    Returns:
        True if confidence is valid (not -1) AND meets or exceeds threshold
        False if confidence is -1 (invalid) or below threshold

    Example:
        >>> is_confident(96)   # Returns True (above 95)
        >>> is_confident(94)   # Returns False (below 95)
        >>> is_confident(-1)   # Returns False (invalid)
    """
    # Tesseract uses -1 to indicate invalid/missing confidence data
    if confidence < 0:
        return False
    return confidence >= threshold


class WellData:
    """Data structure for a single well's monthly reading."""

    def __init__(self) -> None:
        """Initialize well data with None values."""
        self.ose_number: Optional[str] = None
        self.ose_number_conf: int = 0
        self.well_name: Optional[str] = None
        self.well_name_conf: int = 0
        self.mg_value: Optional[float] = None
        self.mg_conf: int = 0
        self.af_value: Optional[float] = None
        self.af_conf: int = 0
        self.meter_reading: Optional[int] = None
        self.meter_conf: int = 0


def pdf_to_image(pdf_path: str) -> Optional[Image]:
    """
    Convert the first page of a PDF to an image for OCR processing.

    This function reads the first page of a PDF file and converts it to a PIL Image
    object at 300 DPI resolution, which is optimal for OCR accuracy with Tesseract.

    Args:
        pdf_path: Path to the PDF file to convert

    Returns:
        PIL Image object of the first page, or None if file cannot be read

    Raises:
        None (errors are logged and None is returned gracefully)
    """
    try:
        # Convert path to Path object for validation
        path = Path(pdf_path)

        # Check if file exists
        if not path.exists():
            print(f"Error: PDF file not found at '{pdf_path}'")
            return None

        # Convert only page 1 (first_page=1, last_page=1) at configured DPI
        # Returns a list of Image objects, we take the first (only) one
        images = convert_from_path(
            pdf_path, first_page=1, last_page=1, dpi=PDF_CONVERSION_DPI
        )

        if not images:
            print(f"Error: Failed to convert PDF '{pdf_path}' to image")
            return None

        return images[0]

    except Exception as e:
        # Include exception type and traceback info for debugging
        print(f"Error processing PDF '{pdf_path}':")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        # Log abbreviated traceback for debugging (last 2 frames)
        tb_lines = traceback.format_exc().strip().split('\n')
        if len(tb_lines) > 4:
            print(f"  Traceback (last 2 frames):")
            for line in tb_lines[-4:]:
                print(f"    {line}")
        return None


def extract_date_from_pdf(
    image: Image,
) -> Tuple[int, str, str, str]:
    """
    Extract year and month information from the PDF header using OCR.

    This function OCRs the top portion of page 1 to find the line matching
    the pattern "Re: Diversion Report for {Month} {Year}" and extracts the
    date information.

    Args:
        image: PIL Image object from page 1 of the PDF

    Returns:
        Tuple of (year, month_name, month_numeric, month_abbrev)
        Example: (2024, "January", "01", "JAN")
        If date cannot be reliably extracted (confidence < 95%), month_name
        will be set to "NOT_OK"

    Raises:
        None (errors are logged and defaults are returned)
    """
    try:
        # Crop to top portion of image to focus on header area
        width, height = image.size
        header_height = int(height * HEADER_CROP_RATIO)
        header_image = image.crop((0, 0, width, header_height))

        # Use OCR to extract text with confidence data
        # image_to_data returns a dictionary with 'text', 'conf' (confidence)
        data = pytesseract.image_to_data(header_image, output_type="dict")

        # Extract all words and their confidence scores
        words = data.get("text", [])
        confidences = data.get("conf", [])

        # Find the line with "Re: Diversion Report for"
        full_text = " ".join(words)

        # Try to find the date line pattern
        # Pattern: "Re: Diversion Report for {Month} {Year}"
        pattern = r"Re:\s*Diversion\s+Report\s+for\s+(\w+)\s+(\d{4})"
        match = re.search(pattern, full_text, re.IGNORECASE)

        if not match:
            print("Warning: Could not find date line in PDF header")
            return (0, "NOT_OK", "NOT_OK", "NOT_OK")

        month_name = match.group(1).strip()
        year_str = match.group(2).strip()

        # Validate month name exists in mapping
        if month_name not in MONTH_NAME_TO_NUMERIC:
            print(f"Warning: Unknown month name '{month_name}'")
            return (0, "NOT_OK", "NOT_OK", "NOT_OK")

        # Parse year as integer
        try:
            year = int(year_str)
        except ValueError:
            print(f"Warning: Could not parse year '{year_str}'")
            return (0, "NOT_OK", "NOT_OK", "NOT_OK")

        # Get the confidence of words in the date line
        # Use fuzzy matching to handle OCR variations (e.g., "January2024" vs "January 2024")
        # Check words that contain the month name or year string
        relevant_confidences = []
        for word, conf in zip(words, confidences):
            word_clean = word.strip()
            if not word_clean:
                continue
            # Check if this word contains the month name or year
            # This handles cases where OCR merges words or has slight variations
            if month_name.lower() in word_clean.lower() or year_str in word_clean:
                if conf >= 0:  # -1 means invalid/no data
                    relevant_confidences.append(conf)

        # If we have confidence data, verify all values meet threshold
        if relevant_confidences:
            min_confidence = min(relevant_confidences)
            if not is_confident(min_confidence):
                print(
                    f"Warning: Date extraction confidence low ({min_confidence}%)"
                )
                return (0, "NOT_OK", "NOT_OK", "NOT_OK")

        # Map month name to numeric and abbreviation
        month_numeric = MONTH_NAME_TO_NUMERIC[month_name]
        month_abbrev = MONTH_NAME_TO_ABBREV[month_name]

        return (year, month_name, month_numeric, month_abbrev)

    except Exception as e:
        print(f"Error extracting date from PDF:")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return (0, "NOT_OK", "NOT_OK", "NOT_OK")


def extract_date_from_filename(filename: str) -> Tuple[int, str, str, str]:
    """
    Extract year and month from PDF filename as fallback when OCR fails.

    This function parses the filename to extract date information when the
    OCR-based extraction from the PDF header is unsuccessful.

    Expected filename format: "YYYY MM MonthName - ..."
    Example: "2024 01 January - City of Santa Fe Water - Meter Reports.pdf"

    Args:
        filename: The PDF filename (with or without path)

    Returns:
        Tuple of (year, month_name, month_numeric, month_abbrev)
        Example: (2024, "January", "01", "JAN")
        Returns (0, "NOT_OK", "NOT_OK", "NOT_OK") if pattern not found
    """
    # Pattern: 4-digit year, space, 2-digit month, space, month name, then " -"
    pattern = r"(\d{4})\s+(\d{2})\s+(\w+)\s*-"
    match = re.search(pattern, filename)

    if not match:
        return (0, "NOT_OK", "NOT_OK", "NOT_OK")

    year_str = match.group(1)
    month_numeric = match.group(2)
    month_name = match.group(3)

    # Validate month name exists in our mapping
    if month_name not in MONTH_NAME_TO_NUMERIC:
        return (0, "NOT_OK", "NOT_OK", "NOT_OK")

    # Validate month numeric matches name (sanity check)
    expected_numeric = MONTH_NAME_TO_NUMERIC[month_name]
    if month_numeric != expected_numeric:
        print(f"    [WARN] Filename month mismatch: {month_numeric} vs {month_name}")

    # Parse year as integer
    try:
        year = int(year_str)
    except ValueError:
        return (0, "NOT_OK", "NOT_OK", "NOT_OK")

    month_abbrev = MONTH_NAME_TO_ABBREV[month_name]
    return (year, month_name, month_numeric, month_abbrev)


def extract_buckman_wells_data(image: Image) -> Tuple[List[WellData], Optional[WellData]]:
    """
    Extract the Buckman Wells table data from the lower portion of page 1.

    This function OCRs the lower half of the page to extract the table containing
    data for Buckman wells #1 through #13, plus the total row.

    Each well's data includes: OSE number, well name, MG value, AF value, meter reading.
    Confidence scores are tracked for each field to flag uncertain values.

    Args:
        image: PIL Image object from page 1 of the PDF

    Returns:
        Tuple of (wells_list, total_row) where:
        - wells_list: List of WellData objects for Buckman #1 through #13
        - total_row: WellData object for "Total Buckman Wells" row, or None if not found

        Any field with <95% OCR confidence will have a flag set but value preserved
        for later validation (cf. US-006 and US-008).

    Raises:
        None (errors are logged and empty list is returned)
    """
    try:
        # Crop to bottom portion of image to focus on table area
        width, height = image.size
        table_start = int(height * TABLE_CROP_RATIO)
        table_image = image.crop((0, table_start, width, height))

        # Use Tesseract with --psm 6 for table/uniform block of text
        # image_to_data returns detailed word-by-word data including confidence
        data = pytesseract.image_to_data(
            table_image, output_type="dict", config="--psm 6"
        )

        # Extract all text components
        words = data.get("text", [])
        confidences = data.get("conf", [])
        left_positions = data.get("left", [])
        top_positions = data.get("top", [])

        # Reconstruct lines by grouping words by top position (approximate line detection)
        # Words within LINE_GROUPING_TOLERANCE_PX pixels vertically are considered same row
        lines: Dict[int, List[Tuple[str, int, int]]] = {}
        for word, conf, top, left in zip(words, confidences, top_positions, left_positions):
            if word.strip():  # Skip empty words
                # Group by top position (with tolerance for alignment variations)
                line_key = (top // LINE_GROUPING_TOLERANCE_PX) * LINE_GROUPING_TOLERANCE_PX
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append((word.strip(), conf, left))

        # Extract wells: skip header rows, extract 13 wells + total
        wells_list: List[WellData] = []
        total_row: Optional[WellData] = None

        # Sort lines by top position to maintain order
        sorted_lines = sorted(lines.items())

        for line_key, line_words in sorted_lines:
            # Join words to form line text
            line_text = " ".join([w[0] for w in line_words])

            # Check if this is the total row
            if "Total" in line_text and "Buckman" in line_text:
                # Parse total row
                total_row = _parse_table_row(line_text, line_words)
                continue

            # Check if this is a Buckman well row (contains "Buckman #" pattern)
            if re.search(r"Buckman\s*#?\d+", line_text, re.IGNORECASE):
                well = _parse_table_row(line_text, line_words)
                if well.well_name:  # Only add if we extracted a well name
                    wells_list.append(well)

        # Return wells and total (total may be None if not found)
        return (wells_list, total_row)

    except Exception as e:
        print(f"Error extracting Buckman wells data:")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return ([], None)


def validate_af_conversion(
    mg_value: Optional[float], reported_af: Optional[float]
) -> str:
    """
    Validate that reported AF matches calculated AF from MG value.

    Compares the City's reported acre-feet value with our calculated conversion
    from million gallons. Both values are rounded to 2 decimal places for
    comparison, as per PRD specification.

    Args:
        mg_value: Million gallons value (from PDF column C)
        reported_af: Acre-feet value reported in PDF (from column D)

    Returns:
        "OK" if values match when rounded to 2 decimals, "NOT_OK" otherwise
        Returns "NOT_OK" if either input is None/invalid

    Raises:
        None (invalid inputs return "NOT_OK")
    """
    if mg_value is None or reported_af is None:
        return "NOT_OK"

    try:
        # Calculate AF from MG
        calculated_af = mg_to_af(mg_value)
        if calculated_af is None:
            return "NOT_OK"

        # Round both to 2 decimal places for comparison
        calculated_rounded = round(calculated_af, 2)
        reported_rounded = round(reported_af, 2)

        # Compare
        if calculated_rounded == reported_rounded:
            return "OK"
        else:
            return "NOT_OK"

    except (TypeError, ValueError):
        return "NOT_OK"


def mg_to_af(mg_value: Optional[float]) -> Optional[float]:
    """
    Convert million gallons to acre-feet using the USGS standard conversion factor.

    Per USGS (https://water.usgs.gov/nawqa/glos.html):
    1 acre-foot = 325,851 gallons
    Therefore: 1 million gallons = 1,000,000 / 325,851 = 3.06889 acre-feet

    Args:
        mg_value: Volume in million gallons (float or None)

    Returns:
        Volume in acre-feet with 5 decimal places precision, or None if input is None/invalid

    Raises:
        None (invalid inputs return None gracefully)
    """
    if mg_value is None:
        return None

    try:
        # USGS conversion factor: 1 MG = 3.06889 AF
        # Using exact factor from USGS: 1,000,000 / 325,851
        conversion_factor = 1_000_000 / 325_851
        af_value = mg_value * conversion_factor

        # Round to 5 decimal places as per PRD spec
        return round(af_value, 5)

    except (TypeError, ValueError):
        return None


def _normalize_well_name(raw_name: str) -> str:
    """
    Normalize well name to consistent 'Buckman #N' format.

    Handles variations like 'Buckman#1', 'Buckman # 1', 'Buckman 1', etc.
    and converts them all to the standard format 'Buckman #N'.

    Args:
        raw_name: Raw well name string from OCR

    Returns:
        Normalized well name in format 'Buckman #N' (e.g., 'Buckman #1')
    """
    # Extract the well number from the raw name
    match = re.search(r"(\d+)", raw_name)
    if match:
        well_num = match.group(1)
        return f"Buckman #{well_num}"
    return raw_name.strip()


def _parse_table_row(line_text: str, line_words: List[Tuple[str, int, int]]) -> WellData:
    """
    Parse a single table row into a WellData object.

    Helper function for extract_buckman_wells_data(). Extracts fields from a
    space-separated row and assigns confidence scores.

    The extraction process:
    1. Extract OSE number (e.g., 'RG-20516-S')
    2. Extract well name (e.g., 'Buckman #1') and normalize format
    3. Remove OSE and well name from text, then extract remaining numbers
    4. Remaining numbers are: MG value, AF value, meter reading (in order)

    Args:
        line_text: Full line text (for pattern matching)
        line_words: List of (word, confidence, left_position) tuples

    Returns:
        WellData object with extracted fields and confidence scores
    """
    well = WellData()

    # Make a working copy of line_text for number extraction
    remaining_text = line_text

    # Extract OSE number (usually first field, format like RG-20516-S)
    ose_pattern = r"(RG-\d+-\S+)"
    ose_match = re.search(ose_pattern, line_text)
    if ose_match:
        well.ose_number = ose_match.group(1)
        # Remove OSE number from remaining text to avoid capturing its digits
        remaining_text = remaining_text.replace(ose_match.group(1), " ")
        # Find confidence for OSE number word
        for word, conf, _ in line_words:
            if ose_match.group(1) in word or word in ose_match.group(1):
                well.ose_number_conf = conf
                break

    # Extract well name (format like "Buckman #1" or "Buckman #13")
    # This pattern captures various OCR variations of the well name
    name_pattern = r"(Buckman\s*#?\s*\d+)"
    name_match = re.search(name_pattern, line_text, re.IGNORECASE)
    if name_match:
        # Normalize to consistent "Buckman #N" format
        well.well_name = _normalize_well_name(name_match.group(1))
        # Remove well name from remaining text to avoid capturing its digit
        remaining_text = re.sub(name_pattern, " ", remaining_text, flags=re.IGNORECASE)
        # Find confidence for well name (use "Buckman" word confidence)
        for word, conf, _ in line_words:
            if "Buckman" in word or "buckman" in word.lower():
                well.well_name_conf = conf
                break

    # Now extract numerical values from remaining text
    # After removing OSE and well name, remaining numbers should be: MG, AF, meter
    # Pattern matches decimal numbers (like 0.000, 12.34) and integers (like 16351)
    numbers = re.findall(r"\d+\.?\d*", remaining_text)

    # We expect exactly 3 numbers: MG, AF, meter reading
    if len(numbers) >= 1:
        # First number is MG (million gallons)
        try:
            well.mg_value = float(numbers[0])
            # Find confidence for this number
            for word, conf, _ in line_words:
                if numbers[0] in word:
                    well.mg_conf = conf
                    break
        except ValueError:
            pass

    if len(numbers) >= 2:
        # Second number is AF (acre-feet)
        try:
            well.af_value = float(numbers[1])
            # Find confidence for AF
            for word, conf, _ in line_words:
                if numbers[1] in word:
                    well.af_conf = conf
                    break
        except ValueError:
            pass

    if len(numbers) >= 3:
        # Third number is meter reading (should be integer)
        try:
            well.meter_reading = int(float(numbers[2]))
            # Find confidence for meter reading
            for word, conf, _ in line_words:
                if numbers[2] in word:
                    well.meter_conf = conf
                    break
        except ValueError:
            pass

    return well


def calculate_totals_verification(
    wells: List[WellData], total_row: Optional[WellData]
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Calculate sums from wells and compare to PDF total row.

    This function calculates totals for MG and AF_Calculated from the wells list,
    then compares against the PDF total row with specified tolerances.

    Args:
        wells: List of WellData objects for Buckman #1 through #13
        total_row: WellData object containing PDF totals, or None

    Returns:
        Tuple of (calculated_sums, verification_results) where:
        - calculated_sums: Dict with "mg_sum" and "af_sum" (formatted strings)
        - verification_results: Dict with "mg_verification" and "af_verification"
          Each is "OK" if match within tolerance, "NOT_OK" otherwise
    """
    calculated_sums: Dict[str, str] = {}
    verification_results: Dict[str, str] = {}

    try:
        # Calculate sums from wells
        mg_sum = 0.0
        af_sum = 0.0
        valid_mg_count = 0
        valid_af_count = 0

        for well in wells:
            if well.mg_value is not None and is_confident(well.mg_conf):
                mg_sum += well.mg_value
                valid_mg_count += 1
            if well.af_value is not None and is_confident(well.af_conf):
                af_sum += well.af_value
                valid_af_count += 1

        # Format calculated sums
        calculated_sums["mg_sum"] = f"{mg_sum:.3f}"
        calculated_sums["af_sum"] = f"{af_sum:.5f}"

        # Compare with PDF total if available
        if total_row and valid_mg_count == len(wells) and valid_af_count == len(wells):
            # Check MG: match within configured tolerance (2 decimal places)
            if total_row.mg_value is not None:
                mg_diff = abs(mg_sum - total_row.mg_value)
                verification_results["mg_verification"] = (
                    "OK" if mg_diff <= MG_VERIFICATION_TOLERANCE else "NOT_OK"
                )
            else:
                verification_results["mg_verification"] = "NOT_OK"

            # Check AF: match within configured tolerance (3 decimal places)
            if total_row.af_value is not None:
                af_diff = abs(af_sum - total_row.af_value)
                verification_results["af_verification"] = (
                    "OK" if af_diff <= AF_VERIFICATION_TOLERANCE else "NOT_OK"
                )
            else:
                verification_results["af_verification"] = "NOT_OK"
        else:
            # Cannot verify without total row or with low confidence wells
            verification_results["mg_verification"] = "NOT_OK"
            verification_results["af_verification"] = "NOT_OK"

        return (calculated_sums, verification_results)

    except Exception as e:
        print(f"Error calculating totals:")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return (
            {"mg_sum": "NOT_OK", "af_sum": "NOT_OK"},
            {"mg_verification": "NOT_OK", "af_verification": "NOT_OK"},
        )


def generate_monthly_csv(
    output_path: str,
    year: int,
    month_numeric: str,
    month_abbrev: str,
    wells: List[WellData],
    total_row: Optional[WellData],
) -> List[str]:
    """
    Generate a monthly CSV file with extracted well data and validation columns.

    This function creates a CSV with the following columns:
    - OSE_Number: State well number
    - Well_Name: City well name (e.g., "Buckman #1")
    - MG_Month: Monthly pumping in million gallons (3 decimal places)
    - AF_Calculated: AF calculated from MG (5 decimal places)
    - AF_Reported: AF reported in PDF (2 decimal places)
    - AF_Verification: "OK" or "NOT_OK" from validation
    - Meter_Reading: Meter reading value

    Rows are sorted by well name (#1 through #13), followed by totals section.

    Args:
        output_path: Path where CSV file will be written
        year: Year (for filename reference)
        month_numeric: Month number string (e.g., "01")
        month_abbrev: Month abbreviation (e.g., "JAN")
        wells: List of WellData objects for wells #1 through #13
        total_row: WellData object for total row, or None if not found

    Returns:
        List of any "NOT_OK" values encountered (for input summary tracking)

    Raises:
        None (errors are logged)
    """
    try:
        # Sort wells by well name to ensure proper order
        def well_sort_key(w: WellData) -> int:
            """Extract well number for sorting (e.g., 1 from 'Buckman #1')."""
            if w.well_name:
                match = re.search(r"\d+", w.well_name)
                if match:
                    return int(match.group())
            return 999

        wells_sorted = sorted(wells, key=well_sort_key)

        # Prepare rows for CSV
        rows = []

        # Add well data rows
        for well in wells_sorted:
            # Handle low confidence values using is_confident() helper
            # This properly handles Tesseract's -1 "invalid" confidence value
            ose_num = (
                well.ose_number
                if is_confident(well.ose_number_conf)
                else "NOT_OK"
            )
            well_name = (
                well.well_name
                if is_confident(well.well_name_conf)
                else "NOT_OK"
            )
            mg_val = (
                f"{well.mg_value:.3f}"
                if well.mg_value is not None and is_confident(well.mg_conf)
                else "NOT_OK"
            )

            # Calculate AF from MG (only if MG confidence is high)
            af_calculated = mg_to_af(well.mg_value) if is_confident(well.mg_conf) else None
            af_calc_str = (
                f"{af_calculated:.5f}"
                if af_calculated is not None
                else "NOT_OK"
            )

            # AF reported from PDF (only if AF confidence is high)
            af_reported = well.af_value if is_confident(well.af_conf) else None
            af_report_str = (
                f"{af_reported:.2f}"
                if af_reported is not None
                else "NOT_OK"
            )

            # Verify AF values match
            af_verification = validate_af_conversion(well.mg_value, af_reported)
            if af_calculated is None or af_reported is None:
                af_verification = "NOT_OK"

            meter_reading = (
                str(well.meter_reading)
                if well.meter_reading is not None and is_confident(well.meter_conf)
                else "NOT_OK"
            )

            rows.append({
                "OSE_Number": ose_num,
                "Well_Name": well_name,
                "MG_Month": mg_val,
                "AF_Calculated": af_calc_str,
                "AF_Reported": af_report_str,
                "AF_Verification": af_verification,
                "Meter_Reading": meter_reading,
            })

        # Calculate and add totals rows
        calculated_sums, verification_results = calculate_totals_verification(wells, total_row)

        # Add Calculated_Sum row
        rows.append({
            "OSE_Number": "Calculated_Sum",
            "Well_Name": "",
            "MG_Month": calculated_sums.get("mg_sum", "NOT_OK"),
            "AF_Calculated": calculated_sums.get("af_sum", "NOT_OK"),
            "AF_Reported": "",
            "AF_Verification": "",
            "Meter_Reading": "",
        })

        # Add PDF_Total row if available
        if total_row:
            pdf_total_mg = (
                f"{total_row.mg_value:.3f}"
                if total_row.mg_value is not None
                else "NOT_OK"
            )
            pdf_total_af = (
                f"{total_row.af_value:.2f}"
                if total_row.af_value is not None
                else "NOT_OK"
            )

            rows.append({
                "OSE_Number": "PDF_Total",
                "Well_Name": "Total Buckman Wells",
                "MG_Month": pdf_total_mg,
                "AF_Calculated": "",
                "AF_Reported": pdf_total_af,
                "AF_Verification": "",
                "Meter_Reading": "",
            })

        # Add Total_Verification row
        rows.append({
            "OSE_Number": "Total_Verification",
            "Well_Name": "",
            "MG_Month": verification_results.get("mg_verification", "NOT_OK"),
            "AF_Calculated": verification_results.get("af_verification", "NOT_OK"),
            "AF_Reported": "",
            "AF_Verification": "",
            "Meter_Reading": "",
        })

        # Write CSV using atomic write pattern (temp file + rename)
        # This prevents partial/corrupted files if the script is interrupted
        if rows:
            df = pd.DataFrame(rows)
            output_dir = os.path.dirname(output_path)

            # Write to temporary file first
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=output_dir,
                suffix='.csv',
                delete=False
            ) as tmp_file:
                df.to_csv(tmp_file, index=False)
                tmp_path = tmp_file.name

            # Atomically replace the target file
            shutil.move(tmp_path, output_path)
            print(f"Created CSV: {output_path}")

        # Collect NOT_OK values for summary
        not_ok_values = []
        for row in rows:
            for col, val in row.items():
                if val == "NOT_OK":
                    not_ok_values.append(val)

        return not_ok_values

    except Exception as e:
        print(f"Error generating monthly CSV '{output_path}':")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return []


def generate_input_summary_csv(year: int, not_ok_values: List[str]) -> None:
    """
    Generate input summary CSV listing all values flagged for human review.

    This function creates a summary of all NOT_OK values encountered during
    processing, with location information (Year, Month, Well, Field, Issue).

    If no issues are found, creates a file with headers only and a note.

    Args:
        year: Year being processed (e.g., 2024)
        not_ok_values: List of NOT_OK strings collected during processing

    Raises:
        None (errors are logged)
    """
    try:
        # Initialize summary data
        summary_rows = []

        # Read all monthly CSVs to find NOT_OK values with location details
        for month_idx, month_abbrev in enumerate(MONTHS_ABBREV):
            month_number = month_idx + 1
            month_numeric = f"{month_number:02d}"

            csv_filename = f"buckman_{year}_{month_numeric}_{month_abbrev}.csv"
            csv_path = f"./output/ingested_data/{csv_filename}"

            if not os.path.exists(csv_path):
                # Missing month
                summary_rows.append({
                    "Year": year,
                    "Month": month_abbrev,
                    "Well": "",
                    "Field": "",
                    "Issue": "Missing PDF file",
                })
                continue

            # Read CSV and find NOT_OK values
            df = pd.read_csv(csv_path)

            # Iterate through rows looking for NOT_OK
            for _, row in df.iterrows():
                well_name = row.get("Well_Name", "")
                ose_number = row.get("OSE_Number", "")

                # Check each column for NOT_OK
                for col_name in df.columns:
                    if pd.notna(row[col_name]) and str(row[col_name]) == "NOT_OK":
                        # Skip header rows in summary
                        if well_name not in ["Calculated_Sum", "PDF_Total", "Total_Verification"]:
                            summary_rows.append({
                                "Year": year,
                                "Month": month_abbrev,
                                "Well": well_name or ose_number,
                                "Field": col_name,
                                "Issue": "Low OCR confidence or verification failure",
                            })

        # Write summary CSV
        output_filename = "input_summary.csv"
        output_path = f"./output/ingested_data/{output_filename}"

        if summary_rows:
            df_summary = pd.DataFrame(summary_rows)
            df_summary.to_csv(output_path, index=False)
            print(f"Created input summary: {output_filename} ({len(summary_rows)} issues)")
        else:
            # No issues found - create file with headers only
            headers_df = pd.DataFrame(columns=["Year", "Month", "Well", "Field", "Issue"])
            headers_df.to_csv(output_path, index=False)
            print(f"Created input summary: {output_filename} (No issues detected)")

    except Exception as e:
        print(f"Error generating input summary:")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")


def generate_annual_summary_csv(year: int) -> None:
    """
    Generate annual summary CSV consolidating all monthly data.

    This function reads all 12 monthly CSV files and creates a summary table
    with the structure:
    - Row 1: Headers (Well, JAN, FEB, ..., DEC, Total)
    - Rows 2-14: Wells 1-13 with AF values from each month
    - Row 15: Total row with column sums

    AF values are displayed with 6 decimal places. If a monthly CSV is missing
    or contains "NOT_OK", that value is carried forward in the summary.

    Args:
        year: Year to generate summary for (e.g., 2024)

    Raises:
        None (errors are logged)
    """
    try:
        # Initialize data structure: well_data[well_num][month] = af_value
        well_data: Dict[int, Dict[str, str]] = {i: {} for i in range(1, 14)}

        # Read all monthly CSVs using module-level MONTHS_ABBREV constant
        for month_idx, month_abbrev in enumerate(MONTHS_ABBREV):
            # Determine month number (1-indexed)
            month_number = month_idx + 1
            month_numeric = f"{month_number:02d}"

            csv_filename = f"buckman_{year}_{month_numeric}_{month_abbrev}.csv"
            csv_path = f"./output/ingested_data/{csv_filename}"

            if not os.path.exists(csv_path):
                # Month not found, mark all wells as NOT_OK
                for well_num in range(1, 14):
                    well_data[well_num][month_abbrev] = "NOT_OK"
                continue

            # Read CSV
            df = pd.read_csv(csv_path)

            # Extract AF_Calculated values for each well
            for well_num in range(1, 14):
                well_name = f"Buckman #{well_num}"
                matching_rows = df[df["Well_Name"] == well_name]

                if not matching_rows.empty:
                    af_value = matching_rows.iloc[0]["AF_Calculated"]
                    well_data[well_num][month_abbrev] = str(af_value)
                else:
                    well_data[well_num][month_abbrev] = "NOT_OK"

        # Build summary table
        rows = []

        # Header row
        header_row = ["Well"] + list(MONTHS_ABBREV) + ["Total"]
        rows.append(header_row)

        # Well rows (1-13)
        for well_num in range(1, 14):
            row = [f"Buckman #{well_num}"]
            well_total = 0.0
            has_valid_data = True

            for month_abbrev in MONTHS_ABBREV:
                value = well_data[well_num].get(month_abbrev, "NOT_OK")
                row.append(value)

                # Try to accumulate total
                if value != "NOT_OK":
                    try:
                        well_total += float(value)
                    except ValueError:
                        has_valid_data = False

            # Add well total
            if has_valid_data and well_total > 0:
                row.append(f"{well_total:.6f}")
            else:
                row.append("NOT_OK")

            rows.append(row)

        # Total row (sum of columns)
        total_row = ["Total"]
        for month_idx, month_abbrev in enumerate(MONTHS_ABBREV):
            month_total = 0.0
            has_valid_data = True

            for well_num in range(1, 14):
                value = well_data[well_num].get(month_abbrev, "NOT_OK")
                if value != "NOT_OK":
                    try:
                        month_total += float(value)
                    except ValueError:
                        has_valid_data = False

            if has_valid_data and month_total > 0:
                total_row.append(f"{month_total:.6f}")
            else:
                total_row.append("NOT_OK")

        # Grand total (sum of all valid cells)
        grand_total = 0.0
        has_valid_data = True
        for well_num in range(1, 14):
            for month_abbrev in MONTHS_ABBREV:
                value = well_data[well_num].get(month_abbrev, "NOT_OK")
                if value != "NOT_OK":
                    try:
                        grand_total += float(value)
                    except ValueError:
                        has_valid_data = False

        if has_valid_data and grand_total > 0:
            total_row.append(f"{grand_total:.6f}")
        else:
            total_row.append("NOT_OK")

        rows.append(total_row)

        # Write summary CSV
        output_filename = f"buckman_{year}_table_2_data.csv"
        output_path = f"./output/ingested_data/{output_filename}"

        df_summary = pd.DataFrame(rows[1:], columns=rows[0])
        df_summary.to_csv(output_path, index=False)

        print(f"Created annual summary: {output_filename}")

    except Exception as e:
        print(f"Error generating annual summary for {year}:")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")


def process_all_months(year: int) -> List[str]:
    """
    Process all 12 months for a given year.

    This function iterates through all months (January through December),
    calls process_single_month for each, and collects all NOT_OK values
    for subsequent input_summary generation.

    Args:
        year: Year to process (e.g., 2024)

    Returns:
        List of all NOT_OK values encountered across all months

    Raises:
        None (errors are logged, processing continues for remaining months)
    """
    # Use module-level month definitions
    all_not_ok_values: List[str] = []
    processed_count = 0
    skipped_count = 0

    print(f"\nProcessing all months for {year}...")
    print("-" * 50)

    for month_numeric, month_abbrev in MONTHS_ORDERED:
        success, not_ok_values = process_single_month(year, month_numeric, month_abbrev)

        if success:
            processed_count += 1
            all_not_ok_values.extend(not_ok_values)
        else:
            skipped_count += 1

    print("-" * 50)
    print(f"Summary: Processed {processed_count} months, skipped {skipped_count}")
    print(f"Total NOT_OK values found: {len(all_not_ok_values)}")

    return all_not_ok_values


def process_single_month(
    year: int, month_numeric: str, month_abbrev: str
) -> Tuple[bool, List[str]]:
    """
    Process a single month's PDF end-to-end, producing a monthly CSV file.

    This function orchestrates the complete workflow for one month:
    1. Constructs input path from year/month/abbrev
    2. Converts PDF page 1 to image
    3. Extracts date information
    4. Extracts well data table
    5. Validates AF conversions
    6. Generates monthly CSV with totals

    Args:
        year: Year (e.g., 2024)
        month_numeric: Month number string (e.g., "01")
        month_abbrev: Month abbreviation (e.g., "JAN")

    Returns:
        Tuple of (success, not_ok_values) where:
        - success: True if processing completed, False if PDF missing
        - not_ok_values: List of NOT_OK values encountered (for summary)

    Raises:
        None (errors are logged)
    """
    try:
        # Construct file paths
        # Use standardized filename format (created by validate_and_prepare_pdfs)
        input_filename = f"{year}_{month_numeric}_{month_abbrev}"
        input_path = f"./input/pdfs/{input_filename}.pdf"

        # Check if PDF exists
        if not os.path.exists(input_path):
            print(f"Warning: PDF not found for {month_abbrev} {year}")
            return (False, [])

        print(f"Processing {month_abbrev} {year}...")

        # Convert PDF to image
        image = pdf_to_image(input_path)
        if image is None:
            print(f"Error: Could not convert PDF for {month_abbrev} {year}")
            return (False, [])

        # Extract date info
        extracted_year, month_name, _, _ = extract_date_from_pdf(image)
        if month_name == "NOT_OK":
            print(f"Warning: Could not extract date for {month_abbrev} {year}")
            return (False, [])

        # Extract well data
        wells, total_row = extract_buckman_wells_data(image)
        if not wells:
            print(f"Warning: Could not extract well data for {month_abbrev} {year}")
            return (False, [])

        # Generate monthly CSV
        output_filename = f"buckman_{year}_{month_numeric}_{month_abbrev}.csv"
        output_path = f"./output/ingested_data/{output_filename}"

        not_ok_values = generate_monthly_csv(
            output_path, year, month_numeric, month_abbrev, wells, total_row
        )

        print(f"Completed {month_abbrev} {year} → {output_filename}")
        return (True, not_ok_values)

    except Exception as e:
        print(f"Error processing {month_abbrev} {year}:")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return (False, [])


def scan_input_pdfs(input_dir: str) -> List[str]:
    """
    Scan the input directory for all PDF files.

    This function finds all PDF files in the specified directory, regardless
    of their naming convention. It returns a list of full paths to each PDF.

    Args:
        input_dir: Path to the directory containing PDF files

    Returns:
        List of full paths to PDF files found, sorted alphabetically

    Example:
        >>> pdfs = scan_input_pdfs("./input/pdfs/")
        >>> print(pdfs[0])
        './input/pdfs/2024 01 January - City of Santa Fe Water - Meter Reports.pdf'
    """
    pdf_files: List[str] = []

    try:
        # Check if directory exists
        if not os.path.exists(input_dir):
            print(f"Warning: Input directory '{input_dir}' does not exist")
            return []

        # Find all PDF files in the directory
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(".pdf"):
                full_path = os.path.join(input_dir, filename)
                pdf_files.append(full_path)

        # Sort alphabetically for consistent ordering
        pdf_files.sort()

        return pdf_files

    except Exception as e:
        print(f"Error scanning input directory '{input_dir}':")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return []


def extract_date_from_pdf_quick(pdf_path: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Lightweight OCR to extract year and month from PDF header only.

    This function is optimized for the pre-flight validation phase. It only
    reads the header area of the PDF to extract the date, avoiding full
    table extraction which is more time-consuming.

    Args:
        pdf_path: Path to the PDF file to scan

    Returns:
        Tuple of (year, month_name) where:
        - year: Integer year (e.g., 2024) or None if extraction failed
        - month_name: Full month name (e.g., "January") or None if extraction failed

    Example:
        >>> year, month = extract_date_from_pdf_quick("./input/pdfs/report.pdf")
        >>> print(f"{month} {year}")
        'January 2024'
    """
    try:
        # Convert PDF to image (first page only)
        image = pdf_to_image(pdf_path)
        if image is None:
            return (None, None)

        # Crop to header area (uses configured ratio instead of hardcoded 1/4)
        width, height = image.size
        header_height = int(height * HEADER_CROP_RATIO)
        header_image = image.crop((0, 0, width, header_height))

        # OCR the header area
        text = pytesseract.image_to_string(header_image)

        # Look for the date pattern
        pattern = r"Re:\s*Diversion\s+Report\s+for\s+(\w+)\s+(\d{4})"
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            month_name = match.group(1).strip()
            year_str = match.group(2).strip()

            # Validate month name
            if month_name in MONTH_NAME_TO_NUMERIC:
                return (int(year_str), month_name)

        return (None, None)

    except Exception as e:
        print(f"Error extracting date from '{pdf_path}':")
        print(f"  Exception type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return (None, None)


def validate_and_prepare_pdfs(target_year: int, input_dir: str = "./input/pdfs/") -> Dict[str, Any]:
    """
    Validate input PDFs and create standardized copies.

    This function performs the pre-flight validation phase:
    1. Scans for all PDF files in the input directory
    2. OCRs each file to extract year and month
    3. Validates coverage (all 12 months present, no duplicates)
    4. Creates standardized copies with consistent naming
    5. Returns a validation report

    Original files are preserved unchanged. Standardized copies are created
    with the naming pattern: {year}_{month_numeric}_{MONTH_ABBREV}.pdf

    Args:
        target_year: The year expected for all PDFs (e.g., 2024)
        input_dir: Path to the input directory (default: "./input/pdfs/")

    Returns:
        Dictionary containing validation results:
        {
            "valid_months": ["01", "02", ...],     # Months ready to process
            "missing_months": ["03", "05"],        # Gaps in coverage
            "duplicates": [("04", [...])],         # Multiple files for same month
            "wrong_year": [("file.pdf", 2023)],    # Files with different year
            "unreadable": ["file.pdf"],            # OCR failed
            "standardized": [{"original": ..., "standard": ...}],
            "total_files_found": 12,
            "issues_count": 0
        }
    """
    # Initialize the validation report
    report: Dict[str, Any] = {
        "valid_months": [],
        "missing_months": [],
        "duplicates": [],
        "wrong_year": [],
        "unreadable": [],
        "standardized": [],
        "total_files_found": 0,
        "issues_count": 0,
    }

    # Track which months we find (for duplicate detection)
    month_to_files: Dict[str, List[str]] = {f"{i:02d}": [] for i in range(1, 13)}

    # Scan for PDF files
    pdf_files = scan_input_pdfs(input_dir)
    report["total_files_found"] = len(pdf_files)

    if not pdf_files:
        report["issues_count"] = 12  # All months missing
        report["missing_months"] = [f"{i:02d}" for i in range(1, 13)]
        return report

    total_pdfs = len(pdf_files)
    print(f"\nScanning {total_pdfs} PDF file(s) for date information...")
    print("-" * 50)

    # Process each PDF with progress indicator
    for idx, pdf_path in enumerate(pdf_files, start=1):
        filename = os.path.basename(pdf_path)
        # Show progress as (current/total) with truncated filename
        progress = f"({idx}/{total_pdfs})"
        print(f"  {progress} Scanning: {filename[:45]}...")

        # Extract date from PDF content (OCR-based)
        year, month_name = extract_date_from_pdf_quick(pdf_path)

        if year is None or month_name is None:
            # OCR failed - try fallback to filename extraction
            year, month_name, _, _ = extract_date_from_filename(filename)
            if month_name == "NOT_OK":
                # Both OCR and filename extraction failed
                report["unreadable"].append(filename)
                report["issues_count"] += 1
                print(f"    [WARN] Could not extract date from header or filename")
                continue
            else:
                print(f"    [INFO] Date extracted from filename: {month_name} {year}")

        if year != target_year:
            # Wrong year
            report["wrong_year"].append((filename, year))
            report["issues_count"] += 1
            print(f"    [WARN] Contains data for {year}, not {target_year}")
            continue

        # Get month numeric
        month_numeric = MONTH_NAME_TO_NUMERIC.get(month_name)
        if month_numeric is None:
            report["unreadable"].append(filename)
            report["issues_count"] += 1
            print(f"    [WARN] Unknown month name: {month_name}")
            continue

        # Track this file for the month
        month_to_files[month_numeric].append(pdf_path)
        print(f"    [OK] {month_name} {year}")

    print("-" * 50)

    # Check for duplicates and create standardized copies
    print("\nCreating standardized copies...")

    for month_numeric, files in sorted(month_to_files.items()):
        month_abbrev = list(MONTH_NAME_TO_ABBREV.values())[int(month_numeric) - 1]

        if len(files) == 0:
            # Missing month
            report["missing_months"].append(month_numeric)
            report["issues_count"] += 1

        elif len(files) == 1:
            # Single file - create standardized copy
            original_path = files[0]
            original_filename = os.path.basename(original_path)
            standard_filename = f"{target_year}_{month_numeric}_{month_abbrev}.pdf"
            standard_path = os.path.join(input_dir, standard_filename)

            # Copy file (skip if already exists with same name)
            if original_path != standard_path:
                shutil.copy2(original_path, standard_path)
                report["standardized"].append({
                    "original": original_filename,
                    "standard": standard_filename,
                })
                print(f"  {month_abbrev}: {original_filename[:40]}... → {standard_filename}")
            else:
                print(f"  {month_abbrev}: Already standardized")

            report["valid_months"].append(month_numeric)

        else:
            # Multiple files for same month
            filenames = [os.path.basename(f) for f in files]
            report["duplicates"].append((month_numeric, filenames))
            report["issues_count"] += 1

    return report


def get_year_interactively(input_dir: str = "./input/pdfs/") -> int:
    """
    Prompt user for the target year, with auto-detection from PDF contents.

    This function scans the input PDFs to detect what years are present,
    then prompts the user to confirm or override the year selection.

    Args:
        input_dir: Path to the input directory (default: "./input/pdfs/")

    Returns:
        Integer year selected by user (e.g., 2024)

    Raises:
        SystemExit: If user provides invalid input or cancels
    """
    print("\nBuckman Well Field PDF Data Ingestion Workflow")
    print("=" * 50)
    print("\nNo year specified. Scanning input/pdfs/ for available data...")

    # Scan PDFs and extract years
    pdf_files = scan_input_pdfs(input_dir)
    years_found: List[int] = []

    for pdf_path in pdf_files:
        year, _ = extract_date_from_pdf_quick(pdf_path)
        if year is not None:
            years_found.append(year)

    # Count occurrences of each year
    if years_found:
        year_counts = Counter(years_found)
        most_common_year = year_counts.most_common(1)[0][0]
        unique_years = sorted(set(years_found))

        print(f"\nFound PDFs containing data for year(s): {', '.join(map(str, unique_years))}")
        default_year = most_common_year
    else:
        print("\nNo valid date information found in PDFs.")
        default_year = 2024  # Fallback default

    # Prompt user for year
    while True:
        try:
            user_input = input(f"\nPlease enter the year to process [{default_year}]: ").strip()

            if user_input == "":
                return default_year

            year = int(user_input)

            # Validate reasonable year range
            if 1990 <= year <= 2100:
                return year
            else:
                print("Please enter a year between 1990 and 2100.")

        except ValueError:
            print("Invalid input. Please enter a valid year (e.g., 2024).")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            sys.exit(0)


def display_preflight_report(report: Dict[str, Any], target_year: int) -> bool:
    """
    Display the pre-flight validation report and prompt for confirmation.

    This function presents a summary of the validation results to the user,
    showing which months are ready, which have issues, and prompts for
    confirmation before proceeding with processing.

    Args:
        report: Validation report from validate_and_prepare_pdfs()
        target_year: The target year for processing

    Returns:
        True if user confirms to proceed, False otherwise
    """
    print("\n")
    print("=" * 60)
    print("           PRE-FLIGHT VALIDATION REPORT")
    print("=" * 60)
    print(f"\nYear: {target_year}")
    print(f"Input directory: ./input/pdfs/")
    print(f"\nOriginal files found: {report['total_files_found']}")
    print(f"Standardized copies created: {len(report['standardized'])}")

    print("\nMonth Coverage:")
    print("-" * 60)

    # Build month status display using module-level constant
    for i, month_abbrev in enumerate(MONTHS_ABBREV):
        month_numeric = f"{i + 1:02d}"

        # Check status
        if month_numeric in report["valid_months"]:
            # Find the standardized file info
            standard_filename = f"{target_year}_{month_numeric}_{month_abbrev}.pdf"
            original = next(
                (s["original"] for s in report["standardized"]
                 if s["standard"] == standard_filename),
                "Already standardized"
            )
            if len(original) > 35:
                original = original[:32] + "..."
            print(f"  [OK]      {month_abbrev} - {standard_filename} (from: {original})")

        elif month_numeric in report["missing_months"]:
            print(f"  [MISSING] {month_abbrev} - No file found for {month_abbrev} {target_year}")

        else:
            # Check for duplicates
            dup_entry = next(
                (d for d in report["duplicates"] if d[0] == month_numeric),
                None
            )
            if dup_entry:
                print(f"  [DUPLICATE] {month_abbrev} - Multiple files contain {month_abbrev} {target_year} data:")
                for dup_file in dup_entry[1]:
                    print(f"              - {dup_file}")

    # Show wrong year files
    if report["wrong_year"]:
        print("\nWrong Year Files:")
        for filename, wrong_year in report["wrong_year"]:
            print(f"  [WRONG YEAR] {filename} - Contains data for {wrong_year}, not {target_year}")

    # Show unreadable files
    if report["unreadable"]:
        print("\nUnreadable Files:")
        for filename in report["unreadable"]:
            print(f"  [UNREADABLE] {filename} - Could not extract date information")

    print("-" * 60)
    print(f"\nIssues Found: {report['issues_count']}")

    # Prompt for confirmation
    if report["issues_count"] == 0:
        # No issues - default to proceed
        prompt = "\nReady to proceed? [Y/n]: "
        default_proceed = True
    else:
        # Issues found - default to not proceed
        print("\nWARNING: Processing will skip missing/problematic months.")
        prompt = "Continue anyway? [y/N]: "
        default_proceed = False

    while True:
        try:
            user_input = input(prompt).strip().lower()

            if user_input == "":
                return default_proceed
            elif user_input in ["y", "yes"]:
                return True
            elif user_input in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            return False


def create_project_directories() -> None:
    """
    Create the required directory structure for the workflow.

    Creates:
    - ./output/ingested_data/ (for output CSV files)

    Verifies:
    - ./input/pdfs/ exists (raises error if missing)

    Handles:
    - Existing directories gracefully (no error if already present)
    """
    # Define the required directories
    output_dir = "./output/ingested_data"
    input_dir = "./input/pdfs"

    # Verify input directory exists
    if not os.path.exists(input_dir):
        raise FileNotFoundError(
            f"Input directory '{input_dir}' does not exist. "
            f"Please ensure the input/pdfs directory is present before running this script."
        )

    # Create output directory if it doesn't exist
    # Using exist_ok=True to avoid race condition where another process
    # could create the directory between our check and creation
    if os.path.exists(output_dir):
        print(f"Output directory already exists: {output_dir}")
    else:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")


if __name__ == "__main__":
    # Check for required system dependencies before doing anything else
    if not check_system_dependencies():
        sys.exit(1)

    # Determine the target year
    # Option 1: Year provided as command-line argument
    # Option 2: Interactive prompt if no argument provided
    if len(sys.argv) == 2:
        try:
            year = int(sys.argv[1])
        except ValueError:
            print(f"Error: Year must be an integer, got '{sys.argv[1]}'")
            sys.exit(1)
    elif len(sys.argv) == 1:
        # No argument provided - use interactive mode
        year = get_year_interactively()
    else:
        print("Usage: python3 ingest_buckman_data.py [year]")
        print("Example: python3 ingest_buckman_data.py 2024")
        print("         python3 ingest_buckman_data.py  (interactive mode)")
        sys.exit(1)

    # Create required directories
    create_project_directories()

    # Validate and prepare PDFs (pre-flight phase)
    # This scans all PDFs, validates dates, and creates standardized copies
    validation_report = validate_and_prepare_pdfs(year)

    # Display pre-flight report and get user confirmation
    proceed = display_preflight_report(validation_report, year)

    if not proceed:
        print("\nOperation cancelled by user.")
        sys.exit(0)

    print(f"\nBuckman Well Field PDF Data Ingestion Workflow")
    print(f"Processing year: {year}")
    print("=" * 50)

    # Process all months
    not_ok_values = process_all_months(year)

    # Generate annual summary
    print("\nGenerating annual summary...")
    generate_annual_summary_csv(year)

    # Generate input summary for human review
    print("\nGenerating input summary...")
    generate_input_summary_csv(year, not_ok_values)

    # Final message
    print("\n" + "=" * 50)
    print("WORKFLOW COMPLETE")
    print("=" * 50)
    print("\nIMPORTANT: Human QA/QC Required")
    print("-" * 50)
    print("1. Review output/ingested_data/input_summary.csv")
    print("2. For each NOT_OK value, open the corresponding monthly CSV")
    print("   and compare against the source PDF")
    print("3. Manually verify and correct NOT_OK values")
    print("4. Save corrected data for downstream analysis")
    print("-" * 50)
    print(f"\nOutput files created in ./output/ingested_data/:")
    print(f"  - 12 monthly CSVs (buckman_{year}_MM_MON.csv)")
    print(f"  - 1 annual summary (buckman_{year}_table_2_data.csv)")
    print(f"  - 1 input summary (input_summary.csv)")
    print()
