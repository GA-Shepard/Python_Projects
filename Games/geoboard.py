import tkinter as tk
from random import choice

class GeoBoard:
    def __init__(self, root, rows=7, cols=7, peg_spacing=60):
        self.root = root
        self.rows = rows
        self.cols = cols
        self.peg_spacing = peg_spacing
        self.canvas_size = peg_spacing * (max(rows, cols) - 1) + 40

        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size, bg="white")
        self.canvas.pack()

        self.pegs = []
        self.bands = []
        self.current_band = []

        self.colors = ["red", "blue", "green", "orange", "purple", "brown", "black"]

        self.draw_pegs()
        self.canvas.bind("<Button-1>", self.on_click)

        self.reset_button = tk.Button(root, text="Reset Board", command=self.reset)
        self.reset_button.pack(pady=10)

    def draw_pegs(self):
        self.pegs.clear()
        for row in range(self.rows):
            for col in range(self.cols):
                x = 20 + col * self.peg_spacing
                y = 20 + row * self.peg_spacing
                peg = (x, y)
                self.pegs.append(peg)
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="black")

    def on_click(self, event):
        clicked_peg = self.find_nearest_peg(event.x, event.y)
        if clicked_peg:
            self.current_band.append(clicked_peg)
            if len(self.current_band) > 1:
                color = choice(self.colors)
                self.canvas.create_line(
                    self.current_band[-2][0], self.current_band[-2][1],
                    self.current_band[-1][0], self.current_band[-1][1],
                    fill=color, width=3
                )
            # Right-click to end band and start a new one
            self.canvas.bind("<Button-3>", self.start_new_band)

    def start_new_band(self, event):
        self.current_band = []

    def find_nearest_peg(self, x, y, radius=10):
        for peg in self.pegs:
            if abs(peg[0] - x) <= radius and abs(peg[1] - y) <= radius:
                return peg
        return None

    def reset(self):
        self.canvas.delete("all")
        self.draw_pegs()
        self.current_band = []
        self.bands = []

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Python Geoboard")
    geoboard = GeoBoard(root)
    root.mainloop()
