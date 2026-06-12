import json
import math
import socket
import threading
import time
import tkinter as tk
from pathlib import Path


GRID_SIZE = 5
SCORE_TARGET = 13
MIN_BOARD_SIZE = 1
MAX_BOARD_SIZE = 8
MAX_TILE_SIZE = 84
MIN_TILE_SIZE = 44
MAX_BOARD_PIXEL_SIZE = 560
PORT = 5000
LOBBY_SLOT_COUNT = 5
MAX_PLAYERS = 5

APP_TITLE = "Task Knockout Client"
# Public release version.
APP_VERSION = "v1.0.0"
DEFAULT_HOST_IP = "127.0.0.1"
SCRIPT_DIR = Path(__file__).resolve().parent
CLIENT_CONFIG_FILE = SCRIPT_DIR / "taskknockout_client_config.json"

STATUS_EMPTY = "empty"
STATUS_POSSIBLE = "possible"
STATUS_COMPLETE = "complete"
STATUS_PENDING = "pending"
HARD_PENDING_SECONDS = 10
IMPOSSIBLE_PENDING_SECONDS = 30

BG = "#080d0f"
PANEL_BG = "#0e1518"
EMPTY_TILE = "#070b0d"
PENDING_TILE = "#142028"
PENDING_OUTLINE = "#8fb4c9"
IMPOSSIBLE_TILE = "#201625"
IMPOSSIBLE_PENDING_TILE = "#251b2b"
IMPOSSIBLE_COMPLETE_TILE = "#2a2216"
IMPOSSIBLE_OUTLINE = "#d6982f"
BORDER = "#263238"
TEXT = "#f5fbfc"
MUTED_TEXT = "#9aa8ad"
DIFFICULTY_LABEL_COLORS = {
    "easy": "#6f8f78",
    "medium": "#9a9060",
    "hard": "#9a6a6a",
    "impossible": "#8a729a",
}
PLAYER_COLORS = {
    1: {"main": "#14a7a5", "dark": "#0c6f72"},
    2: {"main": "#b33428", "dark": "#782017"},
    3: {"main": "#d6982f", "dark": "#8a611b"},
    4: {"main": "#6e70d8", "dark": "#3f4190"},
    5: {"main": "#4da85f", "dark": "#2d6b3a"},
}
FALLBACK_PLAYER_COLOR = {"main": MUTED_TEXT, "dark": BORDER}
P1_COLOR = PLAYER_COLORS[1]["main"]
P1_DARK = PLAYER_COLORS[1]["dark"]
P2_COLOR = PLAYER_COLORS[2]["main"]
P2_DARK = PLAYER_COLORS[2]["dark"]
ACCENT = P1_COLOR
ERROR = "#ff6b5c"
GOOD = "#62d18f"
BUTTON_BG = "#162126"
BUTTON_ACTIVE = "#22333a"

TITLE_FONT = ("Arial", 22, "bold")
SUBTITLE_FONT = ("Arial", 11, "bold")
BODY_FONT = ("Arial", 11)
SMALL_FONT = ("Arial", 9)
TILE_FONT = ("Arial", 9, "bold")
DIFFICULTY_LABEL_FONT = ("Arial", 6, "bold")
SCORE_FONT = ("Arial", 12, "bold")
WINNER_FONT = ("Arial", 13, "bold")

TILE_GAP = 4
SWAP_OVERLAY_PURPLE = "#5b2a73"
SWAP_OVERLAY_FADE = ["#4b245f", "#3b1d4c", "#2c1738"]
SWAP_TEXT_FADE = ["#e8dff0", "#c9b7d3", "#9f86ad"]
SWAP_SCROLL_TEXT = (
    "SWAPPING   SWAPPING   SWAPPING   SWAPPING   "
    "SWAPPING   SWAPPING   SWAPPING   SWAPPING   "
)


class TaskKnockoutClient:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.conn = None
        self.lock = threading.Lock()
        self.disconnected = False
        self.suppress_disconnect_notice = False

        self.player = None
        self.player_name = self.load_saved_player_name() or "Player 2"
        self.player_names = self.default_player_names()
        self.host_ip = ""
        self.ready = False
        self.lobby_ready_states = {1: True}
        self.connected_players = {1}
        self.active_players = [1]
        self.match_player_ids = [1]
        self.player_colors = dict(PLAYER_COLORS)
        self.match_active = False
        self.winner = None
        self.last_announced_winner = None
        self.match_start_time = None
        self.match_end_time = None
        self.board_rows = GRID_SIZE
        self.board_cols = GRID_SIZE
        self.score_target = SCORE_TARGET
        self.hard_verification_enabled = False
        self.swap_mode_enabled = False
        self.swap_charges = {player: 0 for player in range(1, MAX_PLAYERS + 1)}
        self.forced_swap_players = set()
        self.last_reroll_animation_id = None
        self.reroll_animation_keys = {}
        self.ui_generation = 0
        self.animation_after_ids = []
        self.active_tile_animations = {}
        self.local_timer_freeze = None
        self.timer_after_id = None

        self.task_data = {"tasks": []}
        self.board = self.empty_board()
        self.local_possible = set()

        self.name_entry = None
        self.ip_entry = None
        self.setup_error_label = None
        self.lobby_status_label = None
        self.lobby_connection_label = None
        self.lobby_host_label = None
        self.lobby_you_label = None
        self.lobby_countdown_label = None
        self.lobby_rows = {}
        self.ready_button = None
        self.leave_lobby_button = None
        self.status_label = None
        self.timer_label = None
        self.tiles = []
        self.score_bar = None
        self.score_labels = {}
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None
        self.board_container = None
        self.board_canvas = None

        self.show_connect_screen()

    def load_client_config(self):
        try:
            with CLIENT_CONFIG_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def save_client_config(self, updates):
        data = self.load_client_config()
        data.update(updates)
        try:
            with CLIENT_CONFIG_FILE.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
        except OSError:
            pass

    def load_saved_host_ip(self):
        data = self.load_client_config()
        if not data:
            return DEFAULT_HOST_IP
        saved_ip = str(data.get("last_host_ip", "")).strip()
        return saved_ip or DEFAULT_HOST_IP

    def load_saved_player_name(self):
        data = self.load_client_config()
        saved_name = str(data.get("last_player_name", "")).strip()
        return saved_name[:22]

    def save_host_ip(self, host_ip):
        host_ip = str(host_ip or "").strip()
        if not host_ip:
            return
        self.save_client_config({"last_host_ip": host_ip})

    def save_player_name(self, player_name):
        player_name = str(player_name or "").strip()[:22]
        if not player_name:
            return
        self.save_client_config({"last_player_name": player_name})

    def default_player_names(self):
        return {player: f"Player {player}" for player in range(1, MAX_PLAYERS + 1)}

    def player_color(self, player):
        return self.player_colors.get(player, FALLBACK_PLAYER_COLOR)["main"]

    def player_dark(self, player):
        return self.player_colors.get(player, FALLBACK_PLAYER_COLOR)["dark"]

    def parse_player_list(self, raw_players, fallback=None):
        players = set(fallback or {1})
        if isinstance(raw_players, (list, tuple, set)):
            players = set()
            for value in raw_players:
                try:
                    player = int(value)
                except (TypeError, ValueError):
                    continue
                if 1 <= player <= MAX_PLAYERS:
                    players.add(player)
        if 1 not in players:
            players.add(1)
        return players

    def active_game_players(self):
        players = list(self.match_player_ids or self.active_players or sorted(self.connected_players))
        if self.player is not None and self.player not in players:
            players.append(self.player)
        if 1 not in players:
            players.insert(0, 1)
        return sorted({player for player in players if 1 <= player <= MAX_PLAYERS})

    def apply_player_colors(self, raw_colors):
        if not isinstance(raw_colors, dict):
            return
        colors = dict(self.player_colors)
        for key, value in raw_colors.items():
            try:
                player = int(key)
            except (TypeError, ValueError):
                continue
            if not (1 <= player <= MAX_PLAYERS):
                continue
            if isinstance(value, dict):
                main = value.get("main")
                dark = value.get("dark")
                if isinstance(main, str) and isinstance(dark, str) and main and dark:
                    colors[player] = {"main": main, "dark": dark}
            elif isinstance(value, str) and value:
                existing = colors.get(player, FALLBACK_PLAYER_COLOR)
                colors[player] = {"main": value, "dark": existing["dark"]}
        self.player_colors = colors

    def parse_match_players(self, message, fallback=None):
        raw_players = message.get("match_player_ids")
        if raw_players is None:
            raw_players = message.get("players")
        return sorted(self.parse_player_list(raw_players, fallback or self.match_player_ids))

    def board_cell_count(self):
        return self.board_rows * self.board_cols

    def board_geometry(self):
        max_side = max(self.board_rows, self.board_cols)
        if max_side <= 1:
            tile_size = MAX_TILE_SIZE
        else:
            fit_size = (MAX_BOARD_PIXEL_SIZE - (max_side - 1) * TILE_GAP) // max_side
            tile_size = max(MIN_TILE_SIZE, min(MAX_TILE_SIZE, int(fit_size)))
        width = self.board_cols * tile_size + (self.board_cols - 1) * TILE_GAP
        height = self.board_rows * tile_size + (self.board_rows - 1) * TILE_GAP
        return tile_size, width, height, max(24, tile_size - 10)

    def apply_match_settings(self, message):
        try:
            rows = int(message.get("board_rows", self.board_rows) or self.board_rows)
            cols = int(message.get("board_cols", self.board_cols) or self.board_cols)
            target = int(message.get("score_target", self.score_target) or self.score_target)
        except (TypeError, ValueError):
            return
        if MIN_BOARD_SIZE <= rows <= MAX_BOARD_SIZE:
            self.board_rows = rows
        if MIN_BOARD_SIZE <= cols <= MAX_BOARD_SIZE:
            self.board_cols = cols
        if target >= 1:
            self.score_target = target

    def apply_hard_verification_setting(self, message):
        if "hard_verification_enabled" in message:
            self.hard_verification_enabled = bool(message.get("hard_verification_enabled"))

    def apply_swap_mode_setting(self, message):
        if "swap_mode_enabled" in message:
            self.swap_mode_enabled = bool(message.get("swap_mode_enabled"))

    def award_impossible_swap_reward(self, cell, player):
        if (
            self.swap_mode_enabled
            and cell.get("difficulty") == "impossible"
            and not cell.get("swap_reward_given")
            and isinstance(player, int)
            and 1 <= player <= MAX_PLAYERS
        ):
            self.swap_charges[player] = self.swap_charges.get(player, 0) + 1
            self.forced_swap_players.add(player)
            cell["swap_reward_given"] = True
            return True
        return False

    def apply_swap_state_message(self, message):
        raw_charges = message.get("swap_charges", {})
        charges = {player: 0 for player in range(1, MAX_PLAYERS + 1)}
        if isinstance(raw_charges, dict):
            for key, value in raw_charges.items():
                try:
                    player = int(key)
                    charge = int(value)
                except (TypeError, ValueError):
                    continue
                if 1 <= player <= MAX_PLAYERS:
                    charges[player] = max(0, charge)
        self.swap_charges = charges

        raw_forced = message.get("forced_swap_players", [])
        forced = set()
        if isinstance(raw_forced, (list, tuple, set)):
            for value in raw_forced:
                try:
                    player = int(value)
                except (TypeError, ValueError):
                    continue
                if 1 <= player <= MAX_PLAYERS:
                    forced.add(player)
        self.forced_swap_players = forced

    def empty_board(self):
        return [
            [
                self.make_board_cell({"id": "", "text": "", "difficulty": "easy"})
                for _col in range(self.board_cols)
            ]
            for _row in range(self.board_rows)
        ]

    def make_board_cell(self, task, owner=None, status=STATUS_EMPTY, **overrides):
        cell = {
            "task_id": task.get("id", ""),
            "text": task.get("text", ""),
            "difficulty": task.get("difficulty", "easy"),
            "owner": owner,
            "status": status,
            "pending_owner": None,
            "pending_until": None,
            "pending_review": False,
            "swap_reward_given": False,
        }
        cell.update(overrides)
        return self.normalize_board_cell(cell)

    def normalize_board_cell(self, cell):
        normalized = {
            "task_id": cell.get("task_id", cell.get("id", "")),
            "text": cell.get("text", ""),
            "difficulty": cell.get("difficulty", "easy"),
            "owner": cell.get("owner"),
            "status": cell.get("status", STATUS_EMPTY),
            "pending_owner": cell.get("pending_owner"),
            "pending_until": cell.get("pending_until"),
            "pending_review": bool(cell.get("pending_review", False)),
            "swap_reward_given": bool(cell.get("swap_reward_given", False)),
        }
        status = normalized["status"]
        if status == STATUS_PENDING:
            normalized["owner"] = None
        elif status == STATUS_COMPLETE:
            normalized["pending_owner"] = None
            normalized["pending_until"] = None
            normalized["pending_review"] = False
        else:
            normalized["owner"] = None
            normalized["status"] = STATUS_EMPTY
            normalized["pending_owner"] = None
            normalized["pending_until"] = None
            normalized["pending_review"] = False
            normalized["swap_reward_given"] = False
        return normalized

    def board_from_tasks(self):
        cell_count = self.board_cell_count()
        tasks = list(self.task_data.get("tasks", []))[:cell_count]
        while len(tasks) < cell_count:
            tasks.append({"id": "", "text": "", "difficulty": "easy"})
        return [
            [
                self.make_board_cell(tasks[row * self.board_cols + col])
                for col in range(self.board_cols)
            ]
            for row in range(self.board_rows)
        ]

    def empty_task_metadata(self):
        return {
            "task_count": 0,
            "revision_number": 0,
            "last_updated": 0,
            "hash": "",
        }

    def clear_window(self):
        self.cancel_tile_animations()
        self.cancel_timer_update()
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self.board_canvas = None
        self.board_container = None
        self.tiles = []
        self.score_labels = {}
        self.score_bar = None
        self.status_label = None
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None
        self.timer_label = None
        self.countdown_label = None
        try:
            self.root.geometry("")
            self.root.update_idletasks()
        except tk.TclError:
            pass

    def cancel_tile_animations(self):
        self.ui_generation += 1
        for after_id in list(self.animation_after_ids):
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        for row in self.tiles:
            for tile in row:
                overlay_window = tile.get("swap_overlay_window")
                overlay_canvas = tile.get("swap_overlay_canvas")
                try:
                    if self.board_canvas is not None and overlay_window is not None:
                        self.board_canvas.delete(overlay_window)
                except tk.TclError:
                    pass
                try:
                    if overlay_canvas is not None:
                        overlay_canvas.destroy()
                except tk.TclError:
                    pass
                tile["swap_overlay_window"] = None
                tile["swap_overlay_canvas"] = None
                tile["swap_overlay_text"] = None
        self.animation_after_ids.clear()
        self.active_tile_animations.clear()
        self.reroll_animation_keys.clear()

    def make_label(self, parent, text, font=BODY_FONT, fg=TEXT, bg=BG, **kwargs):
        return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kwargs)

    def make_button(self, parent, text, command, width=18, state=tk.NORMAL):
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            state=state,
            font=SUBTITLE_FONT,
            fg=TEXT,
            bg=BUTTON_BG,
            activebackground=BUTTON_ACTIVE,
            activeforeground=TEXT,
            disabledforeground=MUTED_TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            cursor="hand2",
        )

    def tile_font_for_text(self, text):
        text = str(text)
        length = len(text)
        if length <= 16:
            return ("Arial", 10, "bold")
        if length <= 28:
            return ("Arial", 9, "bold")
        if length <= 44:
            return ("Arial", 8, "bold")
        if length <= 60:
            return ("Arial", 7, "bold")
        return ("Arial", 6, "bold")

    def display_tile_text(self, text, max_length=70):
        text = str(text)
        if len(text) <= max_length:
            return text
        return text[: max(0, max_length - 3)].rstrip() + "..."

    def display_player_name(self, player):
        try:
            player_id = int(player)
        except (TypeError, ValueError):
            return ""
        name = getattr(self, "player_names", {}).get(player_id)
        return name or f"P{player_id}"

    def display_difficulty_label(self, cell):
        difficulty = str(cell.get("difficulty", "")).lower()
        if difficulty not in ("easy", "medium", "hard", "impossible"):
            return ""
        if not cell.get("task_id") and not cell.get("text"):
            return ""
        return f"({difficulty})"

    def difficulty_label_color(self, cell):
        difficulty = str(cell.get("difficulty", "")).lower()
        return DIFFICULTY_LABEL_COLORS.get(difficulty, MUTED_TEXT)

    def display_tile_cell(self, cell):
        status = cell.get("status", STATUS_EMPTY)
        difficulty = cell.get("difficulty", "easy")
        is_impossible = difficulty == "impossible"
        text_limit = 44 if is_impossible else 58 if status == STATUS_PENDING else 70
        task_text = self.display_tile_text(cell.get("text", ""), text_limit)

        if is_impossible:
            if status == STATUS_PENDING:
                pending_name = self.display_player_name(cell.get("pending_owner"))
                review = "HOST REVIEW\n" if cell.get("pending_review") else ""
                return f"{review}PENDING {pending_name}\n{task_text}"
            if status == STATUS_COMPLETE:
                owner_name = self.display_player_name(cell.get("owner"))
                reward_text = "\nSwap earned" if cell.get("swap_reward_given") else ""
                return (
                    "COMPLETE\n"
                    f"Owner: {owner_name}\n"
                    f"{task_text}{reward_text}"
                )
            return task_text

        if status == STATUS_PENDING:
            pending_name = self.display_player_name(cell.get("pending_owner"))
            if cell.get("pending_review"):
                return f"HOST REVIEW\nPENDING {pending_name}\n{task_text}"
            return f"PENDING {pending_name}\n{task_text}"

        return task_text

    def tile_style_for_cell(self, cell, row, col):
        owner = cell.get("owner")
        status = cell.get("status", STATUS_EMPTY)
        is_impossible = cell.get("difficulty") == "impossible"

        fill = EMPTY_TILE
        outline = BORDER
        outline_width = 2

        if is_impossible:
            fill = IMPOSSIBLE_TILE
            outline = BORDER
            outline_width = 2
            if status == STATUS_PENDING:
                fill = IMPOSSIBLE_PENDING_TILE
                pending_owner = cell.get("pending_owner")
                if isinstance(pending_owner, int):
                    outline = self.player_color(pending_owner)
            elif status == STATUS_COMPLETE:
                if isinstance(owner, int) and owner in self.active_game_players():
                    fill = self.player_color(owner)
                    outline = self.player_dark(owner)
                else:
                    fill = IMPOSSIBLE_COMPLETE_TILE
            return fill, outline, outline_width

        if status == STATUS_PENDING:
            fill = PENDING_TILE
            pending_owner = cell.get("pending_owner")
            outline = (
                self.player_color(pending_owner)
                if isinstance(pending_owner, int)
                else PENDING_OUTLINE
            )
            outline_width = 3
        elif (
            status == STATUS_COMPLETE
            and isinstance(owner, int)
            and owner in self.active_game_players()
        ):
            fill = self.player_color(owner)
            outline = self.player_dark(owner)
        elif (row, col) in self.local_possible:
            fill = EMPTY_TILE
            outline = self.player_color(self.player)
            outline_width = 4

        return fill, outline, outline_width

    def show_connect_screen(self, error_text=""):
        self.close_connection()
        self.disconnected = False
        self.ready = False
        self.player = None
        self.player_names = self.default_player_names()
        self.lobby_ready_states = {1: True}
        self.connected_players = {1}
        self.active_players = [1]
        self.match_active = False
        self.winner = None
        self.last_announced_winner = None
        self.match_start_time = None
        self.match_end_time = None
        self.board_rows = GRID_SIZE
        self.board_cols = GRID_SIZE
        self.score_target = SCORE_TARGET
        self.local_timer_freeze = None
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None
        self.board_container = None
        self.board_canvas = None
        self.local_possible.clear()
        self.board = self.empty_board()

        self.clear_window()
        self.root.configure(bg=BG)

        outer = tk.Frame(self.root, bg=BG, padx=24, pady=22)
        outer.pack(fill="both", expand=True)

        self.make_label(outer, APP_TITLE, TITLE_FONT).pack(pady=(0, 2))
        self.make_label(
            outer,
            f"Task Knockout {APP_VERSION}",
            SMALL_FONT,
            fg=MUTED_TEXT,
        ).pack(pady=(0, 16))

        self.make_label(outer, "Your name", SUBTITLE_FONT).pack(anchor="w")
        self.name_entry = tk.Entry(
            outer,
            font=BODY_FONT,
            width=30,
            bg=PANEL_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
        )
        self.name_entry.insert(0, self.player_name)
        self.name_entry.pack(fill="x", pady=(4, 14))

        self.make_label(outer, "Host IP", SUBTITLE_FONT).pack(anchor="w")
        self.make_label(
            outer,
            f"Default local IP: {DEFAULT_HOST_IP}",
            SMALL_FONT,
            fg=MUTED_TEXT,
        ).pack(anchor="w", pady=(0, 2))
        self.ip_entry = tk.Entry(
            outer,
            font=BODY_FONT,
            width=30,
            bg=PANEL_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
        )
        self.ip_entry.insert(0, self.load_saved_host_ip() or "127.0.0.1")
        self.ip_entry.pack(fill="x", pady=(4, 14))
        self.ip_entry.bind("<Return>", lambda _event: self.connect_to_host())

        self.make_button(outer, "Connect", self.connect_to_host).pack(fill="x")

        self.setup_error_label = self.make_label(
            outer,
            error_text,
            SMALL_FONT,
            fg=ERROR,
            wraplength=360,
        )
        self.setup_error_label.pack(fill="x", pady=(12, 0))

    def connect_to_host(self):
        name = (self.name_entry.get() if self.name_entry is not None else "").strip()
        host_ip = (self.ip_entry.get() if self.ip_entry is not None else "").strip()
        self.player_name = (name or "Player")[:22]
        self.host_ip = host_ip
        self.save_player_name(self.player_name)

        if not host_ip:
            self.set_setup_error("Enter the host IP.")
            return

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(8)
            conn.connect((host_ip, PORT))
            conn.settimeout(None)
        except OSError as exc:
            self.set_setup_error(f"Could not connect: {exc}")
            return

        self.save_host_ip(host_ip)
        self.conn = conn
        self.disconnected = False
        self.suppress_disconnect_notice = False
        self.ready = False
        self.player = None
        self.connected_players = {1}
        self.lobby_ready_states = {1: True}
        self.match_player_ids = [1]
        self.send_message(
            {
                "type": "join",
                "name": self.player_name,
                "task_metadata": self.empty_task_metadata(),
            }
        )
        self.start_reader_thread()
        self.show_lobby()

    def set_setup_error(self, text):
        if self.setup_error_label is not None:
            self.setup_error_label.config(text=text)

    def show_lobby(self, countdown_text=None):
        self.clear_window()
        self.root.configure(bg=BG)
        self.lobby_rows = {}

        outer = tk.Frame(self.root, bg=BG, padx=24, pady=22)
        outer.pack(fill="both", expand=True)

        self.create_lobby_header(outer)

        self.lobby_you_label = self.make_label(
            outer, "", SUBTITLE_FONT, fg=TEXT, bg=BG
        )
        self.lobby_you_label.pack(anchor="w", pady=(0, 14))

        table = tk.Frame(outer, bg=PANEL_BG, padx=14, pady=12)
        table.pack(fill="x", pady=(0, 14))
        table.grid_columnconfigure(1, weight=1)
        table.grid_columnconfigure(3, minsize=96)

        self.make_label(
            table, "Players", SUBTITLE_FONT, fg=TEXT, bg=PANEL_BG
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.make_label(
            table, "Status", SUBTITLE_FONT, fg=TEXT, bg=PANEL_BG
        ).grid(row=0, column=3, sticky="e", pady=(0, 8))

        for slot in range(1, LOBBY_SLOT_COUNT + 1):
            self.create_player_row(table, slot)

        self.lobby_countdown_label = self.make_label(
            outer,
            "",
            ("Arial", 24, "bold"),
            fg=TEXT,
            bg=BG,
            wraplength=360,
            justify="center",
        )
        self.lobby_countdown_label.pack(fill="x", pady=(0, 12))

        self.ready_button = self.make_button(outer, "", self.toggle_ready)
        self.ready_button.config(font=("Arial", 18, "bold"), pady=14)
        self.ready_button.pack(fill="x", pady=(0, 12))

        self.lobby_status_label = self.make_label(
            outer, "", SMALL_FONT, fg=MUTED_TEXT, bg=BG, wraplength=360
        )
        self.lobby_status_label.pack(fill="x", pady=(0, 12))

        self.leave_lobby_button = self.make_button(
            outer, "Leave Lobby", self.leave_lobby
        )
        self.leave_lobby_button.pack(fill="x")

        self.update_lobby_display(countdown_text)

    def create_lobby_header(self, parent):
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", pady=(0, 10))
        self.make_label(header, "Task Knockout Lobby", TITLE_FONT, bg=BG).pack(
            side="left"
        )
        self.lobby_connection_label = self.make_label(
            header, "", SUBTITLE_FONT, fg=GOOD, bg=BG
        )
        self.lobby_connection_label.pack(side="right")

        self.lobby_host_label = self.make_label(
            parent, "", SMALL_FONT, fg=MUTED_TEXT, bg=BG
        )
        self.lobby_host_label.pack(anchor="w", pady=(0, 12))

    def create_player_row(self, parent, slot):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.grid(row=slot, column=0, columnspan=4, sticky="ew", pady=2)
        row.grid_columnconfigure(1, weight=1)

        square = tk.Label(row, text="", width=2, bg=PANEL_BG)
        square.grid(row=0, column=0, sticky="w", padx=(0, 8))

        name_label = tk.Label(
            row,
            text="",
            font=BODY_FONT,
            fg=TEXT,
            bg=PANEL_BG,
            anchor="w",
        )
        name_label.grid(row=0, column=1, sticky="ew")

        badge_label = tk.Label(
            row,
            text="",
            font=SMALL_FONT,
            fg=MUTED_TEXT,
            bg=PANEL_BG,
            width=10,
            anchor="w",
        )
        badge_label.grid(row=0, column=2, sticky="w", padx=(8, 8))

        status_label = tk.Label(
            row,
            text="",
            font=BODY_FONT,
            fg=MUTED_TEXT,
            bg=PANEL_BG,
            width=10,
            anchor="e",
        )
        status_label.grid(row=0, column=3, sticky="e")

        self.lobby_rows[slot] = {
            "square": square,
            "name": name_label,
            "badge": badge_label,
            "status": status_label,
        }

    def update_lobby_display(self, countdown_text=None):
        connection_text = "Disconnected" if self.disconnected else "Connected"
        if self.lobby_connection_label is not None:
            self.lobby_connection_label.config(
                text=connection_text,
                fg=ERROR if self.disconnected else GOOD,
            )
        if self.lobby_host_label is not None:
            host_text = f"Connected to {self.host_ip}" if self.host_ip else "Connected"
            self.lobby_host_label.config(
                text="Disconnected." if self.disconnected else host_text,
                fg=ERROR if self.disconnected else MUTED_TEXT,
            )
        if self.lobby_you_label is not None:
            if self.player is None:
                self.lobby_you_label.config(text="You are: assigning player...")
            else:
                local_name = self.player_names.get(self.player, self.player_name)
                self.lobby_you_label.config(text=f"You are: {local_name}")

        for slot in range(1, LOBBY_SLOT_COUNT + 1):
            self.update_player_row(slot)

        if self.lobby_countdown_label is not None:
            self.lobby_countdown_label.config(text=countdown_text or "")
        self.update_lobby_status_message()

        if self.ready_button is not None:
            ready_color = self.player_dark(self.player) if self.ready else self.player_color(self.player)
            active_color = self.player_color(self.player) if self.ready else self.player_dark(self.player)
            self.ready_button.config(
                text="NOT READY" if self.ready else "READY",
                bg=ready_color,
                activebackground=active_color,
                state=tk.NORMAL if self.player is not None else tk.DISABLED,
            )

    def update_player_row(self, slot):
        row = self.lobby_rows.get(slot)
        if row is None:
            return

        if slot in self.connected_players:
            color = self.player_color(slot)
            name = self.player_names.get(slot, f"Player {slot}")
            badges = []
            if slot == 1:
                badges.append("HOST")
            if slot == self.player:
                badges.append("YOU")
            ready = bool(self.lobby_ready_states.get(slot, slot == 1))
            status = "Ready" if ready else "Not Ready"
            row["square"].config(text="", bg=color)
            row["name"].config(text=name, fg=TEXT)
            row["badge"].config(text="/".join(badges), fg=GOOD if ready else MUTED_TEXT)
            row["status"].config(text=status, fg=GOOD if ready else MUTED_TEXT)
            return

        row["square"].config(text="", bg=BORDER)
        row["name"].config(text="Waiting for player...", fg=MUTED_TEXT)
        row["badge"].config(text="", fg=MUTED_TEXT)
        row["status"].config(text="Empty", fg=MUTED_TEXT)

    def update_lobby_status_message(self):
        if self.lobby_status_label is None:
            return
        if self.disconnected:
            self.lobby_status_label.config(text="Disconnected.", fg=ERROR)
        elif self.all_real_players_ready():
            self.lobby_status_label.config(
                text="Waiting for host to start the game...", fg=MUTED_TEXT
            )
        else:
            self.lobby_status_label.config(
                text="Waiting for all players to ready up...", fg=MUTED_TEXT
            )

    def all_real_players_ready(self):
        return all(
            self.lobby_ready_states.get(player, player == 1)
            for player in self.connected_players
        )

    def toggle_ready(self):
        if self.player is None:
            return
        self.ready = not self.ready
        self.lobby_ready_states[self.player] = self.ready
        self.update_lobby_display()
        if self.ready_button is not None:
            flash_color = self.player_color(self.player) if self.ready else BUTTON_ACTIVE
            self.ready_button.config(activebackground=flash_color)
        self.send_message(
            {"type": "ready_state", "player": self.player, "ready": self.ready}
        )

    def leave_lobby(self):
        self.suppress_disconnect_notice = True
        if self.player is not None:
            self.send_message({"type": "leave_lobby", "player": self.player})
        self.disconnected = True
        self.ready = False
        self.lobby_ready_states = {1: True}
        self.connected_players = {1}
        self.match_player_ids = [1]
        self.close_connection()
        self.show_connect_screen()

    def start_reader_thread(self):
        threading.Thread(target=self.read_messages, daemon=True).start()

    def read_messages(self):
        try:
            file = self.conn.makefile("r", encoding="utf-8")
            for line in file:
                message = json.loads(line)
                self.root.after(0, lambda msg=message: self.handle_message(msg))
            if not self.disconnected:
                self.root.after(0, self.show_disconnected)
        except (OSError, ValueError, json.JSONDecodeError):
            if not self.disconnected:
                self.root.after(0, self.show_disconnected)

    def handle_message(self, message):
        msg_type = message.get("type")

        if msg_type == "welcome":
            self.apply_match_settings(message)
            self.apply_hard_verification_setting(message)
            self.apply_swap_mode_setting(message)
            self.apply_swap_state_message(message)
            self.apply_player_colors(message.get("player_colors"))
            try:
                self.player = int(message.get("player"))
            except (TypeError, ValueError):
                self.player = None
            if self.player is not None:
                self.player_names[self.player] = self.player_name
            self.match_player_ids = self.parse_match_players(message)
            self.apply_lobby_state(message)

        elif msg_type == "task_sync":
            self.apply_match_settings(message)
            self.apply_hard_verification_setting(message)
            self.apply_swap_mode_setting(message)
            self.apply_swap_state_message(message)
            self.apply_player_colors(message.get("player_colors"))
            incoming = message.get("task_data", {})
            if isinstance(incoming, dict):
                self.task_data = incoming
                if not self.match_active:
                    self.board = self.board_from_tasks()
            self.player_names = self.parse_names(message.get("names", self.player_names))
            self.connected_players = self.parse_player_list(
                message.get("connected_players"), self.connected_players
            )
            self.match_player_ids = self.parse_match_players(message)
            if not self.match_active:
                self.show_lobby()

        elif msg_type == "request_task_pool":
            self.send_message(
                {
                    "type": "task_pool",
                    "task_data": {"revision_number": 0, "last_updated": 0, "tasks": []},
                    "task_metadata": self.empty_task_metadata(),
                }
            )

        elif msg_type == "lobby_state":
            self.apply_lobby_state(message)

        elif msg_type == "ping":
            self.send_message(
                {
                    "type": "pong",
                    "time": message.get("time", time.time()),
                    "player": self.player,
                }
            )

        elif msg_type == "start_countdown":
            self.apply_match_settings(message)
            self.apply_hard_verification_setting(message)
            self.apply_swap_mode_setting(message)
            self.apply_swap_state_message(message)
            self.apply_player_colors(message.get("player_colors"))
            self.player_names = self.parse_names(message.get("names", self.player_names))
            self.connected_players = self.parse_player_list(
                message.get("connected_players"), self.connected_players
            )
            self.match_player_ids = self.parse_match_players(message)
            seconds = message.get("seconds", message.get("countdown"))
            try:
                seconds = int(seconds)
            except (TypeError, ValueError):
                seconds = None
            text = (
                f"Game starting in {seconds}..."
                if seconds in (1, 2, 3)
                else "Game starting soon..."
            )
            if self.lobby_status_label is None:
                self.show_lobby(text)
            else:
                self.update_lobby_display(text)

        elif msg_type == "start_match":
            self.start_match(message)

        elif msg_type == "state":
            self.apply_state_message(message)

        elif msg_type == "return_to_setup":
            self.apply_match_settings(message)
            self.apply_hard_verification_setting(message)
            self.apply_swap_mode_setting(message)
            self.apply_swap_state_message(message)
            self.apply_player_colors(message.get("player_colors"))
            self.player_names = self.parse_names(message.get("names", self.player_names))
            self.connected_players = self.parse_player_list(
                message.get("connected_players"), self.connected_players
            )
            self.match_player_ids = self.parse_match_players(message, {1})
            ready_states = message.get("ready_states") or {}
            if isinstance(ready_states, dict):
                self.lobby_ready_states = {1: True}
                for player in self.connected_players:
                    self.lobby_ready_states[player] = bool(
                        ready_states.get(
                            player, ready_states.get(str(player), player == 1)
                        )
                    )
            self.cancel_timer_update()
            self.ready = False
            if self.player is not None:
                self.lobby_ready_states[self.player] = False
            self.match_active = False
            self.winner = None
            self.last_announced_winner = None
            self.match_start_time = None
            self.match_end_time = None
            self.local_timer_freeze = None
            self.local_possible.clear()
            self.show_lobby()

        elif msg_type in ("error", "disconnect"):
            self.show_disconnected(message.get("message", "Disconnected."))

    def parse_names(self, raw_names):
        names = dict(self.player_names)
        if isinstance(raw_names, dict):
            for key, value in raw_names.items():
                try:
                    names[int(key)] = str(value)
                except (TypeError, ValueError):
                    continue
        if self.player is not None:
            names[self.player] = names.get(self.player, self.player_name)
        return names

    def apply_lobby_state(self, message):
        self.apply_match_settings(message)
        self.apply_hard_verification_setting(message)
        self.apply_swap_mode_setting(message)
        self.apply_swap_state_message(message)
        self.apply_player_colors(message.get("player_colors"))
        self.player_names = self.parse_names(message.get("names", self.player_names))
        self.connected_players = self.parse_player_list(
            message.get("connected_players"), self.connected_players
        )
        self.match_player_ids = self.parse_match_players(message)
        ready_states = message.get("ready") or message.get("ready_states") or {}
        if isinstance(ready_states, dict):
            parsed_ready = {1: True}
            for player in self.connected_players:
                parsed_ready[player] = bool(
                    ready_states.get(player, ready_states.get(str(player), player == 1))
                )
            self.lobby_ready_states = parsed_ready
            if self.player is not None:
                self.ready = bool(self.lobby_ready_states.get(self.player, self.ready))
        elif "ready" in message and isinstance(message.get("ready"), bool):
            self.ready = message["ready"]
            if self.player is not None:
                self.lobby_ready_states[self.player] = self.ready
        elif "p2_ready" in message:
            self.ready = bool(message.get("p2_ready"))
            self.lobby_ready_states[2] = self.ready
        else:
            if self.player is not None:
                self.lobby_ready_states[self.player] = self.ready

        if self.lobby_status_label is None:
            self.show_lobby()
        else:
            self.update_lobby_display()

    def start_match(self, message):
        self.apply_match_settings(message)
        self.apply_hard_verification_setting(message)
        self.apply_swap_mode_setting(message)
        self.apply_swap_state_message(message)
        self.apply_player_colors(message.get("player_colors"))
        self.player = int(message.get("player", 2) or 2)
        self.player_names = self.parse_names(message.get("names", self.player_names))
        self.connected_players = self.parse_player_list(
            message.get("connected_players"), self.connected_players
        )
        self.match_player_ids = self.parse_match_players(message, self.connected_players)
        self.active_players = list(self.match_player_ids)
        self.board = self.normalize_board(message.get("board", self.board))
        self.local_possible.clear()
        self.winner = self.normalize_winner(message.get("winner"))
        self.last_announced_winner = None
        self.last_reroll_animation_id = None
        self.match_active = bool(message.get("match_active", True))
        self.match_start_time = self.parse_time(
            message.get("match_start_time"), fallback=time.time()
        )
        self.match_end_time = self.parse_time(message.get("match_end_time"))
        self.local_timer_freeze = None
        if self.winner is not None or self.match_end_time is not None:
            self.match_active = False
        self.show_game()
        self.update_winner_display(None)

    def normalize_board(self, raw_board):
        board = self.board_from_tasks()
        if not isinstance(raw_board, list):
            return board

        for row in range(min(self.board_rows, len(raw_board))):
            if not isinstance(raw_board[row], list):
                continue
            for col in range(min(self.board_cols, len(raw_board[row]))):
                cell = raw_board[row][col]
                if not isinstance(cell, dict):
                    continue
                merged = dict(board[row][col])
                merged.update(cell)
                board[row][col] = self.normalize_board_cell(merged)
                if board[row][col]["status"] in (STATUS_COMPLETE, STATUS_PENDING):
                    self.local_possible.discard((row, col))
        return board

    def show_game(self):
        self.clear_window()
        self.root.configure(bg=BG)

        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)

        top = tk.Frame(shell, bg=BG, padx=8, pady=8)
        top.pack(fill="x")

        title = (
            f"{APP_TITLE} - You are "
            f"{self.player_names.get(self.player, self.player_name)}"
        )
        self.make_label(top, title, SUBTITLE_FONT, fg=TEXT).pack(side="left")
        self.timer_label = self.make_label(top, "Time: 00:00", SUBTITLE_FONT, fg=TEXT)
        self.timer_label.pack(side="right")

        self.status_label = self.make_label(
            shell,
            "",
            WINNER_FONT,
            fg=MUTED_TEXT,
            bg=BG,
            wraplength=self.board_geometry()[1],
        )
        self.status_label.pack(fill="x", padx=8, pady=(0, 6))

        self.create_winner_banner(shell)
        self.create_board(shell)
        self.create_score_bar(shell)
        self.refresh_grid()
        self.update_scores()
        self.update_winner_display(None)
        self.start_timer_loop()

    def create_winner_banner(self, parent):
        self.winner_banner = tk.Frame(parent, bg=PANEL_BG, padx=18, pady=10)
        self.winner_banner_name = tk.Label(
            self.winner_banner,
            text="",
            font=("Arial", 22, "bold"),
            fg=TEXT,
            bg=PANEL_BG,
            justify="center",
            wraplength=420,
        )
        self.winner_banner_name.pack(fill="x")
        self.winner_banner_result = tk.Label(
            self.winner_banner,
            text="WINS",
            font=("Arial", 16, "bold"),
            fg=TEXT,
            bg=PANEL_BG,
            justify="center",
        )
        self.winner_banner_result.pack(fill="x")
        self.winner_banner.pack(fill="x", padx=8, pady=(0, 8))
        self.winner_banner.pack_forget()

    def create_board(self, parent):
        tile_size, board_width, board_height, text_wrap = self.board_geometry()
        canvas = tk.Canvas(
            parent,
            width=board_width,
            height=board_height,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(padx=8, pady=2)
        canvas.bind("<Button-1>", self.handle_board_click)
        self.board_canvas = canvas
        self.board_container = canvas
        self.tiles = []

        for row in range(self.board_rows):
            tile_row = []
            for col in range(self.board_cols):
                x1 = col * (tile_size + TILE_GAP)
                y1 = row * (tile_size + TILE_GAP)
                x2 = x1 + tile_size
                y2 = y1 + tile_size
                rect = canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=EMPTY_TILE,
                    outline=BORDER,
                    width=2,
                )
                tile_text = self.display_tile_cell(self.board[row][col])
                text = canvas.create_text(
                    x1 + tile_size / 2,
                    y1 + tile_size / 2,
                    text=tile_text,
                    font=self.tile_font_for_text(tile_text),
                    fill=TEXT,
                    justify="center",
                    width=text_wrap,
                )
                tile_row.append({"rect": rect, "text": text})
                difficulty_label = canvas.create_text(
                    x2 - 5,
                    y2 - 4,
                    text=self.display_difficulty_label(self.board[row][col]),
                    font=DIFFICULTY_LABEL_FONT,
                    fill=self.difficulty_label_color(self.board[row][col]),
                    anchor="se",
                )
                tile_row[-1]["difficulty"] = difficulty_label
                tile_row[-1]["swap_overlay"] = None
            self.tiles.append(tile_row)

    def handle_board_click(self, event):
        tile_size, _board_width, _board_height, _text_wrap = self.board_geometry()
        stride = tile_size + TILE_GAP
        if event.x < 0 or event.y < 0:
            return "break"

        col = event.x // stride
        row = event.y // stride
        if row >= self.board_rows or col >= self.board_cols:
            return "break"
        if event.x % stride >= tile_size or event.y % stride >= tile_size:
            return "break"

        mode = STATUS_POSSIBLE if event.state & 0x0001 else STATUS_COMPLETE
        return self.handle_tile_click(row, col, mode)

    def create_score_bar(self, parent):
        self.score_bar = tk.Frame(parent, bg=BG)
        self.score_bar.pack(fill="x", pady=(8, 0))
        self.score_labels = {}

        self.score_bar.grid_rowconfigure(0, weight=1)
        for column, player in enumerate(self.active_game_players()):
            color = self.player_color(player)
            segment = tk.Frame(self.score_bar, bg=color, height=34)
            segment.grid(row=0, column=column, sticky="nsew")
            self.score_bar.grid_columnconfigure(column, weight=1, minsize=90)
            self.score_labels[player] = tk.Label(
                segment,
                text="",
                font=SCORE_FONT,
                fg=TEXT,
                bg=color,
                anchor="center",
            )
            self.score_labels[player].pack(fill="both", expand=True)

    def handle_tile_click(self, row, col, mode):
        if (
            self.player is None
            or self.is_game_over_locally()
        ):
            return "break"

        if self.player in self.forced_swap_players:
            if self.status_label is not None:
                self.status_label.config(
                    text="Pick a tile you would like to swap with another task.",
                    fg=ACCENT,
                )
            self.local_possible.discard((row, col))
            self.send_message(
                {
                    "type": "use_swap",
                    "row": row,
                    "col": col,
                    "player": self.player,
                }
            )
            return "break"

        if mode == STATUS_POSSIBLE:
            self.toggle_local_possible(row, col)
            return "break"

        if self.is_move_allowed(row, col, self.player, mode):
            self.apply_move(row, col, self.player, mode)
            self.refresh_grid()
            self.update_scores()
            self.send_message(
                {
                    "type": "move",
                    "row": row,
                    "col": col,
                    "player": self.player,
                    "status": mode,
                }
            )

        return "break"

    def toggle_local_possible(self, row, col):
        if self.is_game_over_locally():
            return

        if self.player in self.forced_swap_players:
            if self.status_label is not None:
                self.status_label.config(
                    text="Pick a tile you would like to swap with another task.",
                    fg=ACCENT,
                )
            return

        cell = self.board[row][col]
        if cell["status"] in (STATUS_COMPLETE, STATUS_PENDING):
            return
        if cell.get("difficulty") == "impossible":
            return

        key = (row, col)
        if key in self.local_possible:
            self.local_possible.remove(key)
        else:
            self.local_possible.add(key)
        self.refresh_grid()

    def is_move_allowed(self, row, col, player, status):
        if self.is_game_over_locally():
            return False

        if player in self.forced_swap_players:
            return False

        cell = self.board[row][col]
        owner = cell.get("owner")
        current_status = cell.get("status")

        if owner not in (None, player):
            return False
        return status == STATUS_COMPLETE and (
            current_status == STATUS_EMPTY
            or (owner == player and current_status == STATUS_COMPLETE)
        )

    def is_game_over_locally(self):
        scores = self.get_scores()
        return (
            self.winner is not None
            or self.match_end_time is not None
            or not self.match_active
            or any(
                scores.get(player, 0) >= self.score_target
                for player in self.active_game_players()
            )
        )

    def apply_move(self, row, col, player, status):
        cell = self.board[row][col]
        if status == STATUS_COMPLETE and cell.get("owner") == player:
            if cell.get("status") == STATUS_COMPLETE:
                cell["owner"] = None
                cell["status"] = STATUS_EMPTY
                cell["pending_owner"] = None
                cell["pending_until"] = None
                cell["pending_review"] = False
                cell["swap_reward_given"] = False
                return True

        self.local_possible.discard((row, col))
        if (
            status == STATUS_COMPLETE
            and cell.get("status") == STATUS_EMPTY
            and cell.get("difficulty") == "impossible"
            and self.swap_mode_enabled
            and self.hard_verification_enabled
        ):
            cell["owner"] = None
            cell["status"] = STATUS_PENDING
            cell["pending_owner"] = player
            cell["pending_until"] = time.time() + IMPOSSIBLE_PENDING_SECONDS
            cell["pending_review"] = False
            cell["swap_reward_given"] = False
            return True

        if (
            status == STATUS_COMPLETE
            and cell.get("status") == STATUS_EMPTY
            and cell.get("difficulty") == "hard"
            and self.hard_verification_enabled
        ):
            cell["owner"] = None
            cell["status"] = STATUS_PENDING
            cell["pending_owner"] = player
            cell["pending_until"] = time.time() + HARD_PENDING_SECONDS
            cell["pending_review"] = False
            cell["swap_reward_given"] = False
            return True

        cell["owner"] = player
        cell["status"] = status
        cell["pending_owner"] = None
        cell["pending_until"] = None
        cell["pending_review"] = False
        self.award_impossible_swap_reward(cell, player)
        return True

    def animate_tile_reroll(self, row, col, player):
        if (
            self.board_canvas is None
            or not self.tiles
            or not (0 <= row < self.board_rows)
            or not (0 <= col < self.board_cols)
        ):
            return

        key = (row, col)
        generation = self.ui_generation
        canvas = self.board_canvas
        token = self.active_tile_animations.get(key, 0) + 1
        self.active_tile_animations[key] = token
        self.reroll_animation_keys[key] = token
        tile_size, _width, _height, _wrap = self.board_geometry()
        x = col * (tile_size + TILE_GAP)
        y = row * (tile_size + TILE_GAP)
        banner_height = max(18, min(30, tile_size // 3))
        banner_y1 = (tile_size - banner_height) // 2
        banner_y2 = banner_y1 + banner_height
        font_size = max(7, min(12, tile_size // 7))
        banner_fill = self.player_color(player)
        banner_outline = self.player_dark(player)

        def cleanup(refresh=False):
            if self.active_tile_animations.get(key) != token:
                return
            tile = self.tiles[row][col] if row < len(self.tiles) and col < len(self.tiles[row]) else {}
            overlay_window = tile.get("swap_overlay_window")
            overlay_canvas = tile.get("swap_overlay_canvas")
            try:
                if self.board_canvas is canvas and overlay_window is not None:
                    canvas.delete(overlay_window)
            except tk.TclError:
                pass
            try:
                if overlay_canvas is not None:
                    overlay_canvas.destroy()
            except tk.TclError:
                pass
            tile["swap_overlay_window"] = None
            tile["swap_overlay_canvas"] = None
            tile["swap_overlay_text"] = None
            self.active_tile_animations.pop(key, None)
            self.reroll_animation_keys.pop(key, None)
            if refresh and generation == self.ui_generation and self.board_canvas is canvas:
                self.refresh_grid()

        try:
            tile = self.tiles[row][col]
            old_window = tile.get("swap_overlay_window")
            old_canvas = tile.get("swap_overlay_canvas")
            if old_window is not None:
                canvas.delete(old_window)
            if old_canvas is not None:
                old_canvas.destroy()
            overlay = tk.Canvas(
                canvas,
                width=tile_size,
                height=tile_size,
                bg=SWAP_OVERLAY_PURPLE,
                highlightthickness=0,
                bd=0,
            )
            overlay.create_rectangle(
                0,
                0,
                tile_size,
                tile_size,
                fill=SWAP_OVERLAY_PURPLE,
                outline=SWAP_OVERLAY_PURPLE,
                tags=("bg",),
            )
            overlay.create_rectangle(
                0,
                banner_y1,
                tile_size,
                banner_y2,
                fill=banner_fill,
                outline=banner_outline,
                width=1,
                tags=("banner",),
            )
            text_item = overlay.create_text(
                -tile_size,
                tile_size / 2,
                text=SWAP_SCROLL_TEXT * 3,
                font=("Arial", font_size, "bold"),
                fill="#ffffff",
                anchor="w",
                tags=("text",),
            )
            window = canvas.create_window(x, y, anchor="nw", window=overlay)
            canvas.tag_raise(window)
            tile["swap_overlay_window"] = window
            tile["swap_overlay_canvas"] = overlay
            tile["swap_overlay_text"] = text_item
        except tk.TclError:
            cleanup()
            return

        def still_valid():
            if (
                generation != self.ui_generation
                or self.board_canvas is not canvas
                or self.active_tile_animations.get(key) != token
            ):
                return False
            if (
                canvas is None
                or not self.tiles
                or row >= len(self.tiles)
                or col >= len(self.tiles[row])
            ):
                cleanup()
                return False
            try:
                tile = self.tiles[row][col]
                overlay = tile.get("swap_overlay_canvas")
                return bool(canvas.winfo_exists() and overlay is not None and overlay.winfo_exists())
            except tk.TclError:
                cleanup()
                return False

        def scroll_step(step_index=0):
            if not still_valid():
                return
            tile = self.tiles[row][col]
            overlay = tile.get("swap_overlay_canvas")
            text_item = tile.get("swap_overlay_text")
            try:
                progress = (step_index % 24) / 23
                overlay.coords(text_item, -progress * tile_size * 1.65, tile_size / 2)
            except tk.TclError:
                cleanup()
                return
            if step_index < 36:
                schedule(50, lambda idx=step_index + 1: scroll_step(idx))

        def fade_step(index=0):
            if not still_valid():
                return
            tile = self.tiles[row][col]
            overlay = tile.get("swap_overlay_canvas")
            try:
                if index >= len(SWAP_OVERLAY_FADE):
                    cleanup(refresh=True)
                    return
                overlay_color = SWAP_OVERLAY_FADE[index]
                text_color = SWAP_TEXT_FADE[index]
                banner_color = banner_fill if index == 0 else banner_outline
                overlay.config(bg=overlay_color)
                overlay.itemconfig("bg", fill=overlay_color, outline=overlay_color)
                overlay.itemconfig("banner", fill=banner_color, outline=banner_outline)
                overlay.itemconfig("text", fill=text_color)
            except tk.TclError:
                cleanup()
                return
            schedule(180, lambda idx=index + 1: fade_step(idx))

        def schedule(delay, callback):
            try:
                after_id_holder = {}

                def run_step(holder=after_id_holder):
                    after_id = holder.get("id")
                    if after_id in self.animation_after_ids:
                        self.animation_after_ids.remove(after_id)
                    callback()

                after_id = self.root.after(delay, run_step)
                after_id_holder["id"] = after_id
                self.animation_after_ids.append(after_id)
            except tk.TclError:
                cleanup()

        scroll_step()
        schedule(1000, fade_step)

    def refresh_grid(self):
        if self.board_canvas is None or not self.tiles:
            return

        _tile_size, _board_width, _board_height, text_wrap = self.board_geometry()
        for row in range(self.board_rows):
            for col in range(self.board_cols):
                cell = self.board[row][col]
                tile = self.tiles[row][col]
                fill, outline, outline_width = self.tile_style_for_cell(cell, row, col)

                self.board_canvas.itemconfig(
                    tile["rect"],
                    fill=fill,
                    outline=outline,
                    width=outline_width,
                )
                tile_text = self.display_tile_cell(cell)
                self.board_canvas.itemconfig(
                    tile["text"],
                    text=tile_text,
                    font=self.tile_font_for_text(tile_text),
                    width=text_wrap,
                    fill=TEXT,
                )
                self.board_canvas.itemconfig(
                    tile["difficulty"],
                    text=self.display_difficulty_label(cell),
                    fill=self.difficulty_label_color(cell),
                    font=DIFFICULTY_LABEL_FONT,
                )

    def update_scores(self):
        scores = self.get_scores()
        players = self.active_game_players()
        total = sum(scores.get(player, 0) for player in players)
        if self.score_bar is not None:
            for column, player in enumerate(players):
                weight = scores.get(player, 0) if total else 1
                self.score_bar.grid_columnconfigure(column, weight=weight)

        for player in players:
            if player in self.score_labels:
                forced_text = " | Use Swap" if player in self.forced_swap_players else ""
                self.score_labels[player].config(
                    text=f"{self.player_names.get(player, f'Player {player}')}: "
                    f"{scores.get(player, 0)}/{self.score_target}{forced_text}"
                )

    def get_scores(self):
        scores = {player: 0 for player in self.active_game_players()}
        for row in self.board:
            for cell in row:
                if cell.get("status") == STATUS_COMPLETE and cell.get("owner") in scores:
                    scores[cell["owner"]] += 1
        return scores

    def apply_state_message(self, message):
        previous_winner = self.winner
        reroll_hint = self.parse_reroll_animation_hint(message.get("reroll_animation"))
        self.apply_match_settings(message)
        self.apply_hard_verification_setting(message)
        self.apply_swap_mode_setting(message)
        self.apply_swap_state_message(message)
        self.apply_player_colors(message.get("player_colors"))
        self.player_names = self.parse_names(message.get("names", self.player_names))
        self.connected_players = self.parse_player_list(
            message.get("connected_players"), self.connected_players
        )
        self.match_player_ids = self.parse_match_players(message)
        self.active_players = list(self.match_player_ids)
        self.match_start_time = self.parse_time(
            message.get("match_start_time"), fallback=self.match_start_time
        )
        self.match_end_time = self.parse_time(
            message.get("match_end_time"), fallback=self.match_end_time
        )
        self.winner = self.normalize_winner(message.get("winner", self.winner))
        self.match_active = bool(message.get("match_active", self.match_active))

        if "board" in message:
            self.board = self.normalize_board(message["board"])
        else:
            self.apply_tile_state(
                message.get("tile_state", []),
                suppress_reroll_animation=reroll_hint is not None,
            )

        if self.winner is not None or self.match_end_time is not None:
            self.match_active = False
        if (self.winner is not None or self.match_end_time is not None) and self.match_end_time is None:
            if self.local_timer_freeze is None:
                self.local_timer_freeze = time.time()
        elif self.winner is None and self.match_end_time is None:
            self.local_timer_freeze = None

        if self.tiles:
            self.refresh_grid()
            if reroll_hint is not None:
                hint_id, hint_row, hint_col, hint_player = reroll_hint
                self.animate_tile_reroll(hint_row, hint_col, hint_player)
                self.last_reroll_animation_id = hint_id
        self.update_scores()
        self.update_winner_display(previous_winner)
        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass
        self.cancel_timer_update()
        self.update_match_timer()
        if self.winner is not None:
            self.root.after(
                50, lambda previous=previous_winner: self.update_winner_display(previous)
            )
            self.root.after(
                150, lambda previous=previous_winner: self.update_winner_display(previous)
            )

    def parse_reroll_animation_hint(self, hint):
        if not isinstance(hint, dict):
            return None
        try:
            hint_id = int(hint.get("id"))
            row = int(hint.get("row"))
            col = int(hint.get("col"))
            player = int(hint.get("player"))
        except (TypeError, ValueError):
            return None
        if (
            self.last_reroll_animation_id is not None
            and hint_id <= self.last_reroll_animation_id
        ):
            return None
        if not (0 <= row < self.board_rows and 0 <= col < self.board_cols):
            return None
        if not (1 <= player <= MAX_PLAYERS):
            return None
        return hint_id, row, col, player

    def apply_tile_state(self, tile_state, suppress_reroll_animation=False):
        if not isinstance(tile_state, list):
            return
        rerolled_tiles = []
        for row in range(min(self.board_rows, len(tile_state))):
            if not isinstance(tile_state[row], list):
                continue
            for col in range(min(self.board_cols, len(tile_state[row]))):
                state = tile_state[row][col]
                if not isinstance(state, dict):
                    continue
                previous = self.board[row][col]
                old_task_id = previous.get("task_id")
                old_text = previous.get("text")
                cell = dict(self.board[row][col])
                cell.update(state)
                self.board[row][col] = self.normalize_board_cell(cell)
                current = self.board[row][col]
                if (
                    self.match_active
                    and self.tiles
                    and not suppress_reroll_animation
                    and old_task_id
                    and current.get("status") == STATUS_EMPTY
                    and current.get("owner") is None
                    and (
                        current.get("task_id") != old_task_id
                        or current.get("text") != old_text
                    )
                ):
                    rerolled_tiles.append((row, col))
                if self.board[row][col]["status"] in (STATUS_COMPLETE, STATUS_PENDING):
                    self.local_possible.discard((row, col))
        fallback_player = self.player if isinstance(self.player, int) else 1
        for row, col in rerolled_tiles:
            self.animate_tile_reroll(row, col, fallback_player)

    def normalize_winner(self, value):
        try:
            winner = int(value)
        except (TypeError, ValueError):
            return None
        return winner if winner in self.active_game_players() else None

    def update_winner_display(self, previous_winner=None):
        if self.winner is None:
            if self.winner_banner is not None:
                self.winner_banner.pack_forget()
            self.last_announced_winner = None
            if self.status_label is not None:
                if self.player in self.forced_swap_players:
                    self.status_label.config(
                        text="Pick a tile you would like to swap with another task.",
                        fg=ACCENT,
                    )
                    return
                self.status_label.config(
                    text=(
                        "Left click completes. Hard/Impossible tasks lock after "
                        "verification. Shift + left click marks possible."
                        if self.hard_verification_enabled
                        else "Left click completes. Shift + left click marks possible."
                    ),
                    fg=MUTED_TEXT,
                )
            return

        color = self.player_color(self.winner)
        winner_name = self.player_names.get(self.winner, f"Player {self.winner}")

        if self.winner_banner is not None:
            self.winner_banner.config(bg=color)
            if self.winner_banner_name is not None:
                self.winner_banner_name.config(text=winner_name, bg=color, fg=TEXT)
            if self.winner_banner_result is not None:
                self.winner_banner_result.config(text="WINS", bg=color, fg=TEXT)
            if not self.winner_banner.winfo_ismapped():
                try:
                    self.winner_banner.pack(
                        fill="x",
                        padx=8,
                        pady=(0, 8),
                        before=self.board_container,
                    )
                except tk.TclError:
                    self.winner_banner.pack(fill="x", padx=8, pady=(0, 8))
            self.winner_banner.lift()

        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass

        if self.status_label is not None:
            self.status_label.config(text="", fg=color)

        if previous_winner is None and self.last_announced_winner != self.winner:
            self.last_announced_winner = self.winner
            self.bring_window_forward()

    def parse_time(self, value, fallback=None):
        if value is None:
            return fallback
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def start_timer_loop(self):
        self.cancel_timer_update()
        self.update_match_timer()

    def update_match_timer(self):
        if self.timer_label is None:
            return

        start_time = self.match_start_time
        if start_time is None:
            elapsed = 0
        else:
            end_time = self.match_end_time or self.local_timer_freeze
            now = end_time if end_time is not None else time.time()
            elapsed = max(0, int(now - start_time))

        minutes, seconds = divmod(elapsed, 60)
        try:
            self.timer_label.config(text=f"Time: {minutes:02d}:{seconds:02d}")
        except tk.TclError:
            self.timer_label = None
            self.timer_after_id = None
            return

        self.timer_after_id = None
        if (
            self.match_start_time is not None
            and self.match_end_time is None
            and self.local_timer_freeze is None
            and self.winner is None
            and self.match_active
        ):
            self.timer_after_id = self.root.after(250, self.update_match_timer)

    def cancel_timer_update(self):
        if self.timer_after_id is not None:
            try:
                self.root.after_cancel(self.timer_after_id)
            except tk.TclError:
                pass
            self.timer_after_id = None

    def bring_window_forward(self):
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(500, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except tk.TclError:
            pass

    def send_message(self, message):
        if self.conn is None:
            return

        try:
            data = json.dumps(message) + "\n"
            with self.lock:
                self.conn.sendall(data.encode("utf-8"))
        except OSError:
            if not self.disconnected:
                self.root.after(0, self.show_disconnected)

    def show_disconnected(self, message="Disconnected."):
        if self.suppress_disconnect_notice:
            self.suppress_disconnect_notice = False
            return
        if self.disconnected:
            return

        self.disconnected = True
        self.cancel_timer_update()
        self.close_connection()
        self.match_active = False
        self.show_connect_screen(message)

    def close_connection(self):
        if self.conn is None:
            return
        try:
            self.conn.close()
        except OSError:
            pass
        self.conn = None


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskKnockoutClient(root)
    root.mainloop()
