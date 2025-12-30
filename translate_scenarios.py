import csv
import subprocess
import sys
import os
import argparse
import glob
import time
import msvcrt
import json
from datetime import datetime

# --- Colors & Styles ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Backgrounds
    BG_BLUE = '\033[44m'
    BG_SELECTED = '\033[7m' # Inverse

# --- Console Helper (Windows) ---
class ConsoleInput:
    KEY_UP = 72
    KEY_DOWN = 80
    KEY_LEFT = 75
    KEY_RIGHT = 77
    KEY_ENTER = 13
    KEY_ESC = 27
    KEY_SPACE = 32
    KEY_A = 97
    KEY_A_UPPER = 65

    @staticmethod
    def get_key():
        """Reads a keypress and returns the key code."""
        key = msvcrt.getch()
        if key == b'\xe0':  # Arrow keys prefix
            key = msvcrt.getch()
            return ord(key)
        return ord(key)

# --- UI Components ---
class TUI:
    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title, subtitle=None):
        self.clear()
        print(f"{Colors.HEADER}=========================================={Colors.ENDC}")
        print(f"   {Colors.BOLD}{title}{Colors.ENDC}")
        if subtitle:
            print(f"   {subtitle}")
        print(f"{Colors.HEADER}=========================================={Colors.ENDC}\n")

    def show_menu(self, title, options, subtitle=None):
        """
        Renders a navigable menu.
        options: list of strings or tuples (label, value).
        Returns: selected index or -1 if cancelled (Esc/Left).
        """
        current_idx = 0
        while True:
            self.print_header(title, subtitle)
            
            # Instructions
            print(f"{Colors.BLUE}[↑/↓] Navigate   [Enter/→] Select   [Esc/←] Back{Colors.ENDC}\n")

            for i, option in enumerate(options):
                label = option if isinstance(option, str) else option[0]
                
                if i == current_idx:
                    # Highlighted style
                    print(f"  {Colors.CYAN}{Colors.BOLD}> {label} <{Colors.ENDC}")
                else:
                    # Normal style
                    print(f"    {label}")

            key = ConsoleInput.get_key()

            if key == ConsoleInput.KEY_UP:
                current_idx = (current_idx - 1) % len(options)
            elif key == ConsoleInput.KEY_DOWN:
                current_idx = (current_idx + 1) % len(options)
            elif key == ConsoleInput.KEY_ENTER or key == ConsoleInput.KEY_RIGHT:
                return current_idx
            elif key == ConsoleInput.KEY_ESC or key == ConsoleInput.KEY_LEFT:
                return -1

    def multiselect_menu(self, title, options, subtitle=None):
        """
        Renders a multi-select menu.
        options: list of strings (values).
        Returns: list of selected values (strings) or None if cancelled.
        """
        current_idx = 0
        selected_indices = set()
        
        # Initially select all? No, let user choose. Or maybe Select All option?
        # Let's add a virtual option "[ SELECT ALL ]" at -1 index logic if needed, 
        # but for simplicity, we just list items.

        while True:
            self.print_header(title, subtitle)
            
            # Instructions
            print(f"{Colors.BLUE}[↑/↓] Navigate   [Space] Toggle   [A] All   [Enter] Confirm   [Esc] Cancel{Colors.ENDC}\n")

            for i, option in enumerate(options):
                is_selected = i in selected_indices
                checkbox = f"{Colors.GREEN}[x]{Colors.ENDC}" if is_selected else "[ ]"
                
                label = f"{checkbox} {option}"
                
                if i == current_idx:
                    print(f"  {Colors.CYAN}{Colors.BOLD}> {label} <{Colors.ENDC}")
                else:
                    print(f"    {label}")
            
            print(f"\n{Colors.BLUE}Selected: {len(selected_indices)}/{len(options)}{Colors.ENDC}")

            key = ConsoleInput.get_key()

            if key == ConsoleInput.KEY_UP:
                current_idx = (current_idx - 1) % len(options)
            elif key == ConsoleInput.KEY_DOWN:
                current_idx = (current_idx + 1) % len(options)
            elif key == ConsoleInput.KEY_SPACE:
                if current_idx in selected_indices:
                    selected_indices.remove(current_idx)
                else:
                    selected_indices.add(current_idx)
            elif key == ConsoleInput.KEY_A or key == ConsoleInput.KEY_A_UPPER:
                if len(selected_indices) == len(options):
                    selected_indices.clear()
                else:
                    selected_indices = set(range(len(options)))
            elif key == ConsoleInput.KEY_ENTER:
                if not selected_indices:
                    # If nothing selected, maybe they want everything? 
                    # Or maybe warn? Let's assume nothing selected means nothing.
                    # But usually in this app context, empty means ALL.
                    # However, since this is explicit select, let's return selected.
                    pass
                return [options[i] for i in sorted(selected_indices)]
            elif key == ConsoleInput.KEY_ESC:
                return None

    def file_picker(self, start_path=".", allowed_extensions=None):
        """
        Navigable file explorer.
        Returns: absolute path of selected file/folder or None.
        """
        current_path = os.path.abspath(start_path)
        if not os.path.exists(current_path):
            current_path = os.getcwd()
        
        while True:
            items = []
            # Options to navigate/select
            items.append((f"{Colors.GREEN}< SELECT CURRENT FOLDER >{Colors.ENDC}", "."))
            items.append((".. (Go Up)", ".."))
            
            try:
                # List directories first
                with os.scandir(current_path) as it:
                    entries = sorted(list(it), key=lambda e: (not e.is_dir(), e.name.lower()))
                    
                    for entry in entries:
                        if entry.is_dir():
                            items.append((f"[{entry.name}]", entry.name))
                        elif entry.is_file():
                            if allowed_extensions:
                                if any(entry.name.lower().endswith(ext) for ext in allowed_extensions):
                                    items.append((entry.name, entry.name))
                            else:
                                items.append((entry.name, entry.name))
            except PermissionError:
                print(f"{Colors.FAIL}Permission denied!{Colors.ENDC}")
                time.sleep(1)
                return None

            idx = self.show_menu("File Explorer", items, subtitle=f"Current: {current_path}")

            if idx == -1:
                return None # Cancelled
            
            selected_label, selected_name = items[idx]
            
            if selected_name == ".":
                return current_path
            elif selected_name == "..":
                current_path = os.path.dirname(current_path)
            else:
                full_path = os.path.join(current_path, selected_name)
                if os.path.isdir(full_path):
                    current_path = full_path # Dive in
                else:
                    return full_path # Selected file

    def input_text(self, prompt, default=""):
        """Standard text input wrapper."""
        print(f"\n{Colors.GREEN}?{Colors.ENDC} {prompt} [{default}]: ", end="")
        val = input().strip()
        return val if val else default

# --- Prompt Manager ---
class PromptManager:
    def __init__(self, prompts_dir="prompts"):
        self.prompts_dir = prompts_dir
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)
        
        # Ensure default prompt always exists
        default_path = os.path.join(self.prompts_dir, "default.txt")
        if not os.path.exists(default_path):
            self.save_prompt("default", 
                "You are a professional translator. Translate the following scenario text from Russian (ru) to {target_lang}.\n"
                "The text is a dialogue/script for a game or story. Maintain the context, tone, and character styles.\n"
                "Output ONLY the translated lines, one per line, corresponding exactly to the input lines.\n"
                "Input:\n{text}"
            )

    def list_prompts(self):
        files = glob.glob(os.path.join(self.prompts_dir, "*.txt"))
        return [os.path.splitext(os.path.basename(f))[0] for f in files]

    def load_prompt(self, name):
        path = os.path.join(self.prompts_dir, f"{name}.txt")
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def save_prompt(self, name, content):
        path = os.path.join(self.prompts_dir, f"{name}.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

# --- Gemini Client ---
class GeminiClient:
    @staticmethod
    def send(prompt):
        try:
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
                err_msg = stderr if stderr else stdout
                return None, err_msg.strip()
            return stdout.strip(), None
        except Exception as e:
            return None, str(e)

# --- Translator Logic ---
class Translator:
    def __init__(self, prompt_manager):
        self.prompt_manager = prompt_manager

    def _print_progress(self, iteration, total, prefix='', suffix='', decimals=1, length=40, elapsed=None):
        if total == 0: total = 1
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
        bar = Colors.GREEN + '█' * filled_length + Colors.ENDC + '-' * (length - filled_length)
        
        elapsed_str = ""
        if elapsed is not None:
            mins, secs = divmod(int(elapsed), 60)
            elapsed_str = f" [{Colors.CYAN}{mins:02d}:{secs:02d}{Colors.ENDC}]"
            
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}{elapsed_str}')
        sys.stdout.flush()

    def _log(self, message, progress_state=None):
        sys.stdout.write('\r' + ' ' * 120 + '\r')
        print(message)
        if progress_state:
            self._print_progress(*progress_state)
            
    def discover_languages(self, input_path):
        """Scans path to find all unique target languages in CSV headers."""
        input_path = os.path.abspath(input_path)
        files = []
        if os.path.isfile(input_path):
            files = [input_path]
        else:
            for root, dirs, f_list in os.walk(input_path):
                for f in f_list:
                    if f.lower().endswith('.csv'):
                        files.append(os.path.join(root, f))
        
        languages = set()
        for fpath in files:
            try:
                with open(fpath, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header and 'ru' in header:
                        ru_idx = header.index('ru')
                        for i in range(ru_idx + 1, len(header)):
                            if header[i].strip():
                                languages.add(header[i].strip())
            except:
                pass
        return sorted(list(languages))

    def _scan_workload(self, files, target_langs=None):
        """
        Scans headers to calculate total translation tasks.
        target_langs: list of strings (e.g. ['en', 'jp']). If None/Empty, all are used.
        """
        total_steps = 0
        file_meta = [] # (file_path, target_indices_dict)

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    header_line = f.readline()
                    if not header_line: continue
                    # header check passed
                    pass
                
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header or 'ru' not in header: continue
                    
                    ru_index = header.index('ru')
                    targets = {}
                    for i in range(ru_index + 1, len(header)):
                        code = header[i].strip()
                        if code:
                            # Filter Logic
                            if target_langs and code not in target_langs:
                                continue
                            targets[code] = i
                    
                    if targets:
                        total_steps += len(targets)
                        file_meta.append((file_path, targets))
            except Exception:
                continue
        return total_steps, file_meta

    def _load_glossary(self, glossary_path="glossary.json"):
        """Loads the whole glossary JSON."""
        if not os.path.exists(glossary_path):
            return None
        try:
            with open(glossary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Colors.WARNING}Failed to load glossary: {e}{Colors.ENDC}")
            return None

    def process(self, input_path, target_langs=None, prompt_name="default", skip_existing=False):
        """
        target_langs: list of strings (e.g. ['en']) or None for all.
        """
        start_time = time.time()
        input_path = os.path.abspath(input_path)
        
        if not os.path.exists(input_path):
            print(f"{Colors.FAIL}Path not found: {input_path}{Colors.ENDC}")
            return

        # --- Discovery ---
        files_to_process = []
        root_input_dir = ""
        root_output_dir = ""

        if os.path.isfile(input_path):
            root_input_dir = os.path.dirname(input_path)
            files_to_process = [input_path]
            root_output_dir = f"{root_input_dir}_translated"
        else:
            root_input_dir = input_path
            root_output_dir = f"{input_path}_translated"
            for root, dirs, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith('.csv'):
                        files_to_process.append(os.path.join(root, file))

        if not files_to_process:
            print(f"{Colors.WARNING}No CSV files found.{Colors.ENDC}")
            return

        # --- Configuration Summary ---
        prompt_template = self.prompt_manager.load_prompt(prompt_name)
        if not prompt_template:
            print(f"{Colors.FAIL}Prompt '{prompt_name}' not found!{Colors.ENDC}")
            return

        # --- Load Glossary Data ---
        full_glossary = self._load_glossary()
        start_time_str = datetime.now().strftime("%H:%M:%S")

        lang_display = "ALL Detected"
        if target_langs:
            lang_display = ", ".join(target_langs)

        print(f"\n{Colors.HEADER}==========================================")
        print(f"       TRANSLATION TASK STARTED")
        print(f"=========================================={Colors.ENDC}")
        print(f" {Colors.BOLD}Start Time:{Colors.ENDC} {start_time_str}")
        print(f" {Colors.BOLD}Source:{Colors.ENDC}     {input_path}")
        print(f" {Colors.BOLD}Output:{Colors.ENDC}     {root_output_dir}")
        print(f" {Colors.BOLD}Target:{Colors.ENDC}     {lang_display}")
        print(f" {Colors.BOLD}Resume:{Colors.ENDC}     {'Yes (Skip existing)' if skip_existing else 'No (Overwrite)'}")
        if full_glossary:
             print(f" {Colors.BOLD}Glossary:{Colors.ENDC}   Loaded ({len(full_glossary)} languages defined)")
        
        # --- Pre-calculation ---
        print(f"{Colors.CYAN}Scanning files to calculate workload...{Colors.ENDC}")
        total_steps, workload_meta = self._scan_workload(files_to_process, target_langs)
        
        print(f" {Colors.BOLD}Files:{Colors.ENDC}      {len(files_to_process)}")
        print(f" {Colors.BOLD}Tasks:{Colors.ENDC}      {total_steps} languages total")
        print(f"{Colors.HEADER}=========================================={Colors.ENDC}\n")

        if total_steps == 0:
            print(f"{Colors.WARNING}Nothing to translate (check headers for 'ru' and target columns).{Colors.ENDC}")
            return

        # --- Processing Loop ---
        current_step = 0
        errors = 0
        
        # Initial Progress Bar
        self._print_progress(0, total_steps, prefix='Progress:', suffix='Starting...', length=40, elapsed=0)

        for file_path, target_indices in workload_meta:
            rel_path = os.path.relpath(file_path, root_input_dir)
            output_file_path = os.path.join(root_output_dir, rel_path)
            
            # Read File Content Once
            try:
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    rows = list(csv.reader(f))
            except Exception as e:
                elapsed = time.time() - start_time
                self._log(f"{Colors.FAIL}Error reading {rel_path}: {e}{Colors.ENDC}", (current_step, total_steps, 'Progress:', 'Error', 1, 40, elapsed))
                errors += 1
                current_step += len(target_indices) # Skip these steps
                continue

            # Identify source text
            header = rows[0]
            ru_index = header.index('ru') # We know it exists from scan

            # Process per language
            for lang_code, col_index in target_indices.items():
                elapsed = time.time() - start_time
                self._log(f"[{current_step+1}/{total_steps}] {rel_path} -> {Colors.CYAN}{lang_code}{Colors.ENDC}", 
                          (current_step, total_steps, 'Progress:', f'{lang_code}...', 1, 40, elapsed))
                
                # --- Filter for Resume Mode ---
                indices_to_process = []
                source_subset = []
                
                if skip_existing:
                    for i in range(1, len(rows)):
                        row = rows[i]
                        # Check if translation exists
                        has_translation = len(row) > col_index and row[col_index].strip() != ""
                        if not has_translation:
                            indices_to_process.append(i)
                            source_subset.append(row[ru_index] if len(row) > ru_index else "")
                    
                    if not indices_to_process:
                        self._log(f"  {Colors.GREEN}Skipped (Already translated){Colors.ENDC}", None)
                        current_step += 1
                        elapsed = time.time() - start_time
                        self._print_progress(current_step, total_steps, prefix='Progress:', suffix='Skipped', length=40, elapsed=elapsed)
                        continue
                else:
                    # Process All
                    indices_to_process = list(range(1, len(rows)))
                    source_subset = [r[ru_index] if len(r) > ru_index else "" for r in rows[1:]]

                # Prepare Glossary for THIS specific language
                glossary_text = ""
                if full_glossary and lang_code in full_glossary:
                    glossary_text = "\nGLOSSARY / TERMINOLOGY (Mandatory):\n"
                    for term, translation in full_glossary[lang_code].items():
                        glossary_text += f"- {term} -> {translation}\n"
                    glossary_text += f"Please use these exact {lang_code} translations for the terms listed above.\n"

                # Format Prompt
                text_block = "\n".join(source_subset)
                
                # Inject glossary if present
                final_prompt = prompt_template.replace("{target_lang}", lang_code)
                if "{glossary}" in final_prompt:
                     final_prompt = final_prompt.replace("{glossary}", glossary_text)
                else:
                    # Prepend glossary to text block if placeholder missing
                    final_prompt = final_prompt.replace("{text}", f"{glossary_text}\nInput:\n{text_block}")
                
                # Send Request
                response, error = GeminiClient.send(final_prompt)

                if response:
                    translated_lines = []
                    # Try JSON parsing first
                    try:
                        import json
                        # Find potential JSON array
                        start_idx = response.find('[')
                        end_idx = response.rfind(']')
                        if start_idx != -1 and end_idx != -1:
                            json_str = response[start_idx:end_idx+1]
                            translated_lines = json.loads(json_str)
                        else:
                            # Fallback to splitting if no brackets found
                            translated_lines = response.split('\\n')
                    except Exception as e:
                        self._log(f"  {Colors.WARNING}JSON Parse Error: {e}. Falling back to text split.{Colors.ENDC}", None)
                        translated_lines = response.split('\\n')

                    # Fill Data
                    for idx, map_index in enumerate(indices_to_process):
                        if idx < len(translated_lines):
                            target_row = rows[map_index]
                            while len(target_row) <= col_index: target_row.append("")
                            target_row[col_index] = str(translated_lines[idx]).strip()
                    
                    # INCREMENTAL SAVE
                    try:
                        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                        with open(output_file_path, 'w', encoding='utf-8', newline='') as f:
                            csv.writer(f).writerows(rows)
                    except Exception as e:
                        self._log(f"  {Colors.FAIL}Save Error: {e}{Colors.ENDC}", None)
                        errors += 1

                else:
                    self._log(f"  {Colors.FAIL}Translation Failed for {lang_code}: {error}{Colors.ENDC}", None)
                    errors += 1
                
                current_step += 1
                elapsed = time.time() - start_time
                self._print_progress(current_step, total_steps, prefix='Progress:', suffix='Working...', length=40, elapsed=elapsed)

        # --- Final Report ---
        elapsed = time.time() - start_time
        sys.stdout.write('\n')
        print(f"\n{Colors.HEADER}------------------------------------------{Colors.ENDC}")
        if errors == 0:
            print(f"{Colors.GREEN}✔ COMPLETED SUCCESSFULLY{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠ COMPLETED WITH {errors} ERRORS{Colors.ENDC}")
        print(f"Time elapsed: {elapsed:.2f}s")
        print(f"Total operations: {total_steps}")
        print(f"{Colors.HEADER}------------------------------------------{Colors.ENDC}")

# --- Interactive Application ---
class AppCLI:
    def __init__(self):
        self.tui = TUI()
        self.prompt_manager = PromptManager()
        self.translator = Translator(self.prompt_manager)

    def menu_prompts(self):
        while True:
            prompts = self.prompt_manager.list_prompts()
            menu_items = sorted(prompts) + ["+ Create New"]
            
            idx = self.tui.show_menu("Prompt Management", menu_items)
            
            if idx == -1: break
            
            selected = menu_items[idx]
            
            if selected == "+ Create New":
                self.tui.clear()
                print(f"{Colors.HEADER}--- Create New Prompt ---{Colors.ENDC}")
                name = self.tui.input_text("Enter prompt name (no spaces)")
                print("\nEnter prompt text (Use {target_lang} and {text} placeholders).")
                print("Type 'END' on a new line to finish:")
                lines = []
                while True:
                    line = input()
                    if line.strip() == 'END': break
                    lines.append(line)
                self.prompt_manager.save_prompt(name, "\n".join(lines))
            else:
                # View/Edit could go here, for now just view
                self.tui.clear()
                print(f"{Colors.CYAN}--- Content of '{selected}' ---{Colors.ENDC}")
                print(self.prompt_manager.load_prompt(selected))
                print(f"\n{Colors.BLUE}Press any key to return...{Colors.ENDC}")
                msvcrt.getch()

    def run(self):
        while True:
            options = [
                ("Translate Scenarios", "translate"),
                ("Manage Prompts", "prompts"),
                ("Exit", "exit")
            ]
            
            idx = self.tui.show_menu("GEMINI TRANSLATOR", options)
            if idx == -1: idx = 2 # Exit on Esc from main menu
            
            choice = options[idx][1]
            
            if choice == "exit":
                self.tui.clear()
                print("Goodbye!")
                sys.exit(0)
                
            elif choice == "prompts":
                self.menu_prompts()
                
            elif choice == "translate":
                # 1. Select Path
                path = self.tui.file_picker(start_path="scenarios", allowed_extensions=['.csv'])
                if not path: continue # User cancelled

                # 2. Select Prompt
                prompts = self.prompt_manager.list_prompts()
                if not prompts:
                    print("No prompts found!")
                    time.sleep(2)
                    continue
                    
                p_idx = self.tui.show_menu("Select Prompt Template", prompts)
                if p_idx == -1: continue
                selected_prompt = prompts[p_idx]

                # 3. Select Language (MULTI-SELECT)
                self.tui.clear()
                print(f"{Colors.CYAN}Scanning for available languages...{Colors.ENDC}")
                available_langs = self.translator.discover_languages(path)
                
                selected_langs = None
                if not available_langs:
                     print(f"{Colors.WARNING}No languages found in headers (besides 'ru'). Assuming manual override or empty.{Colors.ENDC}")
                     # Fallback to manual input if discovery failed or empty
                     manual = self.tui.input_text("Target language code (Leave empty for all)", default="")
                     if manual: selected_langs = [manual]
                else:
                    # Show Multi-select
                    print(f"{Colors.GREEN}Found {len(available_langs)} languages.{Colors.ENDC}")
                    time.sleep(0.5)
                    selected_langs = self.tui.multiselect_menu("Select Target Languages", available_langs, subtitle="Space to toggle, Enter to confirm")
                
                # If selected_langs is empty list (user pressed enter without selection), treat as None (ALL)
                if selected_langs is not None and len(selected_langs) == 0:
                    selected_langs = None

                # 4. Resume Option
                resume_input = self.tui.input_text("Skip existing translations? (y/n)", default="n")
                skip_existing = resume_input.lower().startswith('y')

                # Run
                self.translator.process(path, selected_langs, selected_prompt, skip_existing)
                
                print(f"\n{Colors.BLUE}Press any key to continue...{Colors.ENDC}")
                msvcrt.getch()

def main():
    if len(sys.argv) > 1:
        # Legacy Headless Mode
        parser = argparse.ArgumentParser(description='Translate scenario CSV files.')
        parser.add_argument('input_path', nargs='?', default='scenarios', help='Path to input')
        parser.add_argument('--lang', type=str, help='Specific target language')
        parser.add_argument('--prompt', type=str, default='default', help='Prompt template name')
        parser.add_argument('--resume', action='store_true', help='Skip already translated lines')
        args = parser.parse_args()
        
        pm = PromptManager()
        # Wrap single lang arg in list if present
        langs = [args.lang] if args.lang else None
        
        Translator(pm).process(args.input_path, langs, args.prompt, args.resume)
    else:
        AppCLI().run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
