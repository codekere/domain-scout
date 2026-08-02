import sys
import os
import subprocess

if sys.platform == 'win32':
    os.system('chcp 65001 >nul')
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import string
import threading
import itertools
import json
import tempfile
import datetime
import keyboard

try:
    import questionary
except ImportError:
    print("[!] Library 'questionary' not found. Please run: py -m pip install questionary")
    sys.exit(1)

os.system('color')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
MASTER_LOG_FILE = os.path.join(BASE_DIR, "domain_scout_master.log")
ERROR_LOG_FILE = os.path.join(BASE_DIR, "domain_scout_error.log")

DEFAULT_CONFIG = {
    "length": 4,
    "charset": "Alphanumeric (a-z, 0-9)",
    "case_style": "Lowercase (a-z)",
    "vowels": 0,
    "mode": "Random",
    "extensions": [".com"],
    "delay": 2,
    "limit": 50,
    "headless": True,
    "log_statuses": ["[+]", "[-]", "[~]", "[*]"],
    "recheck_statuses": ["[+]"],
    "timestamp_format": "YYYY-MM-DD HH:mm:SS.ms"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def log_error(error_message):
    try:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ERROR: {error_message}\n")
    except Exception:
        pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        log_error(f"Failed to save configuration: {e}")

def format_timestamp(fmt_string):
    now = datetime.datetime.now()
    ms_val = f"{now.microsecond:06d}"[:3]
    formatted = fmt_string \
        .replace("YYYY", now.strftime("%Y")) \
        .replace("YY", now.strftime("%y")) \
        .replace("MM", now.strftime("%m")) \
        .replace("DD", now.strftime("%d")) \
        .replace("HH", now.strftime("%H")) \
        .replace("mm", now.strftime("%M")) \
        .replace("SS", now.strftime("%S")) \
        .replace("ms", ms_val)
    return f"[{formatted}]"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class Spinner:
    def __init__(self, message="Processing..."):
        self.spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        self.stop_signal = threading.Event()
        self.message = message
        self.thread = None
        self.is_running = False

    def spin(self):
        while not self.stop_signal.is_set():
            sys.stdout.write(f"\r{Colors.CYAN}{next(self.spinner)}{Colors.RESET} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 15) + '\r')
        sys.stdout.flush()

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()

    def stop(self):
        if self.is_running:
            self.stop_signal.set()
            self.thread.join()
            self.is_running = False

class DomainGenerator:
    def __init__(self, length, charset_type, min_vowels, mode, case_style):
        self.length = length
        self.charset_type = charset_type
        self.min_vowels = min_vowels
        self.mode = mode 
        self.case_style = case_style
        
        letters = string.ascii_uppercase if case_style == 'Uppercase (A-Z)' else string.ascii_lowercase
        if 'Letters Only' in charset_type:
            self.pool = letters
        elif 'Numbers Only' in charset_type:
            self.pool = string.digits
        else: 
            self.pool = letters + string.digits

        self.vowels = set('aeiou')
        if 'Sequential' in mode:
            self.indices = [0] * length

    def _is_valid_vowels(self, word):
        if 'Numbers Only' in self.charset_type:
            return True
        vowel_count = sum(1 for char in word.lower() if char in self.vowels)
        return vowel_count >= self.min_vowels

    def generate(self):
        while True:
            if 'Random' in self.mode:
                word = ''.join(random.choices(self.pool, k=self.length))
                if self._is_valid_vowels(word):
                    return word
            else:
                word = ''.join(self.pool[i] for i in self.indices)
                for i in range(self.length - 1, -1, -1):
                    self.indices[i] += 1
                    if self.indices[i] < len(self.pool):
                        break
                    self.indices[i] = 0
                else:
                    self.indices = [0] * self.length
                if self._is_valid_vowels(word):
                    return word

class DomainScout:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.spinner = None
        self.paused = False
        
        try:
            keyboard.add_hotkey('space', self.toggle_pause)
        except Exception:
            pass

    def toggle_pause(self):
        self.paused = not self.paused

    def print_banner(self):
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
    ____                        _      _____                  __ 
   / __ \\____  ____ ___  ____ _(_)___ / ___/_________  __  __/ /_
  / / / / __ \\/ __ `__ \\/ __ `/ / __ \\\\__ \\/ ___/ __ \\/ / / / __/
 / /_/ / /_/ / / / / / / /_/ / / / / /__/ / /__/ /_/ / /_/ / /_  
/_____/\\____/_/ /_/ /_/\\__,_/_/_/ /_/____/\\___/\\____/\\__,_/\\__/  
{Colors.YELLOW}>> DomainScout by Code Cere | v3.2.5 <<{Colors.RESET}
        """
        print(banner)

    def print_session_box(self):
        c = self.config
        exts_str = ", ".join(c['extensions'])
        box = f"""
{Colors.BLUE}+--------------------------------------------------------------+
|                  ACTIVE SCAN SESSION INFO                    |
+--------------------------------------------------------------+
| • Length     : {str(c['length']).ljust(45)} |
| • Charset    : {c['charset'][:45].ljust(45)} |
| • Case Style : {c['case_style'][:45].ljust(45)} |
| • Mode       : {c['mode'][:45].ljust(45)} |
| • Extensions : {exts_str[:45].ljust(45)} |
| • Delay      : {(str(c['delay']) + 's').ljust(45)} |
| • Limit      : {str(c['limit']).ljust(45)} |
+--------------------------------------------------------------+{Colors.RESET}
"""
        print(box)

    def initialize_browser(self):
        if self.driver:
            return
        self.spinner = Spinner("Initializing stealth browser & rotating fingerprint...")
        self.spinner.start()
        
        options = Options()
        temp_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={temp_dir}")
        options.add_argument('--log-level=3')
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        
        if self.config['headless']:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
        except Exception as e:
            self.spinner.stop()
            log_error(f"Browser initialization failed: {e}")
            print(f"\n{Colors.RED}[!] Browser initialization failed: {e}{Colors.RESET}")
            sys.exit(1)
            
        self.spinner.stop()
        print(f"{Colors.GREEN}[✓] Stealth browser initialized successfully.{Colors.RESET}\n")

    def parse_status(self, soup, domain):
        try:
            text_nodes = soup.find_all(string=lambda t: t and domain.lower() in t.lower())
            for node in text_nodes:
                parent = node.parent
                for _ in range(6):
                    if not parent:
                        break
                    html_str = str(parent)
                    if 'bg-green-' in html_str:
                        return "AVAILABLE"
                    if 'bg-red-' in html_str:
                        return "TAKEN"
                    if 'bg-blue-' in html_str:
                        return "AFTERMARKET"
                    if 'bg-amber-' in html_str or 'bg-yellow-' in html_str:
                        return "PREMIUM"
                    parent = parent.parent
        except Exception as e:
            log_error(f"Error parsing domain status for {domain}: {e}")
        return "UNKNOWN"

    def check_batch(self, keyword):
        try:
            if not self.driver:
                self.initialize_browser()
                
            url = f"https://instantdomainsearch.com/?q={keyword}"
            self.driver.get(url)
            
            WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((By.TAG_NAME, "span"))
            )
            time.sleep(float(self.config['delay']))
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            results = {}
            for ext in self.config['extensions']:
                full_domain = f"{keyword}{ext}"
                results[ext] = self.parse_status(soup, full_domain)
            return results
        except Exception as e:
            log_error(f"Check batch error for keyword '{keyword}': {e}")
            return {ext: "UNKNOWN" for ext in self.config['extensions']}

    def write_log(self, domain, status):
        badge_map = {
            "AVAILABLE": "[+]",
            "TAKEN": "[-]",
            "AFTERMARKET": "[~]",
            "PREMIUM": "[*]"
        }
        badge = badge_map.get(status, "[?]")
        allowed_statuses = self.config.get("log_statuses", ["[+]", "[-]", "[~]", "[*]"])
        
        if badge not in allowed_statuses and badge != "[?]":
            return

        timestamp_fmt = self.config.get('timestamp_format', 'YYYY-MM-DD HH:mm:SS.ms')
        entry = f"{badge} {domain.lower()} {format_timestamp(timestamp_fmt)}\n"
        
        existing_lines = []
        if os.path.exists(MASTER_LOG_FILE):
            try:
                with open(MASTER_LOG_FILE, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()
            except Exception:
                pass
                
        filtered_lines = []
        for l in existing_lines:
            parts = l.strip().split()
            if len(parts) >= 2:
                logged_domain = parts[1].lower()
                if logged_domain == domain.lower():
                    continue
            filtered_lines.append(l)
            
        filtered_lines.append(entry)
        
        top_badges = ("[-]", "[~]", "[*]")
        top_lines = [l for l in filtered_lines if l.strip().startswith(top_badges)]
        other_lines = [l for l in filtered_lines if not l.strip().startswith(top_badges)]
        
        try:
            with open(MASTER_LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(top_lines + other_lines)
        except Exception as e:
            log_error(f"Failed to write master log: {e}")

    def modify_filters(self):
        last_keyword = "Length"
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self.print_banner()
            print(f"\n{Colors.CYAN}[*] SETTINGS & CONFIGURATION MENU{Colors.RESET}")
            
            c = self.config
            choices_dict = {
                f"Length [{c['length']}]": "Length",
                f"Charset [{c['charset']}]": "Charset",
                f"Case Style [{c['case_style']}]": "Case Style",
                f"Mode [{c['mode']}]": "Mode",
                f"Extensions [{', '.join(c['extensions'])}]": "Extensions",
                f"Search Delay [{c['delay']}s]": "Search Delay",
                f"Target Limit [{c['limit']}]": "Target Limit",
                f"Headless Mode [{c['headless']}]": "Headless Mode",
                f"Logging Statuses [{', '.join(c['log_statuses'])}]": "Logging Statuses",
                f"Default Recheck Statuses [{', '.join(c['recheck_statuses'])}]": "Default Recheck Statuses",
                f"Timestamp Format Template [{c['timestamp_format']}]": "Timestamp Format Template",
                "Exit": "Exit"
            }
            choices_list = list(choices_dict.keys())
            
            default_choice = choices_list[0]
            for ch, kw in choices_dict.items():
                if kw == last_keyword:
                    default_choice = ch
                    break

            choice = questionary.select(
                "Select a setting to modify:",
                choices=choices_list,
                default=default_choice
            ).ask()

            if not choice or "Exit" in choice:
                break

            selected_keyword = choices_dict.get(choice, "")
            last_keyword = selected_keyword

            if selected_keyword == "Length":
                len_options = ["3", "4", "5", "6"]
                default_len_idx = len_options.index(str(c['length'])) if str(c['length']) in len_options else 1
                l_choice = questionary.select(
                    "Select target domain character length:", 
                    choices=len_options,
                    default=len_options[default_len_idx]
                ).ask()
                if l_choice:
                    self.config['length'] = int(l_choice)

            elif selected_keyword == "Charset":
                charset_options = ["Letters Only (a-z)", "Numbers Only (0-9)", "Alphanumeric (a-z, 0-9)"]
                c_choice = questionary.select(
                    "Select character permutation set:", 
                    choices=charset_options,
                    default=c['charset'] if c['charset'] in charset_options else charset_options[2]
                ).ask()
                if c_choice:
                    self.config['charset'] = c_choice

            elif selected_keyword == "Case Style":
                case_options = ["Lowercase (a-z)", "Uppercase (A-Z)"]
                case_choice = questionary.select(
                    "Select letter case style:", 
                    choices=case_options,
                    default=c['case_style'] if c['case_style'] in case_options else case_options[0]
                ).ask()
                if case_choice:
                    self.config['case_style'] = case_choice

            elif selected_keyword == "Mode":
                mode_options = ["Random", "Sequential (aaaa, aaab...)"]
                m_choice = questionary.select(
                    "Select generation mode:", 
                    choices=mode_options,
                    default=c['mode'] if c['mode'] in mode_options else mode_options[0]
                ).ask()
                if m_choice:
                    self.config['mode'] = m_choice

            elif selected_keyword == "Extensions":
                current_exts = c.get("extensions", [".com"])
                ext_choices = [
                    questionary.Choice(ext, checked=(ext in current_exts))
                    for ext in [".com", ".net", ".org", ".io", ".co", ".ai", ".xyz"]
                ]
                new_exts = questionary.checkbox(
                    "Select target domain extensions:", 
                    choices=ext_choices
                ).ask()
                if new_exts is not None and len(new_exts) > 0:
                    self.config['extensions'] = new_exts

            elif selected_keyword == "Search Delay":
                d_input = questionary.text("Enter search delay in seconds:", default=str(c['delay'])).ask()
                try:
                    self.config['delay'] = float(d_input) if '.' in d_input else int(d_input)
                except Exception:
                    pass

            elif selected_keyword == "Target Limit":
                l_input = questionary.text("Enter target limit (0 for infinite):", default=str(c['limit'])).ask()
                if l_input.isdigit():
                    self.config['limit'] = int(l_input)

            elif selected_keyword == "Headless Mode":
                h_choice = questionary.confirm("Run in stealth headless mode?", default=c['headless']).ask()
                self.config['headless'] = h_choice

            elif selected_keyword == "Logging Statuses":
                current_logs = c.get("log_statuses", ["[+]", "[-]", "[~]", "[*]"])
                log_choices = [
                    questionary.Choice("Available ([+])", value="[+]", checked=("[+]" in current_logs)),
                    questionary.Choice("Taken ([-])", value="[-]", checked=("[-]" in current_logs)),
                    questionary.Choice("Aftermarket ([~])", value="[~]", checked=("[~]" in current_logs)),
                    questionary.Choice("Premium ([*])", value="[*]", checked=("[*]" in current_logs)),
                ]
                new_log_st = questionary.checkbox(
                    "Select which status types to save into master log:",
                    choices=log_choices
                ).ask()
                if new_log_st is not None:
                    self.config['log_statuses'] = new_log_st

            elif selected_keyword == "Default Recheck Statuses":
                current_rechecks = c.get("recheck_statuses", ["[+]"])
                recheck_choices = [
                    questionary.Choice("Available ([+])", value="[+]", checked=("[+]" in current_rechecks)),
                    questionary.Choice("Taken ([-])", value="[-]", checked=("[-]" in current_rechecks)),
                    questionary.Choice("Aftermarket ([~])", value="[~]", checked=("[~]" in current_rechecks)),
                    questionary.Choice("Premium ([*])", value="[*]", checked=("[*]" in current_rechecks)),
                ]
                new_recheck_st = questionary.checkbox(
                    "Select default status types for rechecker:",
                    choices=recheck_choices
                ).ask()
                if new_recheck_st is not None:
                    self.config['recheck_statuses'] = new_recheck_st

            elif selected_keyword == "Timestamp Format Template":
                ts_input = questionary.text(
                    "Enter custom timestamp format template:",
                    default=c.get("timestamp_format", "YYYY-MM-DD HH:mm:SS.ms")
                ).ask()
                if ts_input:
                    self.config['timestamp_format'] = ts_input

            save_config(self.config)

    def show_pause_help(self):
        print(f"\n{Colors.CYAN}--- PAUSE HELP & SHORTCODES ---")
        print(" [SPACE] : Resume hunting process")
        print(" [M]     : Modify local configuration settings")
        print(" [H]     : Show this help menu")
        print(" [CTRL+C]: Stop/Exit process safely")
        print("--------------------------------")
        print(" SYMBOL LEGEND:")
        print(" [+]     : Available (Domain is free to register)")
        print(" [-]     : Taken (Domain is already registered)")
        print(" [~]     : Aftermarket (Domain is on sale/aftermarket)")
        print(" [*]     : Premium (Domain is premium priced)")
        print(f"--------------------------------{Colors.RESET}\n")

    def recheck_log_file(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()
        print(f"\n{Colors.CYAN}[*] Rechecking log file statuses using primary scan engine...")
        print(f"[*] Shortcuts: Press [S] to STOP recheck, or [CTRL+C] to exit safely.{Colors.RESET}")
        
        if not os.path.exists(MASTER_LOG_FILE):
            print(f"{Colors.RED}[!] No master log file found at {MASTER_LOG_FILE}{Colors.RESET}")
            input("\nPress Enter to return...")
            return

        with open(MASTER_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            print(f"{Colors.YELLOW}[!] Log file is empty.{Colors.RESET}")
            input("Press Enter to return...")
            return

        current_rechecks = self.config.get("recheck_statuses", ["[+]"])
        recheck_choices = [
            questionary.Choice("Available ([+])", value="[+]", checked=("[+]" in current_rechecks)),
            questionary.Choice("Taken ([-])", value="[-]", checked=("[-]" in current_rechecks)),
            questionary.Choice("Aftermarket ([~])", value="[~]", checked=("[~]" in current_rechecks)),
            questionary.Choice("Premium ([*])", value="[*]", checked=("[*]" in current_rechecks)),
        ]
        
        selected_badges = questionary.checkbox(
            "Select which status types to recheck:",
            choices=recheck_choices
        ).ask()

        if not selected_badges:
            print(f"{Colors.YELLOW}[!] No status selected. Returning to main menu...{Colors.RESET}")
            input("Press Enter to return...")
            return

        self.initialize_browser()

        updated_lines = []
        stopped_early = False

        try:
            for line in lines:
                try:
                    if keyboard.is_pressed('s') or keyboard.is_pressed('S'):
                        print(f"\n{Colors.YELLOW}[!] Stop requested by user. Returning to main menu...{Colors.RESET}")
                        stopped_early = True
                        updated_lines.append(line)
                        break
                except Exception:
                    pass

                line_str = line.strip()
                if not line_str:
                    continue
                
                parts = line_str.split()
                if len(parts) < 2:
                    updated_lines.append(line)
                    continue

                current_badge = parts[0]
                dom = parts[1]

                if current_badge not in selected_badges:
                    updated_lines.append(line)
                    continue

                if '.' not in dom:
                    updated_lines.append(line)
                    continue

                keyword, ext = dom.split('.', 1)
                ext_formatted = f".{ext}"

                old_exts = self.config['extensions']
                self.config['extensions'] = [ext_formatted]
                batch_results = self.check_batch(keyword)
                self.config['extensions'] = old_exts

                new_status = batch_results.get(ext_formatted, "UNKNOWN")
                timestamp_fmt = self.config.get('timestamp_format', 'YYYY-MM-DD HH:mm:SS.ms')

                badge_map = {"AVAILABLE": "[+]", "TAKEN": "[-]", "AFTERMARKET": "[~]", "PREMIUM": "[*]"}
                badge = badge_map.get(new_status, "[?]")

                if new_status == "AVAILABLE":
                    status_colored = f"{Colors.GREEN}{new_status}{Colors.RESET}"
                elif new_status == "TAKEN":
                    status_colored = f"{Colors.RED}{new_status}{Colors.RESET}"
                elif new_status == "AFTERMARKET":
                    status_colored = f"{Colors.BLUE}{new_status}{Colors.RESET}"
                elif new_status == "PREMIUM":
                    status_colored = f"{Colors.YELLOW}{new_status}{Colors.RESET}"
                else:
                    status_colored = f"{Colors.YELLOW}{new_status}{Colors.RESET}"

                new_log_entry = f"{badge} {dom} {format_timestamp(timestamp_fmt)}\n"
                updated_lines.append(new_log_entry)
                print(f" • Rechecked {dom} -> Status: {status_colored}")

            if stopped_early and len(updated_lines) < len(lines):
                updated_lines.extend(lines[len(updated_lines):])

            top_badges = ("[-]", "[~]", "[*]")
            top_lines = [l for l in updated_lines if l.strip().startswith(top_badges)]
            other_lines = [l for l in updated_lines if not l.strip().startswith(top_badges)]

            with open(MASTER_LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(top_lines + other_lines)

        except Exception as e:
            log_error(f"Error during recheck process: {e}")
            print(f"\n{Colors.RED}[!] Error during recheck: {e}{Colors.RESET}")
        finally:
            if self.driver:
                print(f"\n{Colors.CYAN}[*] Terminating browser and clearing memory...{Colors.RESET}")
                try:
                    self.driver.quit()
                    self.driver = None
                except Exception as e:
                    log_error(f"Error terminating browser during recheck: {e}")

        print(f"{Colors.GREEN}[✓] Log recheck completed!{Colors.RESET}")

        has_unwanted = False
        try:
            with open(MASTER_LOG_FILE, "r", encoding="utf-8") as f:
                current_lines = f.readlines()
            has_unwanted = any(l.strip().startswith(("[-]", "[~]", "[*]")) for l in current_lines)
        except Exception:
            pass

        if has_unwanted:
            delete_choice = questionary.confirm("Would you like to delete all [-], [~], and [*] entries from the log?").ask()
            if delete_choice:
                try:
                    cleaned_lines = [l for l in current_lines if not l.strip().startswith(("[-]", "[~]", "[*]"))]
                    with open(MASTER_LOG_FILE, "w", encoding="utf-8") as f:
                        f.writelines(cleaned_lines)
                    print(f"{Colors.GREEN}[✓] All [-], [~], and [*] entries have been successfully deleted from the log!{Colors.RESET}")
                except Exception as e:
                    log_error(f"Error deleting unwanted entries from log: {e}")

        input("Press Enter to return to main menu...")

    def run(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()
        self.initialize_browser()
        self.print_session_box()
        
        generator = DomainGenerator(
            length=self.config['length'],
            charset_type=self.config['charset'],
            min_vowels=self.config['vowels'],
            mode=self.config['mode'],
            case_style=self.config['case_style']
        )
        
        checks_completed = 0
        limit = self.config['limit']
        
        print(f"{Colors.YELLOW}[!] Shortcuts: Press [SPACE] to PAUSE | Press [CTRL+C] to STOP | When paused, press [M] to modify, [H] for help.{Colors.RESET}\n")
        
        try:
            while limit == 0 or checks_completed < limit:
                keyword = generator.generate()
                checks_completed += 1
                
                if self.paused:
                    if self.spinner:
                        self.spinner.stop()
                    print(f"\n{Colors.YELLOW}[⏸] PROCESS PAUSED. Press [SPACE] to Resume, [M] to Modify, [H] for Help.{Colors.RESET}")
                    
                    while self.paused:
                        if keyboard.is_pressed('m') or keyboard.is_pressed('M'):
                            time.sleep(0.3)
                            self.modify_filters()
                            generator = DomainGenerator(
                                length=self.config['length'],
                                charset_type=self.config['charset'],
                                min_vowels=self.config['vowels'],
                                mode=self.config['mode'],
                                case_style=self.config['case_style']
                            )
                            self.print_session_box()
                            print(f"{Colors.YELLOW}[⏸] Still paused. Press [SPACE] to resume execution.{Colors.RESET}")
                        elif keyboard.is_pressed('h') or keyboard.is_pressed('H'):
                            time.sleep(0.3)
                            show_help()
                        time.sleep(0.1)
                    
                    print(f"{Colors.GREEN}[▶] RESUMING HUNT...{Colors.RESET}\n")

                self.spinner = Spinner(f"Target locked batch: {Colors.BOLD}{keyword}{Colors.RESET} ...")
                self.spinner.start()
                
                batch_results = self.check_batch(keyword)
                
                self.spinner.stop()
                self.spinner = None
                
                count_str = f"[{checks_completed}]"
                line_output = f"{count_str} {keyword:<14} |"
                
                for ext, status in batch_results.items():
                    domain_target = f"{keyword}{ext}"
                    self.write_log(domain_target, status)
                    
                    if status == "AVAILABLE":
                        badge = f"{Colors.GREEN}{Colors.BOLD}{ext}:[+]{Colors.RESET}"
                    elif status == "AFTERMARKET":
                        badge = f"{Colors.BLUE}{ext}:[~]{Colors.RESET}"
                    elif status == "PREMIUM":
                        badge = f"{Colors.YELLOW}{ext}:[*]{Colors.RESET}"
                    elif status == "TAKEN":
                        badge = f"{Colors.RED}{ext}:[-]{Colors.RESET}"
                    else:
                        badge = f"{Colors.YELLOW}{ext}:[?]{Colors.RESET}"
                    
                    line_output += f"  {badge}"
                
                print(line_output)
                        
        except KeyboardInterrupt:
            if self.spinner:
                self.spinner.stop()
            print(f"\n\n{Colors.YELLOW}[!] Execution manually aborted by user via Ctrl+C.{Colors.RESET}")
        except Exception as e:
            if self.spinner:
                self.spinner.stop()
            log_error(f"Critical system error in main loop: {e}")
            print(f"\n{Colors.RED}[!] Critical system error! Logged to {ERROR_LOG_FILE}. Error: {e}{Colors.RESET}")
        finally:
            if self.driver:
                print(f"\n{Colors.CYAN}[*] Terminating browser and clearing memory...{Colors.RESET}")
                try:
                    self.driver.quit()
                except Exception as e:
                    log_error(f"Error closing browser: {e}")
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}=== SESSION ENDED - UNIFIED LOG PATH ==={Colors.RESET}")
            print(f" • Master Log File : {os.path.abspath(MASTER_LOG_FILE)}")
            print(f"{Colors.GREEN}==========================================={Colors.RESET}")
            input("\nPress Enter to return to main menu...")

def run_file_diagnostics():
    status_report = {}

    if not os.path.exists(CONFIG_FILE):
        status_report['config'] = ("[!] Missing (Will use default)", Colors.YELLOW)
    else:
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                json.load(f)
            status_report['config'] = ("[✓] OK (Valid JSON)", Colors.GREEN)
        except Exception:
            status_report['config'] = ("[X] Corrupt (Invalid format)", Colors.RED)

    if not os.path.exists(ERROR_LOG_FILE) or os.path.getsize(ERROR_LOG_FILE) == 0:
        status_report['error'] = ("[✓] Clean (No errors logged)", Colors.GREEN)
    else:
        try:
            with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            status_report['error'] = (f"[!] Exists ({len(lines)} entries)", Colors.YELLOW)
        except Exception:
            status_report['error'] = ("[X] Error reading file", Colors.RED)

    if not os.path.exists(MASTER_LOG_FILE):
        status_report['master'] = ("[!] Missing / Empty", Colors.YELLOW)
    else:
        try:
            with open(MASTER_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            status_report['master'] = (f"[✓] OK ({len(lines)} entries)", Colors.GREEN)
        except Exception:
            status_report['master'] = ("[X] Error reading file", Colors.RED)

    return status_report

def display_file_contents(filename, label):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\n{Colors.CYAN}[*] {label}{Colors.RESET}\n")
    if not os.path.exists(filename):
        print(f"{Colors.YELLOW}[!] File does not exist.{Colors.RESET}")
    else:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                print(f"{Colors.YELLOW}[!] File is empty.{Colors.RESET}")
            else:
                print(f"{Colors.GREEN}--- BEGIN LOG ---{Colors.RESET}")
                print(content)
                print(f"{Colors.GREEN}--- END LOG ---{Colors.RESET}")
    input("\nPress Enter to return...")

def log_management_menu():
    last_choice_text = "View Master Log"
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        app_dummy = DomainScout(load_config())
        app_dummy.print_banner()

        status = run_file_diagnostics()
        
        def format_diag_line(label, text_color_tuple):
            text, color = text_color_tuple
            padded_text = text.ljust(42)
            colored_text = f"{color}{padded_text}{Colors.RESET}"
            return f"{Colors.BLUE}| • {label.ljust(12)}: {colored_text} {Colors.BLUE}|{Colors.RESET}"

        print(f"{Colors.BLUE}+--------------------------------------------------------------+")
        print(f"|                  SYSTEM DIAGNOSTICS & HEALTH                 |")
        print(f"+--------------------------------------------------------------+")
        print(format_diag_line("Master Log", status['master']))
        print(format_diag_line("Error Log", status['error']))
        print(format_diag_line("Config File", status['config']))
        print(f"{Colors.BLUE}+--------------------------------------------------------------+{Colors.RESET}\n")

        choices_list = [
            "View Master Log",
            "View Error Log",
            "View Config Data",
            questionary.Separator(),
            "Clear & Delete Master Log",
            "Clear & Delete Error Log",
            "Reset Config File to Default",
            questionary.Separator(),
            "Exit"
        ]

        valid_choices = [c for c in choices_list if isinstance(c, str)]
        default_val = last_choice_text if last_choice_text in valid_choices else valid_choices[0]

        choice = questionary.select(
            "Log Management Options:",
            choices=choices_list,
            default=default_val
        ).ask()

        if not choice or choice == "Exit":
            break

        if isinstance(choice, str):
            last_choice_text = choice

        if choice == "View Master Log":
            display_file_contents(MASTER_LOG_FILE, "MASTER LOG VIEWER")
        elif choice == "View Error Log":
            display_file_contents(ERROR_LOG_FILE, "ERROR LOG VIEWER")
        elif choice == "View Config Data":
            display_file_contents(CONFIG_FILE, "CONFIG FILE DATA")
        elif choice == "Clear & Delete Master Log":
            if questionary.confirm("Are you sure you want to completely DELETE the Master Log?").ask():
                if os.path.exists(MASTER_LOG_FILE):
                    os.remove(MASTER_LOG_FILE)
                print(f"{Colors.GREEN}[✓] Master Log deleted.{Colors.RESET}")
                time.sleep(1)
        elif choice == "Clear & Delete Error Log":
            if questionary.confirm("Are you sure you want to completely DELETE the Error Log?").ask():
                if os.path.exists(ERROR_LOG_FILE):
                    os.remove(ERROR_LOG_FILE)
                print(f"{Colors.GREEN}[✓] Error Log deleted.{Colors.RESET}")
                time.sleep(1)
        elif choice == "Reset Config File to Default":
            if questionary.confirm("Reset all settings to Factory Default?").ask():
                save_config(DEFAULT_CONFIG)
                print(f"{Colors.GREEN}[✓] Configuration reset to default.{Colors.RESET}")
                time.sleep(1)

def show_help():
    os.system('cls' if os.name == 'nt' else 'clear')
    app_dummy = DomainScout(load_config())
    app_dummy.print_banner()
    print(f"\n{Colors.CYAN}{Colors.BOLD}=== DOMAINSCOUT HELP & SYSTEM INFO ==={Colors.RESET}")
    print(f" • [SPACE]       : Press during execution to Pause / Resume instantly.")
    print(f" • [M] (Paused)  : Press while paused to modify local settings.")
    print(f" • [H] (Paused)  : Show shortcuts help menu.")
    print(f" • [S] (Recheck) : Press during log recheck to stop and return to menu.")
    print(f" • [CTRL+C]      : Stop/Exit running process safely.")
    print(f" • [+]           : Available (Domain is free to register)")
    print(f" • [-]           : Taken (Domain is already registered)")
    print(f" • [~]           : Aftermarket (Domain is on sale)")
    print(f" • [*]           : Premium (Domain is premium priced)")
    print(f" • Master Log    : {os.path.abspath(MASTER_LOG_FILE)}")
    print(f" • Error Log     : {os.path.abspath(ERROR_LOG_FILE)}")
    print(f" • Config File   : {os.path.abspath(CONFIG_FILE)}")
    print(f"{Colors.CYAN}========================================{Colors.RESET}\n")
    input("Press Enter to return to main menu...")

def prompt_user(last_action="Start Domain Scanning"):
    if not os.path.exists(CONFIG_FILE):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Colors.CYAN}[!] Notice: First time setup detected!{Colors.RESET}")
        print(f"{Colors.YELLOW}You can customize all scan parameters anytime via the 'Settings & Configuration' menu.{Colors.RESET}")
        print(f"{Colors.GREEN}Default factory settings have been automatically applied for now.{Colors.RESET}\n")
        input("Press Enter to continue to the main menu...")
        save_config(DEFAULT_CONFIG)

    config = load_config()
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"""
{Colors.CYAN}{Colors.BOLD}
    ____                        _      _____                  __ 
   / __ \\____  ____ ___  ____ _(_)___ / ___/_________  __  __/ /_
  / / / / __ \\/ __ `__ \\/ __ `/ / __ \\\\__ \\/ ___/ __ \\/ / / / __/
 / /_/ / /_/ / / / / / / /_/ / / / / /__/ / /__/ /_/ / /_/ / /_  
/_____/\\____/_/ /_/ /_/\\__,_/_/_/ /_/____/\\___/\\____/\\__,_/\\__/  
{Colors.YELLOW}>> DomainScout by Code Cere | v3.2.5 <<{Colors.RESET}
    """)

    choices_list = [
        "Start Domain Scanning",
        "Settings & Configuration",
        "Recheck Master Log Status",
        "Log Management & Diagnostics",
        "Help & System Info / Paths",
        "Exit"
    ]
    default_choice = last_action if last_action in choices_list else choices_list[0]

    action = questionary.select(
        "Select an option:",
        choices=choices_list,
        default=default_choice
    ).ask()

    if action == "Settings & Configuration":
        app_temp = DomainScout(config)
        app_temp.modify_filters()
        return prompt_user(action)
    elif action == "Recheck Master Log Status":
        app_temp = DomainScout(config)
        app_temp.recheck_log_file()
        return prompt_user(action)
    elif action == "Log Management & Diagnostics":
        log_management_menu()
        return prompt_user(action)
    elif action == "Help & System Info / Paths":
        show_help()
        return prompt_user(action)
    elif action == "Exit" or not action:
        sys.exit(0)
    
    return config

if __name__ == "__main__":
    while True:
        config = prompt_user()
        app = DomainScout(config)
        app.run()