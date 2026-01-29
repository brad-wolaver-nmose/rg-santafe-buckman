# Lessons Learned: PDF Data Extraction

## Summary

The original PRD assumed all PDFs were scanned images requiring OCR. In reality:
- **2 of 12 PDFs** (Jan, Dec) had embedded text from Adobe's Paper Capture
- **10 of 12 PDFs** (Feb-Nov) were raw scans from a Konica Minolta copier

Using inline Tesseract OCR on text-based PDFs **degraded** data quality, causing:
- "0.025" misread as "25.000" (decimal shift)
- "Buckman #7" misread as "Buckman #0"
- "RG-20516-S-11" misread as "RG-20516-S-ll" (ones as lowercase Ls)

## Root Cause Analysis

### What the Original Prompt Said
```
Read and OCR first page (and first page only)
```

### What It Didn't Consider
1. **PDF type heterogeneity** - Not all PDFs need OCR
2. **Text extraction alternatives** - `pdftotext` is faster and more accurate for text-based PDFs
3. **Pre-processing needs** - Raw scans should be OCR'd once upfront, not inline
4. **OCR error patterns** - Common misreads should be anticipated

---

## PRD.md Updates Needed

### 1. Add New User Story: PDF Type Detection

```markdown
### US-0XX: Detect PDF Type Before Processing
**Description:** As a developer, I need to detect whether a PDF has embedded text or is a raw scan, so I can choose the optimal extraction method.

**Acceptance Criteria:**
- [ ] Create `detect_pdf_type(pdf_path)` function
- [ ] Run pdftotext and check character count
- [ ] If >100 chars: return "text" (use direct extraction)
- [ ] If <100 chars: return "image" (needs OCR pre-processing)
- [ ] Log detection result for each PDF
- [ ] Typecheck passes
```

### 2. Add New User Story: PDF Pre-Processing

```markdown
### US-0XX: Pre-Process Raw Scanned PDFs
**Description:** As a developer, I need raw scanned PDFs converted to text-searchable format before main processing.

**Acceptance Criteria:**
- [ ] For "image" type PDFs, run ocrmypdf to embed text layer
- [ ] Use --skip-text flag to avoid re-processing already-OCR'd PDFs
- [ ] Extract only page 1 (single-page standardized copies)
- [ ] Save standardized copies with format: {year}_{MM}_{ABBREV}.pdf
- [ ] Preserve original files unchanged
- [ ] Typecheck passes
```

### 3. Add New User Story: Hybrid Extraction

```markdown
### US-0XX: Implement Hybrid Text Extraction
**Description:** As a developer, I need the script to use direct text extraction (not inline OCR) for optimal accuracy.

**Acceptance Criteria:**
- [ ] Create `extract_buckman_data_pdftotext(pdf_path)` function
- [ ] Use subprocess to call pdftotext with -layout flag
- [ ] Parse extracted text with regex patterns
- [ ] Handle OCR variations: "ll" vs "11", comma vs period decimals
- [ ] Return same (wells, total_row) structure as OCR version
- [ ] Typecheck passes
```

### 4. Update Technical Considerations Section

Add to PRD.md Technical Considerations:

```markdown
### PDF Processing Strategy

**Critical Insight:** Not all PDFs are the same. Some have embedded text (from Adobe Acrobat or other OCR tools), while others are raw scans.

| PDF Producer | Text Extractable | Processing Method |
|--------------|------------------|-------------------|
| Adobe Acrobat Paper Capture | YES | Direct pdftotext extraction |
| KONICA MINOLTA bizhub (scanner) | NO | Pre-OCR with ocrmypdf first |

**Detection Method:**
```python
def detect_pdf_type(pdf_path: str) -> str:
    result = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], capture_output=True, text=True)
    return "text" if len(result.stdout) > 100 else "image"
```

**Pre-Processing Workflow:**
1. Detect PDF type
2. For "image" PDFs: run `ocrmypdf --skip-text input.pdf output.pdf`
3. Extract page 1 only to standardized filename
4. Then run main extraction using pdftotext

### Known OCR Error Patterns

| Actual | OCR Misread | Mitigation |
|--------|-------------|------------|
| 11 | ll (lowercase L's) | Regex: `[\dl]+` then normalize |
| 0.025 | 25.000 (decimal shift) | Use pre-OCR'd text, validate ranges |
| # | * (hash as asterisk) | Regex: `[#*]` |
| 0.027 | 0,027 (period as comma) | Replace comma with period |

### System Dependencies

Add to requirements:
- `ocrmypdf` - For pre-processing raw scanned PDFs
- `poppler-utils` - Provides pdftotext for direct text extraction
- `ghostscript` - Required by ocrmypdf
```

### 5. Update Non-Goals (Move to Goals)

Remove from Non-Goals:
```markdown
- **PDF preprocessing:** Deskewing, contrast enhancement, or other image cleanup
```

Add to Goals:
```markdown
- Pre-process raw scanned PDFs with OCR before main extraction
- Use direct text extraction when possible (faster, more accurate)
```

---

## /prd_create Command Improvements

### 1. Add Input Format Discovery Questions

Add a new question category when the project involves file processing:

```markdown
### Input Format & Quality

**Question X of Y** - Understanding input characteristics prevents extraction failures.

X. What type of input files will you be processing?
   A. Native digital files (created by software, always have embedded text)
   B. Scanned documents (image-based, may need OCR)
   C. Mixed - some native, some scanned
   D. Unknown - I haven't checked
   E. [No clear recommendation]
   F. Let's brainstorm together
   G. Something else

   → Recommendation: Understanding this is critical for data processing. If "Unknown" or "Mixed",
   suggest adding a detection step to the PRD.
```

```markdown
**Question X+1 of Y** - Consistent input formats reduce errors significantly.

X+1. Have you verified all input files are consistent in format?
   A. Yes - all files from same source/system
   B. No - files from multiple sources/years
   C. No - haven't checked yet
   D. N/A - single file only
   E. [No clear recommendation]
   F. Let's brainstorm together
   G. Something else

   → If B or C: Recommend adding input validation and format detection user stories.
```

### 2. Add Extraction Method Exploration

For PDF/document processing projects, add:

```markdown
**Question X+2 of Y** - The right extraction method can 10x your accuracy.

X+2. For extracting text from PDFs, which approach fits best?
   A. Direct text extraction (pdftotext, pdfplumber) - fast, accurate for text PDFs
   B. OCR (Tesseract, pytesseract) - needed for scanned images
   C. Hybrid - detect PDF type and choose method automatically
   D. Table extraction library (tabula-py, camelot) - for structured tables
   E. Hybrid approach (Recommended: Handles both text and scanned PDFs optimally)
   F. Let's brainstorm together
   G. Something else

   → Recommendation: E. Hybrid approaches handle real-world file variability.
```

### 3. Add Pre-Processing User Story Template

Add to prd_create checklist for data processing projects:

```markdown
### Pre-Processing Stories (if applicable)
- [ ] Input format detection story (if inputs may vary)
- [ ] Input validation/standardization story (if multiple input sources)
- [ ] Pre-processing story (if raw inputs need transformation before main processing)
```

### 4. Add Error Pattern Documentation Reminder

When generating Technical Considerations for data processing PRDs:

```markdown
### Known Error Patterns (Required for data extraction projects)

Document anticipated error patterns based on:
- Input format variations
- OCR/parsing common mistakes
- Edge cases from sample data review

Example format:
| Input | Potential Error | Mitigation |
|-------|-----------------|------------|
| [describe] | [what could go wrong] | [how to handle] |
```

---

## Global CLAUDE.md Additions

Consider adding to your global CLAUDE.md:

```markdown
## Data Extraction Projects

When working on projects that extract data from files (PDFs, images, etc.):

1. **Always check input heterogeneity first**
   - Are all inputs the same type/format?
   - Use `pdfinfo` to check PDF producer/metadata
   - Use `pdftotext` to test text extractability

2. **Prefer direct extraction over OCR**
   - pdftotext is faster and more accurate for text-based PDFs
   - Only use OCR for truly image-based documents
   - Consider pre-OCR as a separate step, not inline

3. **Document error patterns upfront**
   - Sample a few inputs manually first
   - Note any OCR artifacts or format variations
   - Build regex patterns to handle known variations

4. **Validate input before processing**
   - Add pre-flight checks that flag problematic inputs
   - Better to fail fast than produce bad data silently
```

---

## Summary of Changes

| Area | Change | Impact |
|------|--------|--------|
| PRD.md | Add PDF type detection story | Prevents wrong extraction method |
| PRD.md | Add pre-processing story | Handles raw scans properly |
| PRD.md | Add hybrid extraction story | Uses best method per file |
| PRD.md | Document OCR error patterns | Enables robust regex |
| /prd_create | Add input format questions | Discovers heterogeneity early |
| /prd_create | Add extraction method question | Chooses right approach |
| /prd_create | Add pre-processing checklist | Ensures standardization step |
| CLAUDE.md | Add data extraction best practices | Global guidance |

---

## Key Takeaway

**The PRD assumed homogeneous inputs. Reality had heterogeneous inputs.**

The fix is to:
1. **Detect** input type before processing
2. **Standardize** inputs to a common format (pre-OCR)
3. **Extract** using the optimal method (pdftotext, not inline OCR)

This pattern applies to any data extraction workflow where inputs may vary.
