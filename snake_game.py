import tkinter as tk
import random
import json
import os
from tkinter import messagebox


SCORE_FILE = os.path.join(os.path.dirname(__file__), ".snake_highscore.json")

# ----- Game Constants -----
GRID_SIZE = 20
CELL_SIZE = 25
WIDTH = 600
HEIGHT = 500
COLS = WIDTH // CELL_SIZE
ROWS = HEIGHT // CELL_SIZE
HEADER_HEIGHT = 50

# Colors
COLOR_BG = "#1a1a2e"
COLOR_GRID = "#16213e"
COLOR_SNAKE_HEAD = "#00d2ff"
COLOR_SNAKE_BODY = "#0f9b8e"
COLOR_FOOD = "#ff6b6b"
COLOR_FOOD_GLOW = "#ffd93d"
COLOR_TEXT = "#e0e0e0"
COLOR_ACCENT = "#6c63ff"

# Directions
DIRS = {
    "Up": (0, -1),
    "Down": (0, 1),
    "Left": (-1, 0),
    "Right": (1, 0),
}
OPPOSITE = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}


def load_highscore():
    try:
        if os.path.exists(SCORE_FILE):
            with open(SCORE_FILE, "r") as f:
                return json.load(f).get("highscore", 0)
    except:
        pass
    return 0


def save_highscore(score):
    try:
        with open(SCORE_FILE, "w") as f:
            json.dump({"highscore": score}, f)
    except:
        pass


class SnakeGame:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("贪吃蛇 Snake")
        self.window.resizable(False, False)
        self.window.configure(bg=COLOR_BG)

        # Center window
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = (sw - WIDTH) // 2
        y = (sh - HEIGHT - HEADER_HEIGHT) // 2
        self.window.geometry(f"{WIDTH}x{HEIGHT + HEADER_HEIGHT}+{x}+{y}")

        self.init_game()
        self.setup_ui()
        self.bind_keys()
        self.reset_game()

    # ---------- Game State ----------
    def init_game(self):
        self.highscore = load_highscore()
        self.difficulty = 150  # ms per tick
        self.direction = "Right"
        self.next_dir = "Right"
        self.running = False
        self.paused = False

    def reset_game(self):
        start_x = COLS // 4
        start_y = ROWS // 2
        self.snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = "Right"
        self.next_dir = "Right"
        self.score = 0
        self.paused = False
        self.running = False
        self.food = None
        self.canvas.focus_set()

    def start_game(self):
        self.running = True
        self.paused = False
        self.spawn_food()
        self.update_score_display()
        self.clear_overlay()
        self._tick()

    # ---------- UI Setup ----------
    def setup_ui(self):
        # Header frame
        header = tk.Frame(self.window, bg=COLOR_BG, height=HEADER_HEIGHT)
        header.pack(fill=tk.X, padx=15, pady=(8, 2))
        header.pack_propagate(False)

        self.score_label = tk.Label(
            header, text="分数: 0", font=("Segoe UI", 14, "bold"),
            fg=COLOR_TEXT, bg=COLOR_BG
        )
        self.score_label.pack(side=tk.LEFT)

        self.highscore_label = tk.Label(
            header, text=f"最高分: {self.highscore}", font=("Segoe UI", 11),
            fg=COLOR_ACCENT, bg=COLOR_BG
        )
        self.highscore_label.pack(side=tk.LEFT, padx=(20, 0))

        # Difficulty controls
        btn_frame = tk.Frame(header, bg=COLOR_BG)
        btn_frame.pack(side=tk.RIGHT)

        for txt, val in [("慢", 200), ("中", 150), ("快", 100)]:
            btn = tk.Button(
                btn_frame, text=txt, font=("Segoe UI", 9, "bold"),
                bg=COLOR_ACCENT, fg="white", relief=tk.FLAT,
                padx=10, pady=1, cursor="hand2",
                command=lambda v=val: self.set_difficulty(v)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Canvas
        self.canvas = tk.Canvas(
            self.window, width=WIDTH, height=HEIGHT,
            bg=COLOR_BG, highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.toggle_pause())

        # Draw grid background
        self.draw_grid()

        # Overlay for start / pause / game over
        self.overlay_id = None

    def draw_grid(self):
        self.canvas.delete("grid")
        for x in range(0, WIDTH, CELL_SIZE):
            self.canvas.create_line(
                x, 0, x, HEIGHT, fill=COLOR_GRID, tags="grid"
            )
        for y in range(0, HEIGHT, CELL_SIZE):
            self.canvas.create_line(
                0, y, WIDTH, y, fill=COLOR_GRID, tags="grid"
            )

    # ---------- Keyboard ----------
    def bind_keys(self):
        self.window.bind("<KeyPress>", self.on_key)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_key(self, e):
        key = e.keysym
        if not self.running:
            if key == "space":
                self.start_game()
            elif key.lower() == "r":
                self.restart()
            return
        if key in DIRS and key != OPPOSITE.get(self.direction):
            self.next_dir = key
        elif key == "space":
            self.toggle_pause()
        elif key.lower() == "r":
            self.restart()

    # ---------- Difficulty ----------
    def set_difficulty(self, ms):
        self.difficulty = ms
        if self.running and not self.paused:
            if hasattr(self, "_tick_id"):
                self.window.after_cancel(self._tick_id)
            self._tick()

    # ---------- Pause / Restart ----------
    def toggle_pause(self):
        if not self.running:
            self.start_game()
            return
        self.paused = not self.paused
        if self.paused:
            self.show_overlay("⏸  暂停", "按 Space 继续")
        else:
            self.clear_overlay()
            self._tick()

    def restart(self):
        if hasattr(self, "_tick_id"):
            self.window.after_cancel(self._tick_id)
        self.clear_overlay()
        self.reset_game()
        self.start_game()

    def on_close(self):
        if hasattr(self, "_tick_id"):
            self.window.after_cancel(self._tick_id)
        self.window.destroy()

    # ---------- Overlay ----------
    def show_overlay(self, line1, line2=""):
        self.clear_overlay()
        # Semi-transparent overlay
        self.overlay_bg = self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT, fill="#000000", stipple="gray25", tags="overlay"
        )
        self.overlay_id = self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 20, text=line1,
            font=("Segoe UI", 32, "bold"), fill=COLOR_ACCENT, tags="overlay"
        )
        if line2:
            self.canvas.create_text(
                WIDTH // 2, HEIGHT // 2 + 30, text=line2,
                font=("Segoe UI", 14), fill=COLOR_TEXT, tags="overlay"
            )

    def clear_overlay(self):
        self.canvas.delete("overlay")

    # ---------- Food ----------
    def spawn_food(self):
        occupied = set(self.snake)
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occupied]
        if not free:
            return
        self.food = random.choice(free)

    # ---------- Score ----------
    def update_score_display(self):
        self.score_label.config(text=f"分数: {self.score}")
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.highscore)
        self.highscore_label.config(text=f"最高分: {self.highscore}")

    # ---------- Game Loop ----------
    def _tick(self):
        if not self.running or self.paused:
            return

        self.direction = self.next_dir
        dx, dy = DIRS[self.direction]
        head = self.snake[0]
        new_head = (head[0] + dx, head[1] + dy)

        # Wall collision -> game over
        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.game_over()
            return

        # Self collision -> game over
        if new_head in self.snake:
            self.game_over()
            return

        self.snake.insert(0, new_head)

        # Eat food
        if new_head == self.food:
            self.score += 1
            self.update_score_display()
            self.spawn_food()
        else:
            self.snake.pop()

        self.draw()
        self._tick_id = self.window.after(self.difficulty, self._tick)

    # ---------- Drawing ----------
    def draw(self):
        self.canvas.delete("snake")
        self.canvas.delete("food_glow")
        self.canvas.delete("food")

        if self.food is None:
            return

        # Draw food glow
        fx, fy = self.food
        cx = fx * CELL_SIZE + CELL_SIZE // 2
        cy = fy * CELL_SIZE + CELL_SIZE // 2
        r = CELL_SIZE // 2 + 4
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=COLOR_FOOD_GLOW, outline="", tags="food_glow"
        )

        # Draw food
        r2 = CELL_SIZE // 2 - 2
        self.canvas.create_oval(
            cx - r2, cy - r2, cx + r2, cy + r2,
            fill=COLOR_FOOD, outline="", tags="food"
        )

        # Draw snake
        for i, (sx, sy) in enumerate(self.snake):
            x1 = sx * CELL_SIZE + 1
            y1 = sy * CELL_SIZE + 1
            x2 = x1 + CELL_SIZE - 2
            y2 = y1 + CELL_SIZE - 2

            if i == 0:
                color = COLOR_SNAKE_HEAD
                # Eyes
                eye_r = 3
                self.canvas.create_oval(
                    x1 + 5, y1 + 5, x1 + 5 + eye_r * 2, y1 + 5 + eye_r * 2,
                    fill="white", outline="", tags="snake"
                )
                self.canvas.create_oval(
                    x2 - 5 - eye_r * 2, y1 + 5, x2 - 5, y1 + 5 + eye_r * 2,
                    fill="white", outline="", tags="snake"
                )
            else:
                # Gradual color fading for body
                ratio = i / max(len(self.snake) - 1, 1)
                r_val = int(15 + (15 - 15 * ratio))
                g_val = int(155 - 60 * ratio)
                b_val = int(142 - 50 * ratio)
                color = f"#{r_val:02x}{max(g_val, 0):02x}{max(b_val, 0):02x}"

            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color, outline=COLOR_BG, tags="snake"
            )

    # ---------- Game Over ----------
    def game_over(self):
        self.running = False
        if hasattr(self, "_tick_id"):
            self.window.after_cancel(self._tick_id)

        if self.score > self.highscore:
            save_highscore(self.highscore)
            msg = f"🎉 新纪录！{self.score} 分！"
        else:
            msg = f"得分: {self.score}"

        self.show_overlay("游戏结束", f"{msg}    按 R 重新开始")

    # ---------- Run ----------
    def run(self):
        self.draw()
        self.show_overlay("贪吃蛇", "按 Space 或 R 开始游戏")
        self.window.mainloop()


if __name__ == "__main__":
    SnakeGame().run()
