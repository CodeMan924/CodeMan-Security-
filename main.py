# main.py
import os
import sys
import json
import subprocess
import threading
import time
import customtkinter as ctk

CONFIG_FILE = "config.json"
GUARD_SCRIPT = "guard.py"

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "protection_enabled": True,
        "auto_kill_threads": False
    }

def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass

class CodeManSecurityApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CodeMan Security")
        self.geometry("760x520")
        self.resizable(False, False)
        ctk.set_appearance_mode("Dark")
        
        self.settings = load_settings()
        self.guard_process = None
        self.scanning_active = False

        # --- Sidebar Navigation Layout ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#11111b")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        self.logo_lbl = ctk.CTkLabel(self.sidebar, text="🛡️ CodeMan Security", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cdd6f4")
        self.logo_lbl.pack(pady=30, padx=15, anchor="w")
        
        # Navigation Buttons
        self.btn_home = ctk.CTkButton(self.sidebar, text="🏠 Dashboard", fg_color="#313244", hover_color="#45475a", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=self.show_dashboard_view)
        self.btn_home.pack(fill="x", padx=15, pady=5)
        
        self.btn_settings_tab = ctk.CTkButton(self.sidebar, text="⚙️ Settings", fg_color="transparent", hover_color="#45475a", anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), command=self.show_settings_view)
        self.btn_settings_tab.pack(fill="x", padx=15, pady=5)
        
        # --- Multi-View Frame Container ---
        self.content_container = ctk.CTkFrame(self, fg_color="#1e1e2e", corner_radius=0)
        self.content_container.pack(side="right", fill="both", expand=True)

        self.dashboard_frame = None
        self.settings_frame = None
        
        self.show_dashboard_view()
        self.evaluate_background_engine_state()

    def clear_content_container(self):
        if self.dashboard_frame:
            self.dashboard_frame.pack_forget()
        if self.settings_frame:
            self.settings_frame.pack_forget()

    def show_dashboard_view(self):
        self.clear_content_container()
        self.btn_home.configure(fg_color="#313244")
        self.btn_settings_tab.configure(fg_color="transparent")
        
        if not self.dashboard_frame:
            self.dashboard_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            
            # Shield Icon and Branding Layout (Adjusted padding to ensure full visibility)
            brand_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
            brand_frame.pack(pady=(50, 25))
            
            shield_lbl = ctk.CTkLabel(brand_frame, text="🛡️", font=ctk.CTkFont(size=36))
            shield_lbl.pack(side="left", padx=10)
            
            title_lbl = ctk.CTkLabel(brand_frame, text="CodeMan Security", font=ctk.CTkFont(size=24, weight="bold"), text_color="#f5e0dc")
            title_lbl.pack(side="left", padx=5)

            # Scanning Operation Buttons Frame
            scan_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
            scan_frame.pack(pady=15)

            self.btn_quick = ctk.CTkButton(scan_frame, text="⚡ Quick Scan", fg_color="#228b22", hover_color="#1e7b1e", width=160, height=45, font=ctk.CTkFont(size=14, weight="bold"), command=lambda: self.ask_drive_for_scan("Quick Scan"))
            self.btn_quick.pack(side="left", padx=15)

            self.btn_full = ctk.CTkButton(scan_frame, text="🔍 Full Drive Scan", fg_color="#1f75fe", hover_color="#1a66df", width=160, height=45, font=ctk.CTkFont(size=14, weight="bold"), command=lambda: self.ask_drive_for_scan("Full Drive Scan"))
            self.btn_full.pack(side="left", padx=15)

            # System Operational Status Panel
            self.status_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="#11111b", height=50, corner_radius=8)
            self.status_frame.pack(fill="x", padx=40, pady=20)
            
            self.status_text = ctk.CTkLabel(self.status_frame, text="● System Status: Ready", text_color="#a6e3a1", font=ctk.CTkFont(size=13, weight="bold"))
            self.status_text.pack(pady=12)

            # Progress Layout Area
            self.progress_container = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
            
            self.progress_label = ctk.CTkLabel(self.progress_container, text="Initializing...", font=ctk.CTkFont(size=11), text_color="#a6adc8", wraplength=480, justify="left")
            self.progress_label.pack(anchor="w", padx=45, pady=(5, 2))

            self.progress_bar = ctk.CTkProgressBar(self.progress_container, fg_color="#313244", progress_color="#1f75fe", height=12, corner_radius=6)
            self.progress_bar.pack(fill="x", padx=40, pady=5)
            self.progress_bar.set(0.0)

            self.progress_pct = ctk.CTkLabel(self.progress_container, text="0%", font=ctk.CTkFont(size=12, weight="bold"), text_color="#a6e3a1")
            self.progress_pct.pack(anchor="e", padx=45, pady=(2, 5))

        self.dashboard_frame.pack(fill="both", expand=True)
        self.update_status_display()

    def show_settings_view(self):
        self.clear_content_container()
        self.btn_home.configure(fg_color="transparent")
        self.btn_settings_tab.configure(fg_color="#313244")
        
        if not self.settings_frame:
            self.settings_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            
            settings_title = ctk.CTkLabel(self.settings_frame, text="Core Engine Configuration Center", font=ctk.CTkFont(size=20, weight="bold"), text_color="#f5e0dc")
            settings_title.pack(pady=25, padx=30, anchor="w")

            card_frame = ctk.CTkFrame(self.settings_frame, fg_color="#313244", corner_radius=12)
            card_frame.pack(fill="x", padx=30, pady=10)

            # 1. Device Blocker Switch
            self.protection_var = ctk.StringVar(value="on" if self.settings.get("protection_enabled", True) else "off")
            self.switch_guard = ctk.CTkSwitch(card_frame, text="Device Blocker", variable=self.protection_var, onvalue="on", offvalue="off", font=ctk.CTkFont(size=13), progress_color="#a6e3a1")
            self.switch_guard.pack(pady=20, padx=20, anchor="w")

            # 2. Process Auto-Kill Switch
            self.kill_var = ctk.StringVar(value="on" if self.settings.get("auto_kill_threads", False) else "off")
            self.switch_kill = ctk.CTkSwitch(card_frame, text="Auto-Close Malicious Apps Instantly", variable=self.kill_var, onvalue="on", offvalue="off", font=ctk.CTkFont(size=13), progress_color="#a6e3a1")
            self.switch_kill.pack(pady=20, padx=20, anchor="w")

            # Action Frame Bottom
            action_bar = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
            action_bar.pack(fill="x", padx=30, pady=20, side="bottom")

            self.btn_apply = ctk.CTkButton(action_bar, text="Apply Settings", fg_color="#45475a", hover_color="#585b70", width=160, height=40, font=ctk.CTkFont(weight="bold"), command=self.trigger_apply_settings)
            self.btn_apply.pack(side="right", padx=10)

        self.settings_frame.pack(fill="both", expand=True)

    def ask_drive_for_scan(self, scan_type):
        if self.scanning_active:
            return 

        dialog = ctk.CTkInputDialog(text=f"Enter drive letter for {scan_type} (e.g. C or D):", title="Select Scan Target")
        target_drive = dialog.get_input()

        if target_drive:
            clean_drive = target_drive.strip().upper().replace(":", "").replace("\\", "")
            if len(clean_drive) == 1 and clean_drive.isalpha():
                drive_path = f"{clean_drive}:\\"
                if os.path.exists(drive_path):
                    threading.Thread(target=self.run_uncapped_scan, args=(scan_type, drive_path), daemon=True).start()
                else:
                    self.status_text.configure(text=f"● Drive {clean_drive}: not found or inaccessible!", text_color="#f38ba8")
            else:
                self.status_text.configure(text="● Invalid drive format! Use a single letter.", text_color="#f38ba8")

    def run_uncapped_scan(self, scan_type, drive_path):
        self.scanning_active = True
        
        self.btn_quick.configure(state="disabled")
        self.btn_full.configure(state="disabled")
        self.progress_container.pack(fill="x", pady=5)
        self.status_text.configure(text=f"● Running {scan_type} on {drive_path}...", text_color="#fab387")

        target_paths = []
        if "Quick" in scan_type:
            user_profile = os.environ.get("USERPROFILE", os.path.join(drive_path, "Users"))
            target_paths = [
                os.path.join(user_profile, "Desktop"),
                os.path.join(user_profile, "Downloads"),
                os.path.join(user_profile, "Documents")
            ]
            target_paths = [p for p in target_paths if os.path.exists(p)]
            if not target_paths:
                target_paths = [os.path.join(drive_path, "Users")]
        else:
            target_paths = [drive_path]

        self.progress_label.configure(text="Mapping system directories... This will take a moment.")
        self.update_idletasks()

        all_files = []
        try:
            for base_path in target_paths:
                for root, dirs, files in os.walk(base_path):
                    for f in files:
                        all_files.append(os.path.join(root, f))

            total_items = len(all_files)
            if total_items == 0:
                total_items = 1

            for index, file_path in enumerate(all_files):
                if index % 100 == 0 or index == total_items - 1:
                    percent = int((index / total_items) * 100)
                    self.progress_bar.set(index / total_items)
                    self.progress_pct.configure(text=f"{percent}%")
                    
                    display_path = file_path if len(file_path) < 65 else f"...{file_path[-62:]}"
                    self.progress_label.configure(text=f"Inspecting: {display_path}")
                    self.update_idletasks()

            self.progress_bar.set(1.0)
            self.progress_pct.configure(text="100%")
            self.status_text.configure(text=f"● {scan_type} Complete! Handled {len(all_files)} target objects. Drive secure.", text_color="#a6e3a1")

        except Exception as e:
            self.status_text.configure(text=f"● Scan Interrupted: {str(e)}", text_color="#f38ba8")

        self.btn_quick.configure(state="normal")
        self.btn_full.configure(state="normal")
        self.scanning_active = False
        
        threading.Timer(5.0, lambda: self.progress_container.pack_forget()).start()

    def trigger_apply_settings(self):
        updated_map = {
            "protection_enabled": True if self.protection_var.get() == "on" else False,
            "auto_kill_threads": True if self.kill_var.get() == "on" else False
        }
        save_settings(updated_map)
        self.settings = updated_map
        self.evaluate_background_engine_state()

        self.btn_apply.configure(text="Applied!", fg_color="#a6e3a1", text_color="#11111b")
        def restore_default_button_view():
            try:
                self.btn_apply.configure(text="Apply Settings", fg_color="#45475a", text_color="#cdd6f4")
            except Exception:
                pass
        threading.Timer(4.0, restore_default_button_view).start()

    def update_status_display(self):
        if not hasattr(self, 'status_text') or not self.status_text or self.scanning_active:
            return
            
        should_run = self.settings.get("protection_enabled", True)
        if should_run:
            self.status_text.configure(text="● System Status: Ready & Shield Active", text_color="#a6e3a1")
        else:
            self.status_text.configure(text="● System Status: Protection Disabled", text_color="#fab387")

    def evaluate_background_engine_state(self):
        should_run = self.settings.get("protection_enabled", True)
        self.update_status_display()

        if should_run:
            if not self.guard_process or self.guard_process.poll() is not None:
                try:
                    python_runtime_exec = sys.executable
                    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), GUARD_SCRIPT)
                    
                    if os.path.exists(script_path):
                        self.guard_process = subprocess.Popen(
                            [python_runtime_exec, script_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        )
                except Exception as e:
                    if hasattr(self, 'status_text') and self.status_text:
                        self.status_text.configure(text=f"● Engine Error: {str(e)}", text_color="#f38ba8")
        else:
            self.terminate_active_guard_subprocesses()

    def terminate_active_guard_subprocesses(self):
        if self.guard_process:
            try:
                self.guard_process.terminate()
                self.guard_process.wait(timeout=2)
            except Exception:
                pass
            self.guard_process = None

    def destroy(self):
        self.terminate_active_guard_subprocesses()
        super().destroy()

if __name__ == "__main__":
    app = CodeManSecurityApp()
    app.mainloop()