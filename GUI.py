import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import webbrowser  # Import webbrowser module for opening URLs
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import io
import sys
import subprocess
import threading

class PlotRedirector(io.StringIO):
    def __init__(self, console_output, plot_frame):
        self.console_output = console_output
        self.plot_frame = plot_frame
        self.figure_num = 0  # Initialize figure number
        io.StringIO.__init__(self)

    def write(self, buf):
        self.console_output.insert(tk.END, buf)
        self.console_output.see(tk.END)  # Scroll to the end of the text
        if buf.startswith('Figure('):
            self.figure_num += 1  # Increment figure number
            plt.figure(self.figure_num)
            canvas = FigureCanvasTkAgg(plt.gcf(), master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def start_script(console_output):
    process = subprocess.Popen(["python", "main.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            console_output.insert(tk.END, output)
            console_output.see(tk.END)  # Scroll to the end of the text
    process.stdout.close()

def dark_mode(window):
    window.configure(bg='#2b2b2b')
    window.tk_setPalette(background='#2b2b2b', foreground='white')
    style = ttk.Style()
    style.theme_use("clam")  # Choose a ttk theme
    style.configure("Dark.TButton", background="#444", foreground="white", font=("Helvetica", 12))

def open_website():
    webbrowser.open_new("http://82.130.67.100:3000/d/a7518efa-87cd-47f5-80ac-fdb3079936cb/quinto-164?orgId=1")  # Replace "https://example.com" with the desired website URL

def create_gui():
    root = tk.Tk()
    root.title("Thermal Compensation Software")
    root.geometry('1000x600')  # Set initial size
    dark_mode(root)

    console_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, bg="black", fg="green", font=("Courier", 8))  # Adjust font size here
    console_output.grid(row=0, column=0, rowspan=2, sticky="nsew")

    plot_frame = ttk.Frame(root)
    plot_frame.grid(row=0, column=1, sticky="nsew")

    web_frame = ttk.Frame(root)
    web_frame.grid(row=1, column=1, sticky="nsew")
    open_website_button = ttk.Button(web_frame, text="Open Website", command=open_website)
    open_website_button.pack(pady=10)

    # Configure grid weights to distribute space horizontally and vertically
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)  # Stretch the first column
    root.grid_columnconfigure(1, weight=1)  # Stretch the second column

    start_button = ttk.Button(root, text="Start Script", style="Dark.TButton")
    start_button["command"] = lambda: threading.Thread(target=start_script, args=(console_output,), daemon=True).start()
    start_button.grid(row=2, column=0, columnspan=2, pady=10)

    return root, console_output, plot_frame

if __name__ == "__main__":
    gui, console_output, plot_frame = create_gui()

    # Redirect stdout to PlotRedirector
    sys.stdout = PlotRedirector(console_output, plot_frame)

    gui.mainloop()











