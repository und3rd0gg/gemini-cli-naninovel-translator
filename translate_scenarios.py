import csv
import subprocess
import sys
import os
import argparse
import glob
import time
import msvcrt

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

    def _print_progress(self, iteration, total, prefix='', suffix='', decimals=1, length=40):
        if total == 0: total = 1
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
        bar = Colors.GREEN + '█' * filled_length + Colors.ENDC + '-' * (length - filled_length)
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
        sys.stdout.flush()

    def _log(self, message, progress_state=None):
        sys.stdout.write('\r' + ' ' * 100 + '\r')
        print(message)
        if progress_state:
            self._print_progress(*progress_state)

    def _scan_workload(self, files, specific_lang=None):
        """Scans headers to calculate total translation tasks (Language Columns)."""
        total_steps = 0
        file_meta = [] # (file_path, target_indices_dict)

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    header_line = f.readline()
                    if not header_line: continue
                    # Simple split is risky for CSV, but headers usually safe. 
                    # Better use csv reader for just one line.
                    pass
                
                # Re-open properly to parse header
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header or 'ru' not in header: continue
                    
                    ru_index = header.index('ru')
                    targets = {}
                    for i in range(ru_index + 1, len(header)):
                        code = header[i].strip()
                        if code:
                            if specific_lang and code != specific_lang: continue
                            targets[code] = i
                    
                    if targets:
                        total_steps += len(targets)
                        file_meta.append((file_path, targets))
            except Exception:
                continue
        return total_steps, file_meta

    def process(self, input_path, target_lang=None, prompt_name="default"):
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

        print(f"\n{Colors.HEADER}==========================================")
        print(f"       TRANSLATION TASK STARTED")
        print(f"=========================================={Colors.ENDC}")
        print(f" {Colors.BOLD}Source:{Colors.ENDC}   {input_path}")
        print(f" {Colors.BOLD}Output:{Colors.ENDC}   {root_output_dir}")
        print(f" {Colors.BOLD}Target:{Colors.ENDC}   {target_lang if target_lang else 'ALL Detected'}")
        
        # --- Pre-calculation ---
        print(f"{Colors.CYAN}Scanning files to calculate workload...{Colors.ENDC}")
        total_steps, workload_meta = self._scan_workload(files_to_process, target_lang)
        
        print(f" {Colors.BOLD}Files:{Colors.ENDC}    {len(files_to_process)}")
        print(f" {Colors.BOLD}Tasks:{Colors.ENDC}    {total_steps} languages total")
        print(f"{Colors.HEADER}=========================================={Colors.ENDC}\n")

        if total_steps == 0:
            print(f"{Colors.WARNING}Nothing to translate (check headers for 'ru' and target columns).{Colors.ENDC}")
            return

        # --- Processing Loop ---
        current_step = 0
        errors = 0
        
        # Initial Progress Bar
        self._print_progress(0, total_steps, prefix='Progress:', suffix='Starting...', length=40)

        for file_path, target_indices in workload_meta:
            rel_path = os.path.relpath(file_path, root_input_dir)
            output_file_path = os.path.join(root_output_dir, rel_path)
            
            # Read File Content Once
            try:
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    rows = list(csv.reader(f))
            except Exception as e:
                self._log(f"{Colors.FAIL}Error reading {rel_path}: {e}{Colors.ENDC}", (current_step, total_steps, 'Progress:', 'Error', 1, 40))
                errors += 1
                current_step += len(target_indices) # Skip these steps
                continue

            # Identify source text
            header = rows[0]
            ru_index = header.index('ru') # We know it exists from scan
            source_texts = [r[ru_index] if len(r) > ru_index else "" for r in rows[1:]]

            # Process per language
            for lang_code, col_index in target_indices.items():
                self._log(f"[{current_step+1}/{total_steps}] {rel_path} -> {Colors.CYAN}{lang_code}{Colors.ENDC}", 
                          (current_step, total_steps, 'Progress:', f'{lang_code}...', 1, 40))
                
                # Format Prompt
                text_block = "\n".join(source_texts)
                formatted_prompt = prompt_template.replace("{target_lang}", lang_code).replace("{text}", text_block)
                
                # Send Request
                response, error = GeminiClient.send(formatted_prompt)

                if response:
                    translated_lines = response.split('\n')
                    # Fill Data
                    for i in range(1, len(rows)):
                        row_idx = i - 1
                        if row_idx < len(translated_lines):
                            while len(rows[i]) <= col_index: rows[i].append("")
                            rows[i][col_index] = translated_lines[row_idx].strip()
                    
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
                self._print_progress(current_step, total_steps, prefix='Progress:', suffix='Working...', length=40)

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

                # 3. Select Language
                self.tui.clear()
                print(f"{Colors.HEADER}--- Translation Configuration ---{Colors.ENDC}")
                print(f"Target: {path}")
                print(f"Prompt: {selected_prompt}")
                lang = self.tui.input_text("Target language code (Leave empty for all)", default="")
                
                # Run
                self.translator.process(path, lang, selected_prompt)
                
                print(f"\n{Colors.BLUE}Press any key to continue...{Colors.ENDC}")
                msvcrt.getch()

def main():
    if len(sys.argv) > 1:
        # Legacy Headless Mode
        parser = argparse.ArgumentParser(description='Translate scenario CSV files.')
        parser.add_argument('input_path', nargs='?', default='scenarios', help='Path to input')
        parser.add_argument('--lang', type=str, help='Specific target language')
        parser.add_argument('--prompt', type=str, default='default', help='Prompt template name')
        args = parser.parse_args()
        
        pm = PromptManager()
        Translator(pm).process(args.input_path, args.lang, args.prompt)
    else:
        AppCLI().run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass