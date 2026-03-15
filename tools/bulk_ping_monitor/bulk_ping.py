import customtkinter as ctk
from tkinter import ttk, filedialog
import subprocess
import platform
import time
import os
import sys
import threading
import csv
from concurrent.futures import ThreadPoolExecutor

# Import openpyxl for Excel handling
try:
    import openpyxl
except ImportError:
    print("ERROR: Please install openpyxl -> 'pip install openpyxl'")
    sys.exit(1)

# --- Path Resolution Logic ---
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
EXCEL_FILE = os.path.join(BASE_DIR, "devices.xlsx")

# --- GUI Setup ---
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")

class PingMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Bulk Network Ping Monitor - V1.0")
        self.geometry("1500x750") 
        
        self.is_monitoring = False
        self.is_paused = False
        self.devices = []
        self.device_states = {}
        self.detached_items = set()
        
        self.setup_ui()
        self.load_excel()

    def setup_ui(self):
        # --- Top Control Panel ---
        self.top_frame = ctk.CTkFrame(self, height=70)
        self.top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.start_btn = ctk.CTkButton(self.top_frame, text="▶ Start Monitor", width=130, fg_color="green", hover_color="darkgreen", command=self.toggle_monitoring)
        self.start_btn.pack(side="left", padx=10, pady=15)

        self.pause_btn = ctk.CTkButton(self.top_frame, text="⏸ Pause", width=100, fg_color="#b8860b", hover_color="#8b6508", state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=5, pady=15)
        
        self.refresh_var = ctk.StringVar(value="5 seconds")
        ctk.CTkLabel(self.top_frame, text="Interval:").pack(side="left", padx=(15, 5), pady=15)
        self.interval_menu = ctk.CTkOptionMenu(
            self.top_frame, 
            values=["Real-time", "3 seconds", "5 seconds", "10 seconds", "30 seconds", "1 minute"], 
            variable=self.refresh_var, width=100
        )
        self.interval_menu.pack(side="left", padx=5, pady=15)

        self.duration_var = ctk.StringVar(value="Continuous")
        ctk.CTkLabel(self.top_frame, text="Duration:").pack(side="left", padx=(15, 5), pady=15)
        self.duration_menu = ctk.CTkOptionMenu(
            self.top_frame, 
            values=["1 minute", "5 minutes", "10 minutes", "30 minutes", "1 hour", "Continuous"], 
            variable=self.duration_var, width=110
        )
        self.duration_menu.pack(side="left", padx=5, pady=15)
        
        self.status_label = ctk.CTkLabel(self.top_frame, text="Status: Stopped | Devices: 0", font=("Arial", 14, "bold"))
        self.status_label.pack(side="right", padx=20, pady=15)

        # --- Filter Panel ---
        self.filter_frame = ctk.CTkFrame(self, height=50)
        self.filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.filter_frame, text="Filters:").pack(side="left", padx=10, pady=10)
        
        self.loc_var = ctk.StringVar(value="All")
        self.type_var = ctk.StringVar(value="All")
        self.group_var = ctk.StringVar(value="All") 
        self.status_var = ctk.StringVar(value="All")
        self.last_status_var = ctk.StringVar(value="All")
        
        ctk.CTkLabel(self.filter_frame, text="Location:").pack(side="left", padx=(10,2))
        self.loc_filter = ctk.CTkOptionMenu(self.filter_frame, variable=self.loc_var, values=["All"], width=110, command=self.apply_filters)
        self.loc_filter.pack(side="left", padx=5)

        ctk.CTkLabel(self.filter_frame, text="Type:").pack(side="left", padx=(10,2))
        self.type_filter = ctk.CTkOptionMenu(self.filter_frame, variable=self.type_var, values=["All"], width=110, command=self.apply_filters)
        self.type_filter.pack(side="left", padx=5)

        ctk.CTkLabel(self.filter_frame, text="Group:").pack(side="left", padx=(10,2))
        self.group_filter = ctk.CTkOptionMenu(self.filter_frame, variable=self.group_var, values=["All"], width=110, command=self.apply_filters)
        self.group_filter.pack(side="left", padx=5)

        ctk.CTkLabel(self.filter_frame, text="Status:").pack(side="left", padx=(10,2))
        self.status_filter = ctk.CTkOptionMenu(self.filter_frame, variable=self.status_var, values=["All", "UP", "DOWN", "WAITING"], width=100, command=self.apply_filters)
        self.status_filter.pack(side="left", padx=5)

        ctk.CTkLabel(self.filter_frame, text="Last Status:").pack(side="left", padx=(10,2))
        self.last_status_filter = ctk.CTkOptionMenu(self.filter_frame, variable=self.last_status_var, values=["All", "UP", "DOWN"], width=100, command=self.apply_filters)
        self.last_status_filter.pack(side="left", padx=5)

        self.clear_filter_btn = ctk.CTkButton(self.filter_frame, text="✖ Clear Filters", width=110, fg_color="#555555", hover_color="#333333", command=self.clear_filters)
        self.clear_filter_btn.pack(side="right", padx=10)

        # --- Main Table Area ---
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, font=("Arial", 11))
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=("Arial", 11, "bold"))
        style.map('Treeview', background=[('selected', '#1f538d')])
        
        self.columns = (
            "Hostname", "IP Address", "Location", "Device Type", "Group",
            "Latency", "Packet Loss", "Uptime", "Status", 
            "Last Ping Status", "Last Ping Time", "Last Down Time", "Ping OK", "Ping Count"
        )
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings", height=15)
        
        self.tree.tag_configure('UP', foreground='#00FF00')      
        self.tree.tag_configure('DOWN', foreground='#FF4444')    
        self.tree.tag_configure('WAITING', foreground='#AAAAAA') 
        
        widths = [120, 110, 90, 90, 90, 70, 80, 80, 80, 110, 100, 100, 70, 80]
        for col, w in zip(self.columns, widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, anchor="center", width=w)
            
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # --- Bottom Log & Export Area ---
        self.bottom_control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_control_frame.pack(fill="x", padx=10)
        
        self.log_label = ctk.CTkLabel(self.bottom_control_frame, text="Real-Time Alerts:", anchor="w", font=("Arial", 12, "bold"))
        self.log_label.pack(side="left")
        
        self.export_btn = ctk.CTkButton(self.bottom_control_frame, text="💾 Export Results (CSV)", width=150, fg_color="#005580", hover_color="#00334d", command=self.export_csv)
        
        self.log_box = ctk.CTkTextbox(self, height=100, state="disabled", text_color="yellow")
        self.log_box.pack(fill="x", padx=10, pady=(5, 10))

    def sort_column(self, col, reverse):
        rows = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        def convert_for_sort(val):
            if val in ["-", "WAITING"]: return -1
            if " ms" in val: return int(val.replace(" ms", ""))
            if "%" in val: return float(val.replace("%", ""))
            if "m " in val and "s" in val:  
                parts = val.replace("s", "").split("m ")
                return int(parts[0]) * 60 + int(parts[1])
            if val == "0s": return 0
            try: return float(val)
            except ValueError: return val.lower()

        rows.sort(key=lambda t: convert_for_sort(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(rows):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def log_message(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def load_excel(self):
        self.devices = []
        self.detached_items.clear()
        locations = set()
        device_types = set()
        groups = set() 
        
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
            ws = wb.active
            
            for row in ws.iter_rows(min_row=2, max_col=5, values_only=True):
                if not row or not row[0] or not row[1]:
                    continue 
                
                hostname = str(row[0]).strip()
                ip = str(row[1]).strip()
                loc = str(row[2]).strip() if len(row) > 2 and row[2] else "-"
                dev_type = str(row[3]).strip() if len(row) > 3 and row[3] else "-"
                group = str(row[4]).strip() if len(row) > 4 and row[4] else "-"
                
                self.devices.append({
                    'hostname': hostname, 'ip': ip, 'location': loc, 
                    'device_type': dev_type, 'group': group
                })
                
                if loc != "-": locations.add(loc)
                if dev_type != "-": device_types.add(dev_type)
                if group != "-": groups.add(group)
                
                self.device_states[ip] = {
                    'status': 'WAITING', 'total_pings': 0, 'success_pings': 0,
                    'uptime_start': None, 'last_ping_time': '-', 'last_ping_status': '-', 'last_down_time': '-'
                }
            
            self.loc_filter.configure(values=["All"] + sorted(list(locations)))
            self.type_filter.configure(values=["All"] + sorted(list(device_types)))
            self.group_filter.configure(values=["All"] + sorted(list(groups))) 
            
            self.status_label.configure(text=f"Status: Ready | Devices: {len(self.devices)}")
            
            for dev in self.devices:
                self.tree.insert("", "end", iid=dev['ip'], values=(
                    dev['hostname'], dev['ip'], dev['location'], dev['device_type'], dev['group'],
                    "-", "0.0%", "0s", "WAITING", "-", "-", "-", "0", "0"
                ), tags=("WAITING",))
                
        except FileNotFoundError:
            self.log_message(f"ERROR: Could not find '{EXCEL_FILE}' in {BASE_DIR}")
        except Exception as e:
            self.log_message(f"Excel Read Error: {e}")

    # --- Filtering & Export Logic ---
    def clear_filters(self):
        self.loc_var.set("All")
        self.type_var.set("All")
        self.group_var.set("All") 
        self.status_var.set("All")
        self.last_status_var.set("All")
        self.apply_filters()
        self.log_message("Filters cleared.")

    def is_item_visible(self, values):
        if not values: return False
        if self.loc_var.get() != "All" and values[2] != self.loc_var.get(): return False
        if self.type_var.get() != "All" and values[3] != self.type_var.get(): return False
        if self.group_var.get() != "All" and values[4] != self.group_var.get(): return False 
        if self.status_var.get() != "All" and self.status_var.get() not in values[8]: return False
        if self.last_status_var.get() != "All" and self.last_status_var.get() not in values[9]: return False
        return True

    def apply_filters(self, *args):
        for dev in self.devices:
            ip = dev['ip']
            values = self.tree.item(ip, 'values')
            if not values: continue
            
            if self.is_item_visible(values):
                if ip in self.detached_items:
                    self.tree.move(ip, '', 'end')
                    self.detached_items.remove(ip)
            else:
                if ip not in self.detached_items:
                    self.tree.detach(ip)
                    self.detached_items.add(ip)

    def export_csv(self):
        report_dir = os.path.join(BASE_DIR, "report")
        os.makedirs(report_dir, exist_ok=True)
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Results As",
            initialdir=report_dir,  
            initialfile=f"Network_Ping_Report_{time.strftime('%Y%m%d_%H%M')}.csv"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.columns)
                
                for dev in self.devices:
                    ip = dev['ip']
                    values = self.tree.item(ip, 'values')
                    writer.writerow(values)
                    
            self.log_message(f"✅ Results successfully exported to: {os.path.basename(file_path)}")
        except Exception as e:
            self.log_message(f"❌ Export Error: {e}")

    # --- Session Management Controls ---
    def reset_session_data(self):
        """Wipes previous memory so 'Start Monitor' creates a fresh session."""
        for dev in self.devices:
            ip = dev['ip']
            
            # 1. Reset Internal Memory State
            self.device_states[ip] = {
                'status': 'WAITING', 'total_pings': 0, 'success_pings': 0,
                'uptime_start': None, 'last_ping_time': '-', 'last_ping_status': '-', 'last_down_time': '-'
            }
            
            # 2. Reset GUI Table Values to Defaults
            values = (
                dev['hostname'], ip, dev['location'], dev['device_type'], dev['group'],
                "-", "0.0%", "0s", "WAITING", "-", "-", "-", "0", "0"
            )
            self.update_table_row(ip, values, "WAITING")

    def toggle_monitoring(self):
        if not self.is_monitoring:
            if not self.devices:
                self.log_message("Cannot start: No valid devices loaded from Excel.")
                return
            
            # --- BRAND NEW SESSION LOGIC ---
            self.reset_session_data()
            
            self.is_monitoring = True
            self.is_paused = False
            
            self.start_btn.configure(text="⏹ Stop Monitor", fg_color="red", hover_color="darkred")
            self.pause_btn.configure(state="normal", text="⏸ Pause", fg_color="#b8860b")
            
            self.export_btn.pack_forget() 
            
            self.status_label.configure(text=f"Status: MONITORING | Devices: {len(self.devices)}")
            
            self.interval_menu.configure(state="disabled")
            self.duration_menu.configure(state="disabled")
            
            self.log_message(f"Started NEW session. Interval: {self.refresh_var.get()}")
            threading.Thread(target=self.monitor_loop, daemon=True).start()
        else:
            self.stop_monitoring_ui()
            self.log_message("Stopped network monitoring.")

    def stop_monitoring_ui(self):
        self.is_monitoring = False
        self.is_paused = False
        self.start_btn.configure(text="▶ Start Monitor", fg_color="green", hover_color="darkgreen")
        self.pause_btn.configure(state="disabled", text="⏸ Pause")
        
        self.export_btn.pack(side="right") 
        
        self.status_label.configure(text=f"Status: Stopped | Devices: {len(self.devices)}")
        self.interval_menu.configure(state="normal")
        self.duration_menu.configure(state="normal")

    def toggle_pause(self):
        if not self.is_monitoring: return
        
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.configure(text="▶ Resume", fg_color="#006400", hover_color="#004d00")
            self.status_label.configure(text=f"Status: PAUSED | Devices: {len(self.devices)}")
            self.log_message("Monitoring paused. Session data retained. Will wait after current ping cycle finishes.")
        else:
            self.pause_btn.configure(text="⏸ Pause", fg_color="#b8860b", hover_color="#8b6508")
            self.status_label.configure(text=f"Status: MONITORING | Devices: {len(self.devices)}")
            self.log_message("Monitoring resumed.")

    def get_ping_command(self, ip):
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
        return ['ping', param, '1', timeout_param, '1000', ip]

    def ping_device(self, device):
        hostname = device['hostname']
        ip = device['ip']
        loc = device['location']
        dev_type = device['device_type']
        group = device['group']
        state = self.device_states[ip]
        
        command = self.get_ping_command(ip)
        start_time = time.time()
        
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == 'windows' else 0)
            latency_ms = int((time.time() - start_time) * 1000)
            status = "UP" if result.returncode == 0 else "DOWN"
            if status == "DOWN": latency_ms = "-"
        except Exception:
            status = "DOWN"
            latency_ms = "-"

        previous_status = state['status']
        if previous_status != "WAITING":
            state['last_ping_status'] = previous_status
        else:
            state['last_ping_status'] = "-"

        if status == "DOWN":
            state['last_down_time'] = time.strftime('%H:%M:%S')

        state['status'] = status
        state['total_pings'] += 1
        state['last_ping_time'] = time.strftime('%H:%M:%S')
        
        if status == "UP":
            state['success_pings'] += 1
            if state['uptime_start'] is None:
                state['uptime_start'] = time.time()
            uptime_sec = int(time.time() - state['uptime_start'])
            uptime_str = f"{uptime_sec // 60}m {uptime_sec % 60}s"
        else:
            state['uptime_start'] = None
            uptime_str = "0s"
            
        loss_pct = ((state['total_pings'] - state['success_pings']) / state['total_pings']) * 100
        loss_str = f"{loss_pct:.1f}%"

        if previous_status != 'WAITING' and previous_status != status:
            if status == "DOWN": self.after(0, self.log_message, f"ALERT: {hostname} ({ip}) went DOWN")
            else: self.after(0, self.log_message, f"RECOVERY: {hostname} ({ip}) is back UP")
                
        lat_str = f"{latency_ms} ms" if latency_ms != "-" else "-"
        
        values = (
            hostname, ip, loc, dev_type, group,
            lat_str, loss_str, uptime_str, status, 
            state['last_ping_status'], state['last_ping_time'], state['last_down_time'],
            str(state['success_pings']), str(state['total_pings'])
        )
        
        self.after(0, self.update_table_row, ip, values, status)

    def update_table_row(self, ip, values, status_tag):
        if self.tree.exists(ip):
            self.tree.item(ip, values=values, tags=(status_tag,))
            
            if self.is_item_visible(values):
                if ip in self.detached_items:
                    self.tree.move(ip, '', 'end')
                    self.detached_items.remove(ip)
            else:
                if ip not in self.detached_items:
                    self.tree.detach(ip)
                    self.detached_items.add(ip)

    def monitor_loop(self):
        interval_str = self.refresh_var.get()
        interval_sec = 0 if interval_str == "Real-time" else (60 if interval_str == "1 minute" else int(interval_str.split()[0]))
        
        duration_str = self.duration_var.get()
        end_time = None
        if duration_str == "1 minute": end_time = time.time() + 60
        elif duration_str == "5 minutes": end_time = time.time() + 300
        elif duration_str == "10 minutes": end_time = time.time() + 600
        elif duration_str == "30 minutes": end_time = time.time() + 1800
        elif duration_str == "1 hour": end_time = time.time() + 3600

        while self.is_monitoring:
            if self.is_paused:
                time.sleep(1)
                continue

            if end_time and time.time() >= end_time:
                self.after(0, self.log_message, f"Completed {duration_str} monitoring session.")
                self.after(0, self.stop_monitoring_ui)
                break
                
            with ThreadPoolExecutor(max_workers=50) as executor:
                executor.map(self.ping_device, self.devices)
            
            if interval_sec > 0:
                for _ in range(interval_sec):
                    if not self.is_monitoring or self.is_paused: break
                    time.sleep(1)

if __name__ == "__main__":
    app = PingMonitorApp()
    app.mainloop()
