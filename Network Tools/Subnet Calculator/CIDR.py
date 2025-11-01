import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ipaddress
import math

# Generate full subnet reference /0 to /30
def generate_quick_subnets():
    quick_list = []
    for prefix in range(30, -1, -1):
        try:
            net = ipaddress.IPv4Network(f"0.0.0.0/{prefix}")
            hosts = max(net.num_addresses - 2, 0)
            quick_list.append((f"/{prefix}", str(net.netmask), f"{hosts:,} usable hosts"))
        except Exception:
            continue
    return quick_list

# Add Classful Ranges
CLASSFUL_RANGES = [
    ("Class A", "1.0.0.0 - 126.255.255.255", "/8"),
    ("Class B", "128.0.0.0 - 191.255.255.255", "/16"),
    ("Class C", "192.0.0.0 - 223.255.255.255", "/24"),
    ("Class D", "224.0.0.0 - 239.255.255.255", "Multicast"),
    ("Class E", "240.0.0.0 - 255.255.255.255", "Experimental")
]

QUICK_SUBNETS = generate_quick_subnets()

def calculate_subnet(ip_input):
    try:
        net = ipaddress.ip_network(ip_input, strict=False)
        data = {
            "Network Address": str(net.network_address),
            "Broadcast Address": str(net.broadcast_address) if isinstance(net, ipaddress.IPv4Network) else 'N/A',
            "Subnet Mask": str(net.netmask),
            "Wildcard Mask": str(net.hostmask) if isinstance(net, ipaddress.IPv4Network) else 'N/A',
            "Number of Hosts": net.num_addresses - 2 if net.num_addresses > 2 else net.num_addresses,
            "First Host": str(list(net.hosts())[0]) if net.num_addresses > 1 else 'N/A',
            "Last Host": str(list(net.hosts())[-1]) if net.num_addresses > 1 else 'N/A',
            "CIDR": f"/{net.prefixlen}"
        }
        return data
    except Exception as e:
        return {"Error": str(e)}

def supernet_merge(ip_list):
    try:
        networks = [ipaddress.ip_network(ip.strip(), strict=False) for ip in ip_list.split(',')]
        merged = list(ipaddress.collapse_addresses(networks))
        return {f"Supernet {i+1}": str(net) for i, net in enumerate(merged)}
    except Exception as e:
        return {"Error": str(e)}

def show_quick_reference():
    ref_window = tk.Toplevel(bg='black')
    ref_window.title("Quick Subnet Reference")
    ref_window.geometry("600x400")

    tab_control = ttk.Notebook(ref_window)

    subnet_tab = ttk.Frame(tab_control)
    class_tab = ttk.Frame(tab_control)
    tab_control.add(subnet_tab, text='Subnets')
    tab_control.add(class_tab, text='Classful Ranges')

    subnet_tree = ttk.Treeview(subnet_tab, columns=("CIDR", "Subnet Mask", "Hosts"), show="headings")
    subnet_tree.heading("CIDR", text="CIDR")
    subnet_tree.heading("Subnet Mask", text="Subnet Mask")
    subnet_tree.heading("Hosts", text="Usable Hosts")

    for row in QUICK_SUBNETS:
        subnet_tree.insert("", "end", values=row)
    subnet_tree.pack(fill=tk.BOTH, expand=True)

    class_tree = ttk.Treeview(class_tab, columns=("Class", "Range", "Default Mask"), show="headings")
    class_tree.heading("Class", text="Class")
    class_tree.heading("Range", text="Range")
    class_tree.heading("Default Mask", text="Default Mask")

    for row in CLASSFUL_RANGES:
        class_tree.insert("", "end", values=row)
    class_tree.pack(fill=tk.BOTH, expand=True)

    tab_control.pack(expand=True, fill='both')

def perform_calculation():
    ip_input = ip_entry.get()
    result = calculate_subnet(ip_input)
    output.delete("1.0", tk.END)
    if "Error" in result:
        output.insert(tk.END, f"Error: {result['Error']}")
    else:
        for k, v in result.items():
            output.insert(tk.END, f"{k}: {v}\n")

def perform_supernetting():
    ip_input = ip_entry.get()
    result = supernet_merge(ip_input)
    output.delete("1.0", tk.END)
    if "Error" in result:
        output.insert(tk.END, f"Error: {result['Error']}")
    else:
        for k, v in result.items():
            output.insert(tk.END, f"{k}: {v}\n")

def export_results():
    content = output.get("1.0", tk.END)
    if content.strip():
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, 'w') as f:
                f.write(content)

def apply_apple_theme(widget):
    widget.configure(bg='black', fg='white', insertbackground='white', relief=tk.FLAT)

def on_drop(event):
    try:
        ip_entry.delete(0, tk.END)
        ip_entry.insert(0, event.data)
    except Exception as e:
        messagebox.showerror("Drop Error", str(e))

def visualize_subnet():
    ip_input = ip_entry.get()
    try:
        net = ipaddress.ip_network(ip_input, strict=False)
        vis_window = tk.Toplevel()
        vis_window.title("Subnet Tree")
        vis_window.geometry("600x400")
        tree = ttk.Treeview(vis_window)
        tree.heading("#0", text="Subnet Breakdown")

        def insert_subnets(node, net):
            tree.insert(node, 'end', text=str(net))
            if net.prefixlen < 30:
                for sub in net.subnets(new_prefix=net.prefixlen + 1):
                    insert_subnets(node, sub)

        insert_subnets('', net)
        tree.pack(fill=tk.BOTH, expand=True)
    except Exception as e:
        messagebox.showerror("Visualization Error", str(e))

# GUI Setup
root = tk.Tk()
root.title("Subnet Calculator")
root.geometry("520x550")
root.configure(bg='black')

menu = tk.Menu(root)
root.config(menu=menu)

ref_menu = tk.Menu(menu, tearoff=0)
menu.add_cascade(label="Reference", menu=ref_menu)
ref_menu.add_command(label="Quick Subnet Reference", command=show_quick_reference)
ref_menu.add_command(label="Export Results", command=export_results)

label = tk.Label(root, text="Enter IPs (comma separated or CIDR):", bg='black', fg='white')
label.pack(pady=10)

ip_entry = tk.Entry(root, width=40)
ip_entry.pack()
apply_apple_theme(ip_entry)

btn_frame = tk.Frame(root, bg='black')
btn_frame.pack(pady=10)

calc_btn = tk.Button(btn_frame, text="Calculate Subnet", command=perform_calculation, bg='#333', fg='white')
calc_btn.grid(row=0, column=0, padx=5)

supernet_btn = tk.Button(btn_frame, text="Supernet Merge", command=perform_supernetting, bg='#666', fg='white')
supernet_btn.grid(row=0, column=1, padx=5)

visual_btn = tk.Button(btn_frame, text="Visualize Subnets", command=visualize_subnet, bg='#444', fg='white')
visual_btn.grid(row=0, column=2, padx=5)

export_btn = tk.Button(btn_frame, text="Export", command=export_results, bg='#999', fg='black')
export_btn.grid(row=0, column=3, padx=5)

output = tk.Text(root, height=20, width=60, bg='black', fg='lime', insertbackground='white')
output.pack(pady=10)

root.mainloop()
