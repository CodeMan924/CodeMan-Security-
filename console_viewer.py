# console_viewer.py
import os
import sys
import time

LOG_FILE = "app.log"
tabs = ["SIGNATURES", "GUARD", "MAIN"]
current_tab_idx = 0

def draw_interface():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 70)
    print(" CODEMAN'S SECURITY PRO - EXTERNAL RUNTIME STREAM")
    print("=" * 70)
    
    tab_bar = "  "
    for idx, tab in enumerate(tabs):
        if idx == current_tab_idx:
            tab_bar += f"👉 \033[44m\033[37m[ {tab} ]\033[0m   "
        else:
            tab_bar += f"[ {tab} ]   "
    print(tab_bar)
    print("-" * 70)
    print(" (Press Enter to cycle / refresh views | Ctrl+C to close)")
    print("-" * 70)

    if not os.path.exists(LOG_FILE):
        print("\n No logs recorded yet.")
        return

    target_prefix = f"[{tabs[current_tab_idx]}]"
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            matching_lines = [line.strip() for line in lines if line.startswith(target_prefix)]
            
            if not matching_lines:
                print(f"\n No logs found matching tab context {target_prefix}")
            else:
                for line in matching_lines[-15:]:
                    print(f" {line}")
    except Exception as e:
        print(f"Read error: {e}")

if __name__ == "__main__":
    os.system("title CodeMan Tabbed Viewer Console")
    while True:
        try:
            draw_interface()
            input()
            current_tab_idx = (current_tab_idx + 1) % len(tabs)
        except KeyboardInterrupt:
            sys.exit(0)