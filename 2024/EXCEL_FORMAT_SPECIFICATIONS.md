# Excel Validation Files - Format Specifications

Comprehensive formatting details for the two Santa Fe validation Excel files.

---

## File 1: Table_2_2024.xlsx

### Sheet: Table_2_2024

#### Structure
- **Dimensions:** 17 rows × 20 columns
- **Range:** A1:T17
- **Frozen Panes:** None
- **Merged Cells:** None

#### Column Configuration

**Column Widths:**
- Column A: 14.75
- Columns B-N: 13.0
- Column O: 14.75
- Columns P-T: 13.0, 10.125, 11.875, 10.25, 13.0

**Column Headers (Row 1):**
- A: "Well"
- B-M: "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
- N: "Total"
- O: "Well"
- P-T: (additional columns, content not primary)

#### Cell Formatting

**Header Row (Row 1):**
- Font:
  - Name: Aptos
  - Size: 11 pt
  - Bold: True
  - Color: Theme 1 (typically black text)
- Fill:
  - Type: solid
  - Color: Theme 0 (typically white/light)
- Alignment:
  - Horizontal: center
  - Vertical: None
- Borders:
  - Top: medium
  - Bottom: medium

**Data Rows (Rows 2-17):**

*First Column (Column A - Well ID):*
- Values: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, (empty rows possible)
- Number Format: General
- Font:
  - Name: Aptos
  - Size: 11 pt
  - Bold: True
  - Color: Theme 1
- Alignment:
  - Horizontal: center
- Fill:
  - Type: solid
  - Color: Theme 0 (white) for most rows
  - **EXCEPTION:** Row 4 (Well 3) has RGB color FFFFFF00 (yellow)
- Borders:
  - Bottom: hair (thin line) on most rows
  - Row 2: No bottom border
  - Rows 3-16: hair bottom border

*Numeric Data Columns (B-M):*
- Values: Float or integer values (flow/volume data)
- Number Format: `#,##0.00` (thousands separator, 2 decimal places)
- Font:
  - Name: Aptos
  - Size: 11 pt
  - Bold: False
  - Color: Theme 1
- Fill:
  - Type: solid
  - Color: Matches first column (Theme 0 or FFFFFF00 for row 4)
- Borders:
  - Bottom: hair (matching first column)

*Total Column (Column N):*
- Values: Formula `=SUM(B#:M#)` where # is the row number
- Number Format: `#,##0.00`
- Font/Fill/Borders: Same as numeric columns

*Duplicate Well Column (Column O):*
- Same formatting as Column A

#### Special Features
- **Yellow highlighted row:** Row 4 (Well 3) has yellow fill (RGB: FFFFFF00)
- **Formulas:** Column N contains SUM formulas for each row
- **Number formats used:**
  - `#,##0.00` for numeric data
  - `0.0%` appears somewhere in the sheet (possibly for percentages)

---

## File 2: Table_1_data_afy_2024.xlsx

### Sheet 1: Table1_data_afy_2024

#### Structure
- **Dimensions:** 48 rows × 21 columns
- **Range:** A1:U48
- **Frozen Panes:** None
- **Merged Cells:** None

#### Column Configuration

**Column Widths:**
- Column A: 12.75
- Columns B-N: 13.0
- Column O: 11.75
- Columns P-U: 13.0

**Column Headers (Row 1):**
- A: "Well:"
- B-N: "1", "2", "3/3A", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"
- O: "Total"
- P-S: (empty or additional columns)
- T: "Total"
- U: "Sort"

#### Cell Formatting

**Header Row (Row 1):**
- Font:
  - Name: Aptos
  - Size: 11 pt
  - Bold: True
  - Color: Theme 1 (black text)
- Fill:
  - Type: solid
  - Color: Theme 0 (white/light)
- Alignment:
  - Horizontal: right (for A1)
  - Vertical: None
- Borders:
  - Top: medium
  - Bottom: medium

**Data Rows (Rows 2-48):**

*First Column (Column A - Year):*
- Values: 1988, 1989, 1990, ... (years)
- Number Format: General
- Font:
  - Name: Aptos
  - Size: 11 pt
  - Bold: True
  - Color: Theme 1
- Alignment:
  - Horizontal: center
- Fill:
  - Type: solid
  - Color: Theme 0 (white)
- Borders:
  - Bottom: hair (thin line) on all data rows

*Numeric Data Columns (B-N - Well data):*
- Values: Float values (acre-feet per year)
- Number Format: `#,##0.00` (thousands separator, 2 decimal places)
- Font:
  - Name: Aptos
  - Size: 11 pt
  - Bold: False
  - Color: Theme 1
- Fill:
  - Type: solid
  - Color: Theme 0 (white)
- Borders:
  - Bottom: hair

*Total Column (Column O):*
- Likely contains totals for each year
- Number Format: `#,##0.00`
- Font/Fill/Borders: Same as numeric columns

#### Special Features
- **No colored rows:** All rows use Theme 0 (white) fill
- **Number formats used:** Only `#,##0.00` for all numeric data
- **Consistent borders:** All data rows have hair bottom border

### Sheet 2: Sheet1 (Supplementary)

#### Structure
- **Dimensions:** 38 rows × 2 columns
- **Range:** A1:B38

#### Column Configuration
- Columns A, B: 13.0 width

**Headers (Row 1):**
- A1: "1988"
- B1: "12"

**Data:**
- Column A: Years (1988-2024)
- Column B: Integer values (appears to be month counts)
- Number Format: General

**Last Row (38):**
- B38: Formula `=SUM(B1:B37)` - totals the B column

**Formatting:**
- No special formatting
- No bold headers
- No borders
- No fill colors
- Standard Aptos font, size 11

---

## Theme Colors Reference

Both files use Excel theme-based colors:

- **Theme 0:** Background color (typically white or light gray in the default theme)
- **Theme 1:** Text color (typically black or dark gray in the default theme)
- **RGB FFFFFF00:** Bright yellow (used for Well 3 highlighting in Table_2_2024)

When recreating these files programmatically:
- Most cells use `PatternFill(fill_type='solid', fgColor='00FFFFFF')` for white background
- Text uses default theme colors
- Well 3 in Table_2 uses `PatternFill(fill_type='solid', fgColor='FFFFFF00')` for yellow

---

## Border Styles

- **medium:** Thicker border used on header row top and bottom
- **hair:** Thin border used between data rows (bottom border of each cell)

---

## Number Format Codes

- `General`: Standard number display (no special formatting)
- `#,##0.00`: Number with thousands separator and exactly 2 decimal places
  - Examples: 16.89, 1,234.56, 0.00
- `0.0%`: Percentage with 1 decimal place (found in Table_2)

---

## Alignment Patterns

- **Header cells:** Centered horizontally
- **First column (Well/Year IDs):** Centered horizontally, Bold
- **Numeric data cells:** Default (general) alignment
- **Table 1, Header A1:** Right aligned (special case)

---

## Font Consistency

Both files use:
- Font: Aptos
- Size: 11 pt throughout
- Bold: Only for headers (Row 1) and first column (Well/Year IDs)
- No italics anywhere
- No underlines

---

## Row Heights

- Default row heights used for most rows
- No special row height settings detected
- Excel's auto-height based on 11 pt font

---

## Formulas

**Table_2_2024:**
- Column N (Total): `=SUM(B#:M#)` for each data row

**Table_1_data_afy_2024:**
- Sheet 2, Cell B38: `=SUM(B1:B37)`

---

## Key Differences Between Files

| Feature | Table_2_2024 | Table_1_data_afy_2024 |
|---------|--------------|----------------------|
| First column content | Well IDs (1-13) | Years (1988-2024) |
| Header row A1 alignment | Center | Right |
| Number of data rows | ~15 | 47 |
| Colored rows | Yes (Row 4 = yellow) | No |
| Percentage format | Yes (0.0%) | No |
| Secondary sheet | No | Yes (Sheet1) |
| Column O header | "Well" | "Total" |

---

## Notes for Programmatic Recreation

1. **Use openpyxl for Python implementation**
2. **Theme colors:** Use `Color(theme=0)` for fills, `Color(theme=1)` for text
3. **Yellow highlight:** Use `PatternFill(fill_type='solid', fgColor='FFFFFF00')` for Well 3
4. **Borders:**
   ```python
   from openpyxl.styles import Border, Side
   medium_border = Side(style='medium')
   hair_border = Side(style='hair')
   ```
5. **Number formats:** Apply to cells using `cell.number_format = '#,##0.00'`
6. **Formulas:** Write as strings starting with '=' : `cell.value = '=SUM(B2:M2)'`
7. **Column widths:** Set using `ws.column_dimensions['A'].width = 14.75`
8. **Bold font:** `Font(name='Aptos', size=11, bold=True)`
9. **Center alignment:** `Alignment(horizontal='center')`

---

*Generated: 2026-02-02*
*Analysis tool: openpyxl with Python3*
