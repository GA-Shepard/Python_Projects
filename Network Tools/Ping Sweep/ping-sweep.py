import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import ipaddress
import subprocess
import platform
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS = 50

def ping_host(ip, count, timeout):
    system = platform.system().lower()
    count_param = '-n' if system == 'windows' else '-c'
    timeout_param = '-w' if system == 'windows' else '-W'
    try:
        result = subprocess.run(
            ['ping', count_param, str(count), timeout_param, str(timeout), str(ip)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return str(ip), result.returncode == 0
    except Exception:
        return str(ip), False

def update_output(text_widget, msg):
    text_widget.insert(tk.END, msg + '\n')
    text_widget.see(tk.END)
    text_widget.update()

def get_ip_range(start_ip, end_ip, subnet):
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        start = ipaddress.ip_address(start_ip)
        end = ipaddress.ip_address(end_ip)
        return [ip for ip in network.hosts() if start <= ip <= end]
    except Exception as e:
        return None

def start_sweep(subnet, start_ip, end_ip, count, timeout, output_text, result_list):
    try:
        if start_ip and end_ip:
            ip_range = get_ip_range(start_ip, end_ip, subnet)
            if not ip_range:
                raise ValueError("Invalid IP range within subnet.")
        else:
            ip_range = list(ipaddress.ip_network(subnet, strict=False).hosts())
    except ValueError as e:
        messagebox.showerror("Invalid Input", str(e))
        return

    update_output(output_text, f"Pinging subnet: {subnet}")
    update_output(output_text, f"Ping count: {count}, Timeout: {timeout}ms")
    update_output(output_text, f"Range: {start_ip} - {end_ip}" if start_ip and end_ip else "Range: full subnet")
    update_output(output_text, "Starting sweep...\n")

    responsive_hosts = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(ping_host, ip, count, timeout): ip for ip in ip_range}

        for future in as_completed(futures):
            ip, is_up = future.result()
            if is_up:
                responsive_hosts.append(ip)
                update_output(output_text, f"[+] Host Up: {ip}")
            else:
                update_output(output_text, f"[-] No Response: {ip}")

    update_output(output_text, "\nSweep complete.")
    update_output(output_text, f"{len(responsive_hosts)} host(s) responded.\n")
    result_list.clear()
    result_list.extend(responsive_hosts)

def threaded_sweep(subnet_entry, start_ip_entry, end_ip_entry,
                   count_entry, timeout_entry, output_text, result_list):
    subnet = subnet_entry.get().strip()
    start_ip = start_ip_entry.get().strip()
    end_ip = end_ip_entry.get().strip()
    try:
        count = int(count_entry.get())
        timeout = int(timeout_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Ping count and timeout must be integers.")
        return

    thread = threading.Thread(
        target=start_sweep,
        args=(subnet, start_ip, end_ip, count, timeout, output_text, result_list),
        daemon=True
    )
    thread.start()

def export_results(results):
    if not results:
        messagebox.showinfo("Export", "No results to export.")
        return

    filepath = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt")])
    if filepath:
        try:
            with open(filepath, 'w') as f:
                for host in results:
                    f.write(f"{host}\n")
            messagebox.showinfo("Export Successful", f"Results saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

def main():
    root = tk.Tk()
    root.title("Enhanced ICMP Ping Sweep Tool")
    root.geometry("750x600")

    tk.Label(root, text="Enter Subnet (e.g., 192.168.1.0/24):").pack(pady=2)
    subnet_entry = tk.Entry(root, width=40)
    subnet_entry.pack()

    range_frame = tk.Frame(root)
    range_frame.pack(pady=2)
    tk.Label(range_frame, text="Start IP (optional):").grid(row=0, column=0, padx=2)
    start_ip_entry = tk.Entry(range_frame, width=15)
    start_ip_entry.grid(row=0, column=1)

    tk.Label(range_frame, text="End IP (optional):").grid(row=0, column=2, padx=2)
    end_ip_entry = tk.Entry(range_frame, width=15)
    end_ip_entry.grid(row=0, column=3)

    config_frame = tk.Frame(root)
    config_frame.pack(pady=2)
    tk.Label(config_frame, text="Ping Count:").grid(row=0, column=0, padx=2)
    count_entry = tk.Entry(config_frame, width=5)
    count_entry.insert(0, "1")
    count_entry.grid(row=0, column=1)

    tk.Label(config_frame, text="Timeout (ms):").grid(row=0, column=2, padx=2)
    timeout_entry = tk.Entry(config_frame, width=5)
    timeout_entry.insert(0, "1000")
    timeout_entry.grid(row=0, column=3)

    output_text = scrolledtext.ScrolledText(root, width=85, height=25)
    output_text.pack(pady=10)

    results = []

    button_frame = tk.Frame(root)
    button_frame.pack()

    sweep_button = tk.Button(button_frame, text="Start Ping Sweep",
                             command=lambda: threaded_sweep(
                                 subnet_entry, start_ip_entry, end_ip_entry,
                                 count_entry, timeout_entry, output_text, results))
    sweep_button.pack(side=tk.LEFT, padx=10)

    export_button = tk.Button(button_frame, text="Export Results",
                              command=lambda: export_results(results))
    export_button.pack(side=tk.LEFT, padx=10)

    root.mainloop()

if __name__ == "__main__":
    main()
