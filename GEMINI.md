# Translation Automation Tool

## Project Overview

This project is a Python-based utility designed to automate the translation of scenario/dialogue files (in CSV format) using the Gemini CLI. It is specifically tailored for game development or story writing contexts, where maintaining tone, context, and character voice is crucial.

The tool reads CSV files where the source language (Russian, `ru`) is in one column, and target languages are defined in the headers of subsequent columns. It sends the dialogue in batches to the Gemini model to ensure context-aware translation and populates the corresponding columns in a new output file.

## Key Features

-   **Context-Aware Translation:** Sends entire dialogue blocks to Gemini to preserve context and tone.
-   **Batch Processing:** Can process entire directories of CSV files recursively, maintaining the folder structure in the output.
-   **Single File Support:** Can target specific files for quick testing or individual updates.
-   **Language Selection:** Supports translating to all languages defined in the CSV header or a specific target language via command-line arguments.
-   **Windows Compatibility:** Specifically designed to work with `gemini.cmd` to bypass PowerShell execution policy issues on Windows systems.

## Prerequisites

-   **Python 3.x**
-   **Gemini CLI:** Must be installed and configured (API key set). The script expects `gemini.cmd` to be available in the system PATH.

## Usage

The main entry point is the `translate_scenarios.py` script.

### Basic Command

Translate all CSV files in the default `scenarios` directory to all languages found in their headers:

```bash
python translate_scenarios.py
```

### Specify Input Path

Translate a specific folder or file:

```bash
# Translate a specific folder
python translate_scenarios.py path/to/my_folder

# Translate a specific file
python translate_scenarios.py path/to/my_folder/dialogue.csv
```

### Specify Target Language

Translate only to a specific language (e.g., English `en`):

```bash
python translate_scenarios.py --lang en
```

### Combined Usage

```bash
python translate_scenarios.py scenarios/chapter1.csv --lang ja
```

## Output

The tool creates a new directory (or file) with the suffix `_translated` next to the input source.

-   Input: `scenarios/` -> Output: `scenarios_translated/`
-   Input: `data/story.csv` -> Output: `data_translated/story.csv`

The internal folder structure of the input directory is preserved in the output directory.

## CSV Format Expectation

The tool expects CSV files with a header row.
-   **Source Column:** Must be named `ru`.
-   **Target Columns:** Any other columns in the header are treated as target language codes (e.g., `en`, `fr`, `jp`).
-   **Structure:** `#, ;;, ru, en, fr, ...`

## Development Notes

-   **Script:** `translate_scenarios.py`
-   **Logic:**
    -   Reads the `ru` column.
    -   Constructs a prompt for Gemini including all text lines to maintain context.
    -   Parses the response and fills the target language column.
    -   Writes the result to a new file.
-   **Error Handling:** The script includes basic error handling for missing files, mismatched line counts, and CLI execution errors.
