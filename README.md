# Gemini CLI Translator Tool

A powerful Python utility designed to automate the translation of scenario/dialogue files (CSV) for games and stories using the Gemini CLI. It preserves context, tone, and character voice, making it ideal for narrative-heavy projects like visual novels.

## Key Features

- **Interactive CLI:** User-friendly terminal interface with arrow key navigation, file picker, and menus.
- **Context-Aware Translation:** Sends entire dialogue blocks to Gemini to maintain narrative consistency.
- **Prompt Management:**Create, edit, and select custom translation prompts (stored in `prompts/`).
- **Batch Processing:** Translate single files or entire directories recursively.
- **Real-time Progress:** Visual progress bar tracking translation status per language.
- **Incremental Saving:** Saves progress after every translated language to prevent data loss.
- **Cross-Platform:** Python-based, with specific support for Windows (`gemini.cmd`).

## Prerequisites

1.  **Python 3.x** installed.
2.  **Gemini CLI** installed and configured (API key set).
    - Ensure `gemini` (or `gemini.cmd` on Windows) is available in your system PATH.

## Installation

Clone this repository:
```bash
git clone https://github.com/und3rd0gg/gemini-cli-naninovel-translator.git
cd gemini-cli-naninovel-translator
```

## Usage

### Interactive Mode (Recommended)
Simply run the script without arguments to launch the interactive menu:
```bash
python translate_scenarios.py
```
- **Navigate:** Use `Up/Down` arrows.
- **Select:** Press `Enter`.
- **Back:** Press `Esc` or `Left` arrow.
- **File Picker:** Browse folders and select specific `.csv` files or choose `< SELECT CURRENT FOLDER >` to translate everything in a directory.

### Command Line Mode (Headless)
For automation or CI/CD pipelines, you can pass arguments directly:

```bash
# Translate all files in 'scenarios' folder using default prompt
python translate_scenarios.py scenarios

# Translate a specific file to English only
python translate_scenarios.py scenarios/chapter1.csv --lang en

# Use a custom prompt template named 'funny_style.txt' from prompts folder
python translate_scenarios.py scenarios --prompt funny_style
```

### Arguments
- `input_path`: Path to a `.csv` file or a directory containing them. (Default: `scenarios`)
- `--lang`: Target language code (e.g., `en`, `ja`). If omitted, translates to all languages found in the CSV header.
- `--prompt`: Name of the prompt file in `prompts/` (without `.txt` extension). (Default: `default`)

## Prompt Management
The tool looks for prompt templates in the `prompts/` directory.
- **Default:** `prompts/default.txt` is created automatically.
- **Custom Prompts:** Create new `.txt` files in this folder.
- **Placeholders:** Your prompt **MUST** include:
  - `{target_lang}`: Where the target language name/code will be inserted.
  - `{text}`: Where the source text to translate will be inserted.

Example `custom_prompt.txt`:
```text
Translate this RPG dialogue to {target_lang}. 
Keep it medieval and archaic.
Input:
{text}
```

## CSV Format
The tool expects standard CSV files with a header row.
- **Source Column:** Must be named `ru` (Russian) currently.
- **Target Columns:** Any other columns (e.g., `en`, `jp`, `fr`) are treated as targets.
- **Structure:**
  ```csv
  id, notes, ru, en, jp
  line1,,Привет,Hello,
  line2,,Пока,Bye,
  ```

## Output
Translated files are saved in a new directory with the `_translated` suffix, preserving the original folder structure.
- Input: `scenarios/intro.csv`
- Output: `scenarios_translated/intro.csv`
