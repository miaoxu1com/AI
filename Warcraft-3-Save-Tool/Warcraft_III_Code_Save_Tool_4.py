import os
import json
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyperclip
import keyboard
import threading
import re
import psutil
import ctypes
import time
import sys

try:
    import pygetwindow as gw
except ImportError:
    gw = None

CONFIG_FILE = "config.json"
DEFAULT_HOTKEYS = {
    "Save": {"key": "", "command": "-save"},
    "Buy Platinum Auto Converter": {"key": "", "command": "-bppc"},
    "Buy Arcadite Lumber Auto Converter": {"key": "", "command": "-bpac"},
}

def is_warcraft_focused():
    if platform.system() == "Windows" and gw:
        try:
            active_window = gw.getActiveWindow()
            if not active_window:
                return False

            title = active_window.title.lower()
            hwnd = active_window._hWnd

            # Get process ID from window handle
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['pid'] == pid.value:
                    exe_name = proc.info['name'].lower()
                    return ("warcraft" in title and "warcraft" in exe_name)
        except Exception as e:
            print(f"is_warcraft_focused error: {e}")
            return False

    elif platform.system() == "Linux":
        try:
            import subprocess
            result = subprocess.check_output(['xdotool', 'getwindowfocus', 'getwindowname'])
            return "warcraft" in result.decode().lower()
        except Exception as e:
            print(f"is_warcraft_focused error: {e}")
            return False

    return False

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class HotkeyEntry(ttk.Entry):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<KeyPress>", self.capture_key)

    def capture_key(self, event):
        keys = []
        if event.state & 0x0004:
            keys.append("ctrl")
        if event.state & 0x0001:
            keys.append("shift")
        if event.state & 0x0002:
            keys.append("alt")

        key = event.keysym.lower()
        mod_map = {
            "control_l": "ctrl",
            "control_r": "ctrl",
            "shift_l": "shift",
            "shift_r": "shift",
            "alt_l": "alt",
            "alt_r": "alt",
            "meta_l": "win",
            "meta_r": "win",
        }

        # Filter out raw modifier key names
        if key not in mod_map:
            keys.append(key)

        hotkey_str = "+".join(keys)
        self.delete(0, tk.END)
        self.insert(0, hotkey_str)
        return "break"  # Prevent character insertion


class SaveFile:
    def __init__(self, filepath, extract_fn):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.class_name, self.level = self._parse_filename()
        self.save_code = extract_fn(filepath)

    def _parse_filename(self):
        filename = self.filename.replace(".txt", "")
        parent = os.path.basename(os.path.dirname(self.filepath))
        if filename.startswith("[Level ") and filename.endswith("]"):
            level = filename.replace("[Level ", "").replace("]", "")
            return (parent, level)
        elif " - " in filename:
            parts = filename.rsplit(" - ", 1)
            return (parts[0], parts[1]) if len(parts) == 2 else ("Unknown", "?")
        else:
            return (parent, "?")



class WarcraftHotkeyUtility:
    def __init__(self, root):
        self.root = root
        self.root.title("Warcraft III Hotkey Utility")
        self.root.geometry("550x600")
        self.root.minsize(550, 600)
        self.config = self.load_config()
        self.current_map = tk.StringVar()
        self.auto_save_thread = None
        self.auto_save_event = threading.Event()
        self.build_ui()
        self.setup_hotkeys()
        
    def add_map(self):
        name = tk.simpledialog.askstring("New Map", "Enter map name:")
        if not name or name in self.config["maps"]:
            messagebox.showerror("Error", "Invalid or duplicate map name.")
            return
        path = filedialog.askdirectory(title="Select save folder for this map")
        if not path:
            return
        self.config["maps"][name] = {
            "save_directories": [path],
            "hotkeys": DEFAULT_HOTKEYS.copy()
        }
        self.config["last_selected_map"] = name
        self.save_config()
        self.update_map_list()
        
    def remove_map(self):
        name = self.current_map.get()
        if not name:
            return
        if messagebox.askyesno("Confirm", f"Remove map '{name}'?"):
            self.config["maps"].pop(name, None)
            if self.config["last_selected_map"] == name:
                self.config["last_selected_map"] = ""
            self.save_config()
            self.update_map_list()



    def build_options_tab(self):
        for widget in self.options_tab.winfo_children():
            widget.destroy()

        map_name = self.current_map.get()
        if not map_name:
            return

        options = self.config["maps"][map_name].setdefault("options", {})
        enabled_var = tk.BooleanVar(value=options.get("auto_save_enabled", False))
        interval_var = tk.IntVar(value=options.get("auto_save_interval", 300))

        def toggle_auto_save():
            options["auto_save_enabled"] = enabled_var.get()
            options["auto_save_interval"] = interval_var.get()
            self.save_config()
            self.setup_auto_save()

        def update_interval(*args):
            try:
                val = int(interval_var.get())
                if val > 0:
                    options["auto_save_interval"] = val
                    self.save_config()
                    self.setup_auto_save()
            except:
                pass

        ttk.Checkbutton(
            self.options_tab,
            text="Enable Auto Save Macro",
            variable=enabled_var,
            command=toggle_auto_save
        ).pack(anchor='w', padx=10, pady=5)

        interval_frame = ttk.Frame(self.options_tab)
        interval_frame.pack(anchor='w', padx=10, pady=5)

        ttk.Label(interval_frame, text="Interval (seconds):").pack(side='left')
        interval_entry = ttk.Entry(interval_frame, textvariable=interval_var, width=10)
        interval_entry.pack(side='left', padx=5)
        interval_var.trace_add("write", lambda *args: update_interval())

    def setup_auto_save(self):
        self.auto_save_event.set()
        map_data = self.config["maps"].get(self.current_map.get(), {})
        options = map_data.get("options", {})
        if not options.get("auto_save_enabled", False):
            return

        interval = options.get("auto_save_interval", 300)

        def auto_save_loop():
            while not self.auto_save_event.wait(interval):
                if is_warcraft_focused():
                    save_command = map_data.get("hotkeys", {}).get("Save", {}).get("command", "-save")
                    self.trigger_command(save_command)
                    
                    def press_escape():
                        threading.Event().wait(5)
                    if is_warcraft_focused():
                        keyboard.press_and_release('esc')

                    threading.Thread(target=press_escape, daemon=True).start()

        self.auto_save_event.clear()
        self.auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self.auto_save_thread.start()

    # ensure this is called in update_tabs
    def update_tabs(self):
        self.build_hotkeys_tab()
        self.build_saves_tab()
        self.build_folders_tab()
        self.build_options_tab()
        
    def build_hotkeys_tab(self):
        for widget in self.hotkeys_tab.winfo_children():
            widget.destroy()
        map_name = self.current_map.get()
        if not map_name:
            return

        hotkeys = self.config["maps"][map_name]["hotkeys"]
        self.hotkey_entries = {}

        for label, data in hotkeys.items():
            frame = ttk.Frame(self.hotkeys_tab)
            frame.pack(fill='x', padx=5, pady=2)

            label_entry = ttk.Entry(frame)
            label_entry.insert(0, label)
            label_entry.pack(side='left', fill='x', expand=True)

            key_entry = HotkeyEntry(frame, width=20)
            key_entry.insert(0, data.get("key", ""))
            key_entry.pack(side='left', padx=5)

            cmd_entry = ttk.Entry(frame, width=20)
            cmd_entry.insert(0, data.get("command", ""))
            cmd_entry.pack(side='left', padx=5)

            remove_btn = ttk.Button(frame, text="X", width=3,
                                    command=lambda l=label: self.remove_hotkey(l))
            remove_btn.pack(side='right')

            self.hotkey_entries[label] = (label_entry, key_entry, cmd_entry)

        ttk.Button(self.hotkeys_tab, text="Add Hotkey", command=self.add_hotkey).pack(pady=5)
        ttk.Button(self.hotkeys_tab, text="Save Hotkeys", command=self.save_hotkeys).pack()
        
    def add_hotkey(self):
        self.config["maps"][self.current_map.get()]["hotkeys"]["New Hotkey"] = {
            "key": "",
            "command": ""
        }
        self.save_config()
        self.update_tabs()

    def remove_hotkey(self, label):
        if label in self.config["maps"][self.current_map.get()]["hotkeys"]:
            del self.config["maps"][self.current_map.get()]["hotkeys"][label]
            self.save_config()
            self.update_tabs()

    def save_hotkeys(self):
        updated = {}
        for label, (label_entry, key_entry, cmd_entry) in self.hotkey_entries.items():
            new_label = label_entry.get()
            updated[new_label] = {
                "key": key_entry.get(),
                "command": cmd_entry.get()
            }
        self.config["maps"][self.current_map.get()]["hotkeys"] = updated
        self.save_config()
        self.setup_hotkeys()
        messagebox.showinfo("Saved", "Hotkeys updated.")

    def setup_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass

        map_data = self.config["maps"].get(self.current_map.get(), {})
        for label, data in map_data.get("hotkeys", {}).items():
            key = data.get("key")
            command = data.get("command")
            if key and command:
                keyboard.add_hotkey(key, lambda cmd=command: self.trigger_command(cmd))

    def trigger_command(self, cmd):
        def send_command():
            if is_warcraft_focused():
                # Step 1: Open chat
                keyboard.press_and_release('enter')
                time.sleep(0.2)  # Wait for chat box to open

                # Step 2: Type command
                keyboard.write(cmd)
                time.sleep(0.2)  # Optional: brief pause before sending

                # Step 3: Send command
                keyboard.press_and_release('enter')
                time.sleep(0.2)  # Wait before closing chat

                # Step 4: Close chat box
                keyboard.press_and_release('esc')

        threading.Thread(target=send_command).start()

        
    def build_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(pady=5, fill='x')

        self.map_dropdown = ttk.Combobox(top_frame, textvariable=self.current_map, state="readonly")
        self.map_dropdown.pack(side='left', padx=5)
        self.map_dropdown.bind("<<ComboboxSelected>>", self.on_map_change)

        ttk.Button(top_frame, text="Add Map", command=self.add_map).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Remove Map", command=self.remove_map).pack(side='left', padx=5)

        self.tab_control = ttk.Notebook(self.root)

        # Hotkeys tab
        self.hotkeys_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.hotkeys_tab, text="Hotkeys")

        # Scrollable Saves tab
        saves_container = ttk.Frame(self.tab_control)
        self.saves_tab_canvas = tk.Canvas(saves_container)
        scrollbar = ttk.Scrollbar(saves_container, orient="vertical", command=self.saves_tab_canvas.yview)
        self.saves_tab = ttk.Frame(self.saves_tab_canvas)

        self.saves_tab.bind(
            "<Configure>",
            lambda e: self.saves_tab_canvas.configure(scrollregion=self.saves_tab_canvas.bbox("all"))
        )

        self.saves_tab_canvas.create_window((0, 0), window=self.saves_tab, anchor="nw")
        self.saves_tab_canvas.configure(yscrollcommand=scrollbar.set)

        self.saves_tab_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tab_control.add(saves_container, text="Saves")

        # Folders tab
        self.folders_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.folders_tab, text="Save Folders")

        # Options tab
        self.options_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.options_tab, text="Options")

        self.tab_control.pack(fill='both', expand=True)

        self.update_map_list()


    def on_map_change(self, event=None):
        selected = self.current_map.get()
        self.config["last_selected_map"] = selected
        self.save_config()
        self.update_tabs()

    def update_map_list(self):
        maps = list(self.config["maps"].keys())
        self.map_dropdown["values"] = maps

        if self.config["last_selected_map"] in maps:
            self.current_map.set(self.config["last_selected_map"])
        elif maps:
            self.current_map.set(maps[0])
        else:
            self.current_map.set("")

        self.update_tabs()
        
    def extract_save_code(self, file_path):
        map_data = self.config["maps"].get(self.current_map.get(), {})
        mode = map_data.get("save_code_mode", "last_preload_line")

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        preload_lines = []
        for line in lines:
            match = re.search(r'call Preload\(\s*"([^"]+)"\s*\)', line)
            if match:
                preload_lines.append(match.group(1))

        if mode == "first_preload_line" and preload_lines:
            return preload_lines[0]
        elif mode == "last_preload_line" and preload_lines:
            return preload_lines[-1]
        elif mode.startswith("match_line_contains:"):
            keyword = mode.split(":", 1)[1].lower()
            for line in preload_lines:
                if keyword in line.lower():
                    return line
        elif mode.startswith("regex:"):
            pattern = mode.split(":", 1)[1]
            text = "".join(lines)
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return "Save code not found"

    def build_saves_tab(self):
        for widget in self.saves_tab.winfo_children():
            widget.destroy()
            
        refresh_btn = ttk.Button(self.saves_tab, text="Refresh", command=self.build_saves_tab)
        refresh_btn.pack(pady=5)

        map_data = self.config["maps"].get(self.current_map.get(), {})
        folders = map_data.get("save_directories", [])
        all_files = []

        for folder in folders:
            if not os.path.isdir(folder):
                continue
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(".txt"):
                        all_files.append(os.path.join(root, file))

        save_files = [SaveFile(f, self.extract_save_code) for f in all_files]
        grouped = {}
        for save in save_files:
            grouped.setdefault(save.class_name, []).append(save)

        for class_name in sorted(grouped):
            class_frame = ttk.LabelFrame(self.saves_tab, text=class_name)
            class_frame.pack(fill='x', padx=5, pady=5)

            saves = sorted(grouped[class_name], key=lambda s: int(s.level) if s.level.isdigit() else 0, reverse=True)
            level_var = tk.StringVar(value=saves[0].level)
            code_var = tk.StringVar(value=saves[0].save_code)

            codes = {s.level: s.save_code for s in saves}

            def update_code(selected_level, var=level_var, codes=codes, code_var=code_var):
                var.set(selected_level)
                code_var.set(codes.get(selected_level, ""))

            level_menu = ttk.OptionMenu(class_frame, level_var, saves[0].level, *[s.level for s in saves],
                                        command=update_code)
            level_menu.pack(side='left', padx=5)

            ttk.Label(class_frame, textvariable=code_var, wraplength=400).pack(side='left', padx=5)
            ttk.Button(class_frame, text="Copy", command=lambda c=code_var: pyperclip.copy(c.get())).pack(side='right')
            
    def build_folders_tab(self):
        for widget in self.folders_tab.winfo_children():
            widget.destroy()

        map_data = self.config["maps"].get(self.current_map.get(), {})
        folders = map_data.get("save_directories", [])

        for folder in folders:
            frame = ttk.Frame(self.folders_tab)
            frame.pack(fill='x', padx=5, pady=2)

            folder_name = os.path.basename(folder)
            label = ttk.Label(frame, text=folder_name)
            label.pack(side='left', fill='x', expand=True)
            ToolTip(label, folder)

            btn = ttk.Button(frame, text="Remove", command=lambda f=folder: self.remove_folder(f))
            btn.pack(side='right')

        ttk.Button(self.folders_tab, text="Add Folder", command=self.add_folder).pack(pady=5)

        self.build_save_code_mode_selector(self.folders_tab)

    def build_save_code_mode_selector(self, parent):
        map_name = self.current_map.get()
        if not map_name:
            return

        current_mode = self.config["maps"][map_name].get("save_code_mode", "last_preload_line")
        mode_var = tk.StringVar(value=current_mode)

        default_modes = [
            "first_preload_line",
            "last_preload_line",
            "match_line_contains:Hero",
            "match_line_contains:SaveCode",
            "regex:call Preload\\(\\s*\"(.+?)\"\\s*\\)"
        ]
        custom_modes = self.config["maps"][map_name].get("custom_save_code_modes", [])
        all_modes = sorted(set(default_modes + custom_modes))

        ttk.Label(parent, text="Save Code Detection Mode:").pack(anchor='w', padx=5)

        mode_box = ttk.Combobox(
            parent,
            textvariable=mode_var,
            values=all_modes,
            state="normal",
            width=60
        )
        mode_box.pack(fill='x', padx=5, pady=2)

        def apply_mode():
            value = mode_var.get().strip()
            if not value:
                messagebox.showwarning("Warning", "Please enter a valid detection mode.")
                return

            self.config["maps"][map_name]["save_code_mode"] = value

            if value not in default_modes and value not in custom_modes:
                self.config["maps"][map_name].setdefault("custom_save_code_modes", []).append(value)

            self.save_config()
            self.update_tabs()
            messagebox.showinfo("Saved", "Detection mode updated.")

        def delete_mode():
            value = mode_var.get().strip()
            if value in default_modes:
                messagebox.showwarning("Protected Mode", f"'{value}' is a default detection mode and cannot be removed.")
                return

            custom_list = self.config["maps"][map_name].get("custom_save_code_modes", [])
            if value in custom_list:
                if messagebox.askyesno("Confirm", f"Remove custom detection mode '{value}'?"):
                    custom_list.remove(value)

                    # If it's the active mode, reset it
                    if self.config["maps"][map_name].get("save_code_mode") == value:
                        self.config["maps"][map_name]["save_code_mode"] = "last_preload_line"
                        mode_var.set("last_preload_line")

                    self.save_config()
                    self.update_tabs()
                    messagebox.showinfo("Removed", f"Detection mode '{value}' was removed.")
            else:
                messagebox.showinfo("Not Found", f"'{value}' is not a custom detection mode.")

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', padx=5, pady=(0, 10))

        ttk.Button(button_frame, text="Apply", command=apply_mode).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Remove", command=delete_mode).pack(side='left')

    def add_folder(self):
        path = filedialog.askdirectory(title="Select save folder")
        if path:
            folders = self.config["maps"][self.current_map.get()].setdefault("save_directories", [])
            if path not in folders:
                folders.append(path)
                self.save_config()
                self.update_tabs()

    def remove_folder(self, folder):
        folders = self.config["maps"][self.current_map.get()].get("save_directories", [])
        if folder in folders:
            folders.remove(folder)
            self.save_config()
            self.update_tabs()

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

                for map_name, data in config.get("maps", {}).items():
                    if "save_directory" in data:
                        data["save_directories"] = [data.pop("save_directory")]

                known_defaults = {
                    "Curse of Time: Fires of Chaos": "first_preload_line",
                    "Twilight's Eve Evo": "last_preload_line"
                }
                for name, default_mode in known_defaults.items():
                    if name in config.get("maps", {}):
                        config["maps"][name].setdefault("save_code_mode", default_mode)

                return config
        return {"maps": {}, "last_selected_map": ""}

# Entry point
if __name__ == "__main__":
    root = tk.Tk()
    if getattr(sys, 'frozen', False):
        # Running from PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(base_path, 'W3PST.ico')

    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Could not set icon: {e}")

    app = WarcraftHotkeyUtility(root)
    root.mainloop()
