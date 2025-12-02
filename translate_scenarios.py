import csv
import subprocess
import sys
import os
import argparse
import shutil

def get_gemini_translation(prompt):
    """
    Sends the prompt to the Gemini CLI and returns the response.
    """
    try:
        # We use gemini.cmd to bypass PowerShell policy issues on Windows.
        command = ['cmd', '/c', 'gemini.cmd']
        
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            # If stderr is empty, sometimes error info is in stdout depending on the tool
            err_msg = stderr if stderr else stdout
            print(f"Error calling Gemini CLI: {err_msg}", file=sys.stderr)
            return None
            
        return stdout.strip()
        
    except Exception as e:
        print(f"Exception running Gemini CLI: {e}", file=sys.stderr)
        return None

def translate_csv_file(input_path, output_path, specific_lang=None):
    """
    Reads a CSV, translates content, and writes to output path.
    """
    print(f"  Processing: {os.path.basename(input_path)}")
    
    try:
        with open(input_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception as e:
        print(f"  Error reading file {input_path}: {e}")
        return

    if not rows:
        print(f"  Skipping empty file: {os.path.basename(input_path)}")
        return

    header = rows[0]
    
    # Find Source Column
    try:
        ru_index = header.index('ru')
    except ValueError:
        print(f"  Skipping {os.path.basename(input_path)}: Source column 'ru' not found in header.")
        return

    # Identify Target Columns
    target_indices = {}
    for i in range(ru_index + 1, len(header)):
        lang_code = header[i].strip()
        if lang_code:
            target_indices[lang_code] = i

    # Filter for specific language if requested
    if specific_lang:
        if specific_lang in target_indices:
            target_indices = {specific_lang: target_indices[specific_lang]}
            print(f"  - Configuration: Translating ONLY to '{specific_lang}' for this file.")
        else:
            print(f"  - Warning: Requested language '{specific_lang}' not found in {os.path.basename(input_path)}. Skipping translation for this file.")
            target_indices = {}

    if not target_indices:
        print("  - No target languages to translate for this file.")
    
    # Extract source texts
    source_texts = []
    for i in range(1, len(rows)):
        if len(rows[i]) <= ru_index:
            source_texts.append("")
        else:
            source_texts.append(rows[i][ru_index])

    # Translate loop
    total_languages_for_file = len(target_indices)
    current_lang_count = 0
    for lang_code, col_index in target_indices.items():
        current_lang_count += 1
        print(f"  - Starting translation to {lang_code} ({current_lang_count}/{total_languages_for_file})...")
        
        prompt = (
            f"You are a professional translator. Translate the following scenario text from Russian (ru) to {lang_code}.\n"
            "The text is a dialogue/script for a game or story. Maintain the context, tone, and character styles (e.g., formal vs informal, internal monologue).\n"
            "Output ONLY the translated lines, one per line, corresponding exactly to the input lines.\n"
            "Do not include any introduction, numbering, or markdown formatting like ```.\n"
            "If a line is empty, output an empty line.\n\n"
            "Input:\n"
        )
        
        for text in source_texts:
            prompt += f"{text}\n"

        translated_block = get_gemini_translation(prompt)

        if translated_block:
            print(f"  - Translation for {lang_code} received.")
            translated_lines = translated_block.strip().split('\n')
            
            # Validation and Filling
            if len(translated_lines) != len(source_texts):
                print(f"    Warning: Line count mismatch for {lang_code}. Source: {len(source_texts)}, Translated: {len(translated_lines)}. Attempting to fill best as possible.")
            
            for i in range(1, len(rows)):
                row_idx = i - 1
                if row_idx < len(translated_lines):
                    while len(rows[i]) <= col_index:
                        rows[i].append("")
                    rows[i][col_index] = translated_lines[row_idx].strip()
        else:
            print(f"    Failed to translate to {lang_code}.")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write output
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"  - File translated and saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Translate scenario CSV files using Gemini.')
    parser.add_argument('input_path', nargs='?', default='scenarios', help='Path to input folder or specific file (default: "scenarios")')
    parser.add_argument('--lang', type=str, help='Specific target language code to translate (e.g., "en").')
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_path)

    if not os.path.exists(input_path):
        print(f"Error: Input path '{input_path}' does not exist.")
        return

    # Determine Root Dir and Output Dir
    root_input_dir = ""
    root_output_dir = ""
    files_to_process = []

    if os.path.isfile(input_path):
        # Single file mode
        root_input_dir = os.path.dirname(input_path)
        files_to_process = [input_path]
        root_output_dir = f"{root_input_dir}_translated"
    else:
        # Directory mode
        root_input_dir = input_path
        root_output_dir = f"{input_path}_translated"
        for root, dirs, files in os.walk(input_path):
            for file in files:
                if file.lower().endswith('.csv'):
                    files_to_process.append(os.path.join(root, file))

    print(f"Starting translation process.")
    print(f"Input path: {input_path}")
    print(f"Output root directory: {root_output_dir}")
    
    if not files_to_process:
        print("No CSV files found to process.")
        return

    total_files = len(files_to_process)
    for i, file_path in enumerate(files_to_process):
        print(f"\n--- Processing file {i+1} of {total_files}: {os.path.relpath(file_path, root_input_dir)} ---")
        
        # Calculate relative path to maintain structure
        rel_path = os.path.relpath(file_path, root_input_dir)
        
        # Construct full output path
        output_file_path = os.path.join(root_output_dir, rel_path)
        
        translate_csv_file(file_path, output_file_path, args.lang)

    print("\nAll translation tasks completed.")

if __name__ == "__main__":
    main()