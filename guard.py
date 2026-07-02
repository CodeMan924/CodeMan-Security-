# guard.py
import os
import sys
import time
import psutil
import asyncio
import json
import threading
import customtkinter as ctk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import websockets

EXCLUSIONS_FILE = "exclusions.txt"
LOG_FILE = "app.log"

CONNECTED_CLIENTS = set()
CLIENTS_LOCK = threading.Lock()
LOOP = None  

GLOBAL_FILENAME_MEMORY = {}
COOLDOWN_LOCK = threading.Lock()
DELETION_REGISTRY = set()

UPCOMING_INTERCEPTS = [] 
QUEUE_LOCK = threading.Lock()

def log_to_file(tag, message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{tag}] {message}\n")
            f.flush()
    except Exception:
        pass

async def chrome_server_handler(websocket):
    with CLIENTS_LOCK:
        CONNECTED_CLIENTS.add(websocket)
    log_to_file("GUARD", "Chrome Extension linked to security matrix.")
    
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("event") == "browser_download_start":
                filename = data.get('filename')
                log_to_file("GUARD", f"Chrome reported incoming file download stream: {filename}")
                with QUEUE_LOCK:
                    if filename not in UPCOMING_INTERCEPTS:
                        UPCOMING_INTERCEPTS.append(filename)
    except websockets.ConnectionClosed:
        pass
    finally:
        with CLIENTS_LOCK:
            CONNECTED_CLIENTS.discard(websocket)
        log_to_file("GUARD", "Chrome Extension decoupled from matrix.")

async def main_ws_server():
    global LOOP
    LOOP = asyncio.get_running_loop()
    async with websockets.serve(chrome_server_handler, "127.0.0.1", 8765):
        await asyncio.Event().wait()

def start_websocket_loop():
    asyncio.run(main_ws_server())

def send_block_signal_to_chrome(filename):
    global LOOP
    if not LOOP:
        return
    with CLIENTS_LOCK:
        if not CONNECTED_CLIENTS:
            return
        payload = json.dumps({"action": "BLOCK", "filename": filename})
        for client in CONNECTED_CLIENTS:
            asyncio.run_coroutine_threadsafe(client.send(payload), LOOP)

def load_exclusions():
    if not os.path.exists(EXCLUSIONS_FILE):
        return []
    with open(EXCLUSIONS_FILE, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def add_to_exclusions(file_path):
    exclusions = load_exclusions()
    normalized = os.path.normpath(file_path)
    if normalized not in exclusions:
        with open(EXCLUSIONS_FILE, "a") as f:
            f.write(normalized + "\n")

def kill_associated_process(filename):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == filename.lower():
                proc.terminate()
                proc.wait(timeout=2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            continue

def open_intercept_list_window():
    manager = ctk.CTkToplevel()
    manager.title("Intercept Stream Pipeline Control")
    manager.geometry("620x470")
    manager.resizable(False, False)
    manager.attributes("-topmost", True)
    
    checkbox_references = {}
    checkbox_vars = {}
    
    top_bar = ctk.CTkFrame(manager, height=45, fg_color="#1e1e2e")
    top_bar.pack(fill="x", side="top")
    
    title_label = ctk.CTkLabel(top_bar, text="🛡️ STREAM PIPELINE MONITOR", font=ctk.CTkFont(size=13, weight="bold"), text_color="#a6adc8")
    title_label.pack(side="left", padx=15)
    
    feature_action_bar = ctk.CTkFrame(manager, height=45, fg_color="#313244")
    
    def execute_removal_sequence():
        with QUEUE_LOCK:
            for name, var in list(checkbox_vars.items()):
                if var.get() == "on":
                    send_block_signal_to_chrome(name)
                    kill_associated_process(name)
                    if name in UPCOMING_INTERCEPTS:
                        UPCOMING_INTERCEPTS.remove(name)
        render_intercept_rows(show_checkboxes=True)
    
    def execute_remove_all_sequence():
        with QUEUE_LOCK:
            for name in list(UPCOMING_INTERCEPTS):
                send_block_signal_to_chrome(name)
                kill_associated_process(name)
                if name in UPCOMING_INTERCEPTS:
                    UPCOMING_INTERCEPTS.remove(name)
        render_intercept_rows(show_checkboxes=True)

    # Action buttons placed side-by-side inside the selection action bar
    remove_all_btn = ctk.CTkButton(feature_action_bar, text="🗑️ Remove all intercepts", fg_color="#fab387", hover_color="#ea999c", text_color="#11111b", font=ctk.CTkFont(weight="bold"), command=execute_remove_all_sequence)
    remove_all_btn.pack(side="right", padx=10, pady=8)

    remove_btn = ctk.CTkButton(feature_action_bar, text="❌ Remove Selected", fg_color="#f38ba8", hover_color="#e05f83", text_color="#11111b", font=ctk.CTkFont(weight="bold"), command=execute_removal_sequence)
    remove_btn.pack(side="right", padx=5, pady=8)

    scroll_frame = ctk.CTkScrollableFrame(manager, fg_color="#11111b", label_text="Active & Upcoming Intercept Queue Stream")
    scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)
    
    def render_intercept_rows(show_checkboxes=False):
        for child in scroll_frame.winfo_children():
            child.destroy()
        checkbox_references.clear()
        checkbox_vars.clear()
        
        with QUEUE_LOCK:
            if not UPCOMING_INTERCEPTS:
                empty_lbl = ctk.CTkLabel(scroll_frame, text="[No Intercept Pipelines Currently Logged]", font=ctk.CTkFont(slant="italic"), text_color="#585b70")
                empty_lbl.pack(pady=40)
                feature_action_bar.pack_forget()
                return
                
            for index, item_name in enumerate(UPCOMING_INTERCEPTS):
                row = ctk.CTkFrame(scroll_frame, fg_color="#1e1e2e", height=40)
                row.pack(fill="x", pady=4, padx=5)
                
                if show_checkboxes:
                    var = ctk.StringVar(value="off")
                    chk = ctk.CTkCheckBox(row, text="", variable=var, onvalue="on", offvalue="off", width=20)
                    chk.pack(side="left", padx=10)
                    checkbox_vars[item_name] = var
                    checkbox_references[item_name] = chk
                
                num_lbl = ctk.CTkLabel(row, text=f"[{index + 1}]", text_color="#fab387", font=ctk.CTkFont(weight="bold"))
                num_lbl.pack(side="left", padx=10)
                
                name_lbl = ctk.CTkLabel(row, text=item_name, text_color="#cdd6f4", font=ctk.CTkFont(size=12))
                name_lbl.pack(side="left", padx=5)
                
        if show_checkboxes:
            feature_action_bar.pack(fill="x", side="bottom", padx=15, pady=10)
        else:
            feature_action_bar.pack_forget()

    mgr_menu_state = {"active": False, "cb_mode": False}
    mgr_dropdown = ctk.CTkFrame(manager, fg_color="#1e1e2e", border_width=1, border_color="#313244", width=160, height=35)

    def select_intercepts_clicked():
        mgr_dropdown.place_forget()
        mgr_menu_state["active"] = False
        mgr_menu_state["cb_mode"] = not mgr_menu_state["cb_mode"]
        render_intercept_rows(show_checkboxes=mgr_menu_state["cb_mode"])

    select_menu_btn = ctk.CTkButton(mgr_dropdown, text="⚙️ Select Intercepts", fg_color="transparent", hover_color="#45475a", anchor="w", text_color="#cdd6f4", font=ctk.CTkFont(size=11, weight="bold"), command=select_intercepts_clicked)
    select_menu_btn.pack(fill="both", expand=True, padx=2, pady=2)

    def toggle_manager_menu():
        if not mgr_menu_state["active"]:
            mgr_dropdown.place(x=450, y=40)
            mgr_menu_state["active"] = True
        else:
            mgr_dropdown.place_forget()
            mgr_menu_state["active"] = False

    menu_btn = ctk.CTkButton(top_bar, text="⋮", width=30, height=30, fg_color="transparent", hover_color="#45475a", font=ctk.CTkFont(size=16, weight="bold"), command=toggle_manager_menu)
    menu_btn.pack(side="right", padx=10)
    
    render_intercept_rows(show_checkboxes=mgr_menu_state["cb_mode"])

def show_warning_ui(file_path):
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.title("CodeMan's Security - Intercept Alert")
    root.geometry("540x310")  
    root.resizable(False, False)
    root.attributes("-topmost", True)  

    user_choice = {"continue": True, "exclude": False}

    header_strip = ctk.CTkFrame(root, height=35, fg_color="transparent")
    header_strip.pack(fill="x", side="top", padx=5, pady=2)
    
    label_title = ctk.CTkLabel(root, text="⚠️ Warning: Unverified File Detected", text_color="#f59e0b", font=ctk.CTkFont(size=18, weight="bold"))
    label_title.pack(pady=10)

    filename = os.path.basename(file_path)
    label_msg = ctk.CTkLabel(root, text=f"The system detected activity on this file:\n'{filename}'\n\nAre you sure you want to allow this program to run?", font=ctk.CTkFont(size=12), justify="center")
    label_msg.pack(pady=5)

    chk_var = ctk.StringVar(value="off")
    chk_exclude = ctk.CTkCheckBox(root, text="Add to Exclusions (Do not warn again)", variable=chk_var, onvalue="on", offvalue="off", font=ctk.CTkFont(size=11))
    chk_exclude.pack(pady=5)

    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(pady=10)

    def on_yes():
        if chk_var.get() == "on":
            user_choice["exclude"] = True
        user_choice["continue"] = True
        root.destroy()

    def on_no():
        user_choice["continue"] = False
        root.destroy()

    btn_no = ctk.CTkButton(btn_frame, text="No (Block/Close)", fg_color="#ef4444", hover_color="#dc2626", width=140, command=on_no)
    btn_no.pack(side="left", padx=15)

    btn_yes = ctk.CTkButton(btn_frame, text="Yes (Allow)", fg_color="#10b981", hover_color="#059669", width=140, command=on_yes)
    btn_yes.pack(side="left", padx=15)

    menu_open_state = {"active": False}
    context_option_frame = ctk.CTkFrame(root, fg_color="#1e1e2e", border_width=1, border_color="#313244", width=260, height=45)

    list_nav_btn = ctk.CTkButton(context_option_frame, text="🔍 Show List Of Incoming Intercepts", fg_color="transparent", hover_color="#45475a", anchor="w", text_color="#cdd6f4", font=ctk.CTkFont(size=11, weight="bold"), command=lambda: [open_intercept_list_window(), context_option_frame.place_forget(), menu_open_state.update({"active": False})])
    list_nav_btn.pack(fill="both", expand=True, padx=2, pady=2)

    def trigger_menu_dropdown_action():
        if not menu_open_state["active"]:
            context_option_frame.place(x=260, y=35)
            menu_open_state["active"] = True
        else:
            context_option_frame.place_forget()
            menu_open_state["active"] = False

    three_dots_btn = ctk.CTkButton(header_strip, text="⋮", width=30, height=30, fg_color="transparent", hover_color="#2b2b36", font=ctk.CTkFont(size=16, weight="bold"), command=trigger_menu_dropdown_action)
    three_dots_btn.pack(side="right", padx=10, pady=2)

    root.mainloop()
    return user_choice

class DeviceProtectorHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory or "app.log" in event.src_path or "exclusions.txt" in event.src_path:
            return
        
        if event.event_type not in ["created", "modified", "moved"]:
            return

        file_path = event.dest_path if event.event_type == "moved" else event.src_path
        if file_path in DELETION_REGISTRY:
            return

        filename = os.path.basename(file_path)
        if file_path.endswith(".crdownload") or file_path.endswith(".tmp") or filename.startswith(".com.google.Chrome"):
            return

        now = time.time()
        with COOLDOWN_LOCK:
            if filename in GLOBAL_FILENAME_MEMORY:
                if (now - GLOBAL_FILENAME_MEMORY[filename]) < 5.0:
                    return
            GLOBAL_FILENAME_MEMORY[filename] = now

        if os.path.normpath(file_path) in load_exclusions():
            return

        with QUEUE_LOCK:
            if filename not in UPCOMING_INTERCEPTS:
                UPCOMING_INTERCEPTS.append(filename)

        log_to_file("GUARD", f"Intercepted modification event for asset: {filename}")
        choice = show_warning_ui(file_path)
        
        if choice["exclude"]:
            add_to_exclusions(file_path)
            log_to_file("SIGNATURES", f"Whitelisted asset tracking path: {filename}")

        if not choice["continue"]:
            send_block_signal_to_chrome(filename)
            kill_associated_process(filename)
            log_to_file("GUARD", f"Terminated process and cancelled stream: {filename}")
            
            DELETION_REGISTRY.add(file_path)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)  
            except Exception:
                pass
            finally:
                threading.Timer(3.0, lambda: DELETION_REGISTRY.discard(file_path)).start()
            
            with QUEUE_LOCK:
                if filename in UPCOMING_INTERCEPTS:
                    UPCOMING_INTERCEPTS.remove(filename)
        else:
            log_to_file("GUARD", f"Authorized execution context allowed: {filename}")

if __name__ == "__main__":
    ws_thread = threading.Thread(target=start_websocket_loop, daemon=True)
    ws_thread.start()

    user_home = os.path.expanduser("~")
    possible_paths = [
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "OneDrive", "Downloads"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "OneDrive", "Desktop")
    ]
    
    watch_paths = [p for p in possible_paths if os.path.exists(p)]
    if not watch_paths:
        watch_paths = [user_home]

    event_handler = DeviceProtectorHandler()
    observer = Observer()
    
    for path in watch_paths:
        log_to_file("GUARD", f"Active. Watching thread folder path: {path}")
        observer.schedule(event_handler, path, recursive=True)
        
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()