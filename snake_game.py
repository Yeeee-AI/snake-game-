import tkinter as tk
import random
import json
import os
import time
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
COLOR_TEXT = "#e0e0e0"
COLOR_ACCENT = "#6c63ff"
COLOR_OBSTACLE = "#4a4a6a"
COLOR_OBSTACLE_GLOW = "#5a5a7a"

# Food types
FOOD_TYPES = [
    {"id": "normal", "color": "#4ade80", "glow": "#86efac", "score": 1, "weight": 55},
    {"id": "golden", "color": "#fbbf24", "glow": "#fde68a", "score": 3, "weight": 20},
    {"id": "speed",  "color": "#f87171", "glow": "#fca5a5", "score": 2, "weight": 15},
    {"id": "shrink", "color": "#60a5fa", "glow": "#93c5fd", "score": 2, "weight": 10},
]

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


def weighted_choice(items):
    total = sum(item["weight"] for item in items)
    r = random.uniform(0, total)
    upto = 0
    for item in items:
        upto += item["weight"]
        if r <= upto:
            return item
    return items[0]


class SnakeGame:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("贪吃蛇 Snake")
        self.window.resizable(False, False)
        self.window.configure(bg=COLOR_BG)

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
        self.base_difficulty = 150
        self.difficulty = 150
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
        self.food_type = None
        self.food_spawn_time = 0
        self.obstacles = []
        self.level = 1
        self.combo = 0
        self.last_eat_time = 0
        self.combo_popups = []
        self.speed_boost_until = 0
        self.is_speed_boosted = False
        self.golden_timer_id = None
        self.anim_id = None
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

        self.level_label = tk.Label(
            header, text="Lv.1", font=("Segoe UI", 11, "bold"),
            fg="#fbbf24", bg=COLOR_BG
        )
        self.level_label.pack(side=tk.LEFT, padx=(20, 0))

        self.combo_label = tk.Label(
            header, text="", font=("Segoe UI", 11, "bold"),
            fg="#fbbf24", bg=COLOR_BG
        )
        self.combo_label.pack(side=tk.LEFT, padx=(10, 0))

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

        self.canvas = tk.Canvas(
            self.window, width=WIDTH, height=HEIGHT,
            bg=COLOR_BG, highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.toggle_pause())

        self.draw_grid()
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
        self.base_difficulty = ms
        self.update_tick_speed()
        if self.running and not self.paused:
            if hasattr(self, "_tick_id"):
                self.window.after_cancel(self._tick_id)
            self._tick()

    def update_tick_speed(self):
        level_bonus = max(0, self.level - 1) * 5
        boost_penalty = 40 if self.is_speed_boosted else 0
        self.difficulty = max(50, self.base_difficulty - level_bonus - boost_penalty)

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
        if self.golden_timer_id:
            self.window.after_cancel(self.golden_timer_id)
            self.golden_timer_id = None
        if self.anim_id:
            self.window.after_cancel(self.anim_id)
            self.anim_id = None
        self.clear_overlay()
        self.reset_game()
        self.start_game()

    def on_close(self):
        if hasattr(self, "_tick_id"):
            self.window.after_cancel(self._tick_id)
        if self.golden_timer_id:
            self.window.after_cancel(self.golden_timer_id)
        if self.anim_id:
            self.window.after_cancel(self.anim_id)
        self.window.destroy()

    # ---------- Overlay ----------
    def show_overlay(self, line1, line2="", line3=""):
        self.clear_overlay()
        self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT, fill="#000000", stipple="gray25", tags="overlay"
        )
        self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 20, text=line1,
            font=("Segoe UI", 32, "bold"), fill=COLOR_ACCENT, tags="overlay"
        )
        if line2:
            self.canvas.create_text(
                WIDTH // 2, HEIGHT // 2 + 30, text=line2,
                font=("Segoe UI", 14), fill=COLOR_TEXT, tags="overlay"
            )
        if line3:
            self.canvas.create_text(
                WIDTH // 2, HEIGHT // 2 + 55, text=line3,
                font=("Segoe UI", 12), fill="#888888", tags="overlay"
            )

    def clear_overlay(self):
        self.canvas.delete("overlay")

    # ---------- Obstacles ----------
    def get_occupied(self):
        occ = set(self.snake)
        if self.food:
            occ.add(self.food)
        occ.update(self.obstacles)
        return occ

    def spawn_obstacles(self):
        new_count = min(self.level * 2, 20)
        while len(self.obstacles) < new_count:
            occ = self.get_occupied()
            free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occ]
            if not free:
                break
            obs = random.choice(free)
            self.obstacles.append(obs)
            occ.add(obs)

    # ---------- Food ----------
    def spawn_food(self):
        occ = self.get_occupied()
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occ]
        if not free:
            return
        choice = weighted_choice(FOOD_TYPES)
        self.food = random.choice(free)
        self.food_type = choice
        self.food_spawn_time = time.time()

        # Golden food disappears after 6 seconds
        if self.golden_timer_id:
            self.window.after_cancel(self.golden_timer_id)
            self.golden_timer_id = None
        if self.food_type["id"] == "golden":
            self.golden_timer_id = self.window.after(6000, self.on_golden_expire)

    def on_golden_expire(self):
        self.golden_timer_id = None
        if self.running and not self.paused and self.food and self.food_type["id"] == "golden":
            self.show_floating_text(self.food[0], self.food[1], "消失!", "#888888")
            self.food = None
            self.food_type = None
            self.spawn_food()
            self.draw()

    # ---------- Floating Text (Combo / Score Popups) ----------
    def show_floating_text(self, gx, gy, text, color="#ffffff"):
        cx = gx * CELL_SIZE + CELL_SIZE // 2
        cy = gy * CELL_SIZE + CELL_SIZE // 2
        tid = self.canvas.create_text(
            cx, cy, text=text, font=("Segoe UI", 14, "bold"),
            fill=color, tags="float"
        )
        # Animate upward
        self._animate_float(tid, cy, 0)

    def _animate_float(self, tid, start_y, step):
        if step > 20:
            return
        self.canvas.coords(tid, WIDTH // 2, start_y - step * 2)
        alpha = max(0, 1 - step / 20)
        if step < 10:
            size = 14 + step
        else:
            size = 24 - step
        self.canvas.itemconfig(tid, font=("Segoe UI", int(size), "bold"))
        self.anim_id = self.window.after(30, lambda: self._animate_float(tid, start_y, step + 1))

    # ---------- Combo ----------
    def check_combo(self):
        now = time.time()
        if now - self.last_eat_time < 1.5 and self.last_eat_time > 0:
            self.combo += 1
        else:
            self.combo = 1
        self.last_eat_time = now

        if self.combo >= 3:
            self.combo_label.config(text=f"🔥 {self.combo}连击!")
        elif self.combo == 2:
            self.combo_label.config(text=f"✨ x{self.combo}")
        else:
            self.combo_label.config(text="")

    # ---------- Score ----------
    def update_score_display(self):
        self.score_label.config(text=f"分数: {self.score}")
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.highscore)
        self.highscore_label.config(text=f"最高分: {self.highscore}")

        new_level = self.score // 10 + 1
        if new_level != self.level:
            self.level = new_level
            self.level_label.config(text=f"Lv.{self.level}")
            self.update_tick_speed()
            self.spawn_obstacles()
            self.show_floating_text(COLS // 2, ROWS // 2, f"LEVEL {self.level}!", "#fbbf24")

    # ---------- Game Loop ----------
    def _tick(self):
        if not self.running or self.paused:
            return

        # Check speed boost expiry
        if self.is_speed_boosted and time.time() > self.speed_boost_until:
            self.is_speed_boosted = False
            self.update_tick_speed()

        self.direction = self.next_dir
        dx, dy = DIRS[self.direction]
        head = self.snake[0]
        new_head = (head[0] + dx, head[1] + dy)

        # Wall collision
        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.game_over()
            return

        # Self collision
        if new_head in self.snake:
            self.game_over()
            return

        # Obstacle collision
        if new_head in self.obstacles:
            self.game_over()
            return

        self.snake.insert(0, new_head)

        # Eat food
        if self.food and new_head == self.food:
            ft = self.food_type
            gained = ft["score"]
            self.score += gained
            self.check_combo()

            # Combo bonus
            combo_bonus = 0
            if self.combo >= 3:
                combo_bonus = self.combo // 2
                self.score += combo_bonus

            # Show floating score
            txt = f"+{gained}"
            if combo_bonus > 0:
                txt += f" (+{combo_bonus} combo)"
            self.show_floating_text(new_head[0], new_head[1], txt, ft["color"])

            # Food effects
            if ft["id"] == "speed":
                self.speed_boost_until = time.time() + 5
                self.is_speed_boosted = True
                self.update_tick_speed()
            elif ft["id"] == "shrink" and len(self.snake) > 4:
                # Remove from tail
                remove_n = min(3, len(self.snake) - 3)
                for _ in range(remove_n):
                    self.snake.pop()

            self.update_score_display()
            self.food = None
            self.food_type = None
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
        self.canvas.delete("obstacle")
        self.canvas.delete("float")

        # Draw obstacles
        for ox, oy in self.obstacles:
            x1 = ox * CELL_SIZE + 2
            y1 = oy * CELL_SIZE + 2
            x2 = x1 + CELL_SIZE - 4
            y2 = y1 + CELL_SIZE - 4
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=COLOR_OBSTACLE, outline=COLOR_OBSTACLE_GLOW,
                tags="obstacle"
            )

        # Draw food
        if self.food and self.food_type:
            fx, fy = self.food
            cx = fx * CELL_SIZE + CELL_SIZE // 2
            cy = fy * CELL_SIZE + CELL_SIZE // 2

            # Food icon based on type
            r = CELL_SIZE // 2 - 3
            if self.food_type["id"] == "normal":
                # Circle
                r2 = CELL_SIZE // 2 + 4
                self.canvas.create_oval(
                    cx - r2, cy - r2, cx + r2, cy + r2,
                    fill=self.food_type["glow"], outline="", tags="food_glow"
                )
                self.canvas.create_oval(
                    cx - r, cy - r, cx + r, cy + r,
                    fill=self.food_type["color"], outline="", tags="food"
                )
            elif self.food_type["id"] == "golden":
                # Star/diamond shape
                r2 = CELL_SIZE // 2 + 5
                self.canvas.create_oval(
                    cx - r2, cy - r2, cx + r2, cy + r2,
                    fill=self.food_type["glow"], outline="", tags="food_glow"
                )
                self.canvas.create_polygon(
                    cx, cy - r - 2,
                    cx + r - 2, cy,
                    cx, cy + r + 2,
                    cx - r + 2, cy,
                    fill=self.food_type["color"], outline="", tags="food"
                )
            elif self.food_type["id"] == "speed":
                # Lightning bolt shape (triangle pointing right)
                r2 = CELL_SIZE // 2 + 4
                self.canvas.create_oval(
                    cx - r2, cy - r2, cx + r2, cy + r2,
                    fill=self.food_type["glow"], outline="", tags="food_glow"
                )
                self.canvas.create_polygon(
                    cx - r - 2, cy - r - 2,
                    cx + r + 2, cy,
                    cx - r - 2, cy + r + 2,
                    fill=self.food_type["color"], outline="", tags="food"
                )
            elif self.food_type["id"] == "shrink":
                # Small square
                r2 = CELL_SIZE // 2 + 4
                self.canvas.create_oval(
                    cx - r2, cy - r2, cx + r2, cy + r2,
                    fill=self.food_type["glow"], outline="", tags="food_glow"
                )
                self.canvas.create_rectangle(
                    cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1,
                    fill=self.food_type["color"], outline="", tags="food"
                )

        # Draw snake
        for i, (sx, sy) in enumerate(self.snake):
            x1 = sx * CELL_SIZE + 1
            y1 = sy * CELL_SIZE + 1
            x2 = x1 + CELL_SIZE - 2
            y2 = y1 + CELL_SIZE - 2

            if i == 0:
                color = COLOR_SNAKE_HEAD
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
        if self.golden_timer_id:
            self.window.after_cancel(self.golden_timer_id)
            self.golden_timer_id = None

        if self.score > self.highscore:
            save_highscore(self.highscore)
            msg = f"🎉 新纪录！{self.score} 分！"
        else:
            msg = f"得分: {self.score}"

        combo_info = f"最高连击: {self.combo}" if self.combo >= 3 else ""
        self.show_overlay("游戏结束", msg, combo_info + "  按 R 重新开始")

    # ---------- Run ----------
    def run(self):
        self.draw()
        self.show_overlay("贪吃蛇", "按 Space 或 R 开始游戏",
                          "多种食物 · 障碍物 · 连击 · 升级")
        self.window.mainloop()


if __name__ == "__main__":
    SnakeGame().run()
