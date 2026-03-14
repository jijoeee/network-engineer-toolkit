import customtkinter as ctk
import ipaddress
import tkinter.messagebox as messagebox

# Set the theme and color for a professional look
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

class IPSubnetCalculatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("IP Subnet Calculator (IPv4 & IPv6)")
        self.geometry("650x650") 
        self.resizable(False, False)

        # Configure grid for centering
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Header
        self.calc_header = ctk.CTkLabel(self, text="IP Subnet Calculator", font=ctk.CTkFont(size=24, weight="bold"))
        self.calc_header.grid(row=0, column=0, columnspan=2, padx=20, pady=(30, 20))

        # Inputs
        self.lbl_ip = ctk.CTkLabel(self, text="Network IP / CIDR:")
        self.lbl_ip.grid(row=1, column=0, padx=20, pady=10, sticky="e")
        
        self.entry_ip = ctk.CTkEntry(self, placeholder_text="e.g., 192.168.1.5/24 or 2001:db8::1/64", width=250)
        self.entry_ip.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        self.btn_calc = ctk.CTkButton(self, text="Calculate Base Subnet", command=self.calculate_subnet)
        self.btn_calc.grid(row=2, column=0, columnspan=2, padx=20, pady=15)

        # Outputs
        self.output_textbox = ctk.CTkTextbox(self, height=230, width=550, font=ctk.CTkFont(family="Courier", size=13))
        self.output_textbox.grid(row=3, column=0, columnspan=2, padx=20, pady=10)
        self.output_textbox.insert("0.0", "Awaiting input...\nEnter a valid IP with CIDR to proceed.")
        self.output_textbox.configure(state="disabled")

        # Extra Feature: Auto Subnet Splitting
        self.lbl_split = ctk.CTkLabel(self, text="Target CIDR for Splitting:")
        self.lbl_split.grid(row=4, column=0, padx=20, pady=10, sticky="e")
        
        self.entry_split = ctk.CTkEntry(self, placeholder_text="e.g., 25 or 125", width=100)
        self.entry_split.grid(row=4, column=1, padx=20, pady=10, sticky="w")
        
        # Bind the key release event to check for input
        self.entry_split.bind("<KeyRelease>", self.check_split_input)

        # Button starts disabled (greyed out)
        self.btn_split = ctk.CTkButton(self, text="Generate Split Subnets", command=self.split_subnet, fg_color="#2b7a4b", hover_color="#1e5c37", state="disabled")
        self.btn_split.grid(row=5, column=0, columnspan=2, padx=20, pady=15)

    def check_split_input(self, event=None):
        if self.entry_split.get().strip():
            self.btn_split.configure(state="normal")
        else:
            self.btn_split.configure(state="disabled")

    def calculate_subnet(self):
        ip_input = self.entry_ip.get().strip()
        try:
            interface = ipaddress.ip_interface(ip_input)
            network = interface.network
            exact_ip = interface.ip
            
            # --- SMART NEXT-HOP LOGIC ---
            if network.prefixlen == network.max_prefixlen:
                # Case 1: Host route (/32 or /128). Show the same IP.
                next_ip_str = f"{exact_ip}/{network.prefixlen}"
                
            elif (network.version == 4 and network.prefixlen == 31) or (network.version == 6 and network.prefixlen == 127):
                # Case 2: Point-to-Point link (/31 or /127). Only 2 IPs exist.
                if exact_ip == network.network_address:
                    next_ip_str = f"{exact_ip + 1}/{network.prefixlen}"
                else:
                    next_ip_str = f"{exact_ip - 1}/{network.prefixlen}"
                    
            else:
                # Case 3: Standard Subnets
                if exact_ip == network.network_address or exact_ip == network.broadcast_address:
                    # User entered the Network or Broadcast IP
                    next_ip_str = "Input is Network or Broadcast IP"
                elif exact_ip + 1 < network.broadcast_address:
                    # Normal case: Next IP is valid and not the broadcast
                    next_ip_str = f"{exact_ip + 1}/{network.prefixlen}"
                else:
                    # User entered the LAST usable IP, so we decrement by 1 instead
                    next_ip_str = f"{exact_ip - 1}/{network.prefixlen}"
            # -----------------------------
            
            if network.version == 4:
                result = (
                    f"Protocol        : IPv4\n"
                    f"Network Address : {network.network_address}\n"
                    f"Subnet Mask     : {network.netmask}\n"
                    f"Broadcast       : {network.broadcast_address}\n"
                    f"Usable Range    : {network.network_address + 1} - {network.broadcast_address - 1}\n"
                    f"Number of Hosts : {network.num_addresses - 2 if network.num_addresses > 2 else 0}\n\n"
                    f"Input IP        : {exact_ip}/{network.prefixlen}\n"
                    f"Next-hop        : {next_ip_str}\n"
                )
            else:
                result = (
                    f"Protocol        : IPv6\n"
                    f"Network Address : {network.network_address}\n"
                    f"Prefix Length   : /{network.prefixlen}\n"
                    f"Last Address    : {network.broadcast_address}\n"
                    f"Total IPs       : {network.num_addresses:,}\n\n"
                    f"Input IP        : {exact_ip}/{network.prefixlen}\n"
                    f"Next-hop        : {next_ip_str}\n"
                )
            
            self.output_textbox.configure(state="normal")
            self.output_textbox.delete("0.0", "end")
            self.output_textbox.insert("0.0", result)
            self.output_textbox.configure(state="disabled")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid IPv4 or IPv6 network/IP (e.g., 192.168.1.5/24 or 2001:db8::1/64)")

    def split_subnet(self):
        ip_input = self.entry_ip.get().strip()
        split_input = self.entry_split.get().strip().replace("/", "") 
        
        try:
            network = ipaddress.ip_network(ip_input, strict=False)
            new_prefix = int(split_input)
            
            # --- DYNAMIC DISPLAY LIMITS ---
            if network.version == 4:
                DISPLAY_LIMIT = 1000 # Limit for IPv4
            else:
                DISPLAY_LIMIT = 100  # Stricter limit of 100 for IPv6
            
            # Calculate total subnets mathematically to prevent Memory Crash
            total_subnets = 2 ** (new_prefix - network.prefixlen)
            
            # Create a generator instead of a list. This uses almost zero RAM.
            subnets_generator = network.subnets(new_prefix=new_prefix)
            
            result = f"Splitting {network} into /{new_prefix} subnets:\n" + "-"*55 + "\n"
            
            # Extract only up to the DISPLAY_LIMIT using next()
            displayed_count = 0
            for _ in range(DISPLAY_LIMIT):
                try:
                    sn = next(subnets_generator)
                    net_str = f"{str(sn.network_address)}/{sn.prefixlen}"
                    
                    if network.version == 4:
                        result += f"Net: {net_str:<18} | Range: {sn.network_address + 1} - {sn.broadcast_address - 1}\n"
                    else:
                        result += f"Net  : {net_str}\nRange: {sn.network_address} \n    to {sn.broadcast_address}\n\n"
                    
                    displayed_count += 1
                except StopIteration:
                    break # We ran out of subnets before hitting the limit
            
            # If there are more subnets than we displayed, show the remaining count mathematically
            if total_subnets > displayed_count:
                remaining_subnets = total_subnets - displayed_count
                result += f"... and {remaining_subnets:,} more subnets.\n\n(Output capped at {DISPLAY_LIMIT} to prevent app freezing)"

            self.output_textbox.configure(state="normal")
            self.output_textbox.delete("0.0", "end")
            self.output_textbox.insert("0.0", result)
            self.output_textbox.configure(state="disabled")

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}\n\nEnsure target prefix is larger than current (e.g., split /24 into /25, or /32 into /48).")
        except OverflowError:
            messagebox.showerror("Error", "The split difference is too astronomically large to compute.")

if __name__ == "__main__":
    app = IPSubnetCalculatorApp()
    app.mainloop()
