import hashlib
import json
import math
import random
import socket
import threading
import time
import tkinter as tk
import uuid
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
HEARTBEAT_INTERVAL_MS = 2500
HEARTBEAT_TIMEOUT_SECONDS = 8

APP_TITLE = "Task Knockout"
# Public release version.
APP_VERSION = "v1.0.0"
DEFAULT_SHARE_IP = "127.0.0.1"
SCRIPT_DIR = Path(__file__).resolve().parent
TASKS_FILE = SCRIPT_DIR / "tasks.json"
HOST_CONFIG_FILE = SCRIPT_DIR / "taskknockout_host_config.json"
DIFFICULTIES = ("easy", "medium", "hard", "impossible")
BOARD_DIFFICULTIES = ("easy", "medium", "hard")
DIFFICULTY_PRESETS = {
    "easy": {
        "profile": {"easy": 0.65, "medium": 0.20, "hard": 0.15},
        "priority": ("easy", "medium", "hard"),
    },
    "medium": {
        "profile": {"easy": 0.25, "medium": 0.50, "hard": 0.25},
        "priority": ("medium", "easy", "hard"),
    },
    "hard": {
        "profile": {"easy": 0.15, "medium": 0.20, "hard": 0.65},
        "priority": ("hard", "medium", "easy"),
    },
}

DEFAULT_TASKS = [
    ("Use a jetpack", "easy"),
    ("Go on a Date", "easy"),
    ("Go Out of Bounds", "medium"),
    ("Open a Treasure Chest", "easy"),
    ("Get 10,000 of something", "medium"),
    ("Step on a trap", "easy"),
    ("Block something with a shield", "medium"),
    ("Find God", "hard"),
    ("Cut Down A Tree", "easy"),
    ("Escape a Prison Cell", "medium"),
    ("Roll the credits", "hard"),
    ("Open a Door", "easy"),
    ('Get an item starting with the letter "Q"', "hard"),
    ("Get a Companion", "medium"),
    ("Take off your shirt", "easy"),
    ("Get a gold medal", "medium"),
    ("Have a Pekomonja Kill Something", "hard"),
    ("Get honey", "easy"),
    ("Get Killed by a Bee", "medium"),
    ("Make 1,000,000 Dollars", "hard"),
    ("Hit a bush", "easy"),
    ("Speedrun A Mission", "hard"),
    ("Kill a dragon", "hard"),
    ("Use a Flashlight", "easy"),
    ("Find an Egg", "easy"),
]

STATUS_EMPTY = "empty"
STATUS_POSSIBLE = "possible"
STATUS_COMPLETE = "complete"
STATUS_PENDING = "pending"
HARD_PENDING_SECONDS = 10
IMPOSSIBLE_PENDING_SECONDS = 30
PENDING_CHECK_INTERVAL_MS = 500

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


class TaskKnockout:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.task_data = self.load_task_data()
        self.local_possible = set()
        self.tiles = []
        self.score_labels = {}
        self.score_bar = None
        self.status_label = None
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None

        self.is_host = False
        self.player = None
        self.player_names = self.default_player_names()
        self.player_names[1] = self.load_saved_player_name() or "Player"
        self.winner = None
        self.last_announced_winner = None
        self.match_active = False
        self.ready_states = {1: True}
        self.active_players = [1]
        self.match_player_ids = [1]
        self.board_rows = GRID_SIZE
        self.board_cols = GRID_SIZE
        self.score_target = SCORE_TARGET
        self.hard_verification_enabled = False
        self.swap_mode_enabled = False
        self.countdown_active = False
        self.countdown_remaining = None
        self.countdown_after_id = None
        self.countdown_generation = 0
        self.pending_start_counts = None
        self.countdown_label = None
        self.timer_label = None
        self.timer_after_id = None
        self.timer_generation = 0
        self.pending_check_after_id = None
        self.pending_check_generation = 0
        self.match_start_time = None
        self.match_end_time = None
        self.swap_charges = {player: 0 for player in range(1, MAX_PLAYERS + 1)}
        self.forced_swap_players = set()
        self.reroll_animation_counter = 0
        self.last_reroll_animation = None
        self.reroll_animation_keys = {}
        self.ui_generation = 0
        self.animation_after_ids = []
        self.active_tile_animations = {}
        self.current_screen = "menu"
        self.setup_generation = 0
        self.setup_sanity_after_id = None
        self.setup_rebuild_in_progress = False
        self.is_building_setup_screen = False
        self.board = self.empty_board()
        self.board_container = None
        self.board_canvas = None
        self.pending_dialog = None
        self.pending_dialog_tile = None
        self.pending_review_pauses = {}

        self.conn = None
        self.server_socket = None
        self.client_conns = {}
        self.conn_players = {}
        self.last_pong_times = {}
        self.lock = threading.Lock()
        self.disconnected = False
        self.suppress_host_error = False
        self.host_ip_value = ""
        self.last_pong_time = None
        self.heartbeat_after_id = None

        self.name_entry = None
        self.easy_var = None
        self.medium_var = None
        self.hard_var = None
        self.hard_verification_var = None
        self.hard_verification_buttons = {}
        self.swap_mode_var = None
        self.swap_mode_buttons = {}
        self.board_rows_var = None
        self.board_cols_var = None
        self.win_target_var = None
        self.impossible_tiles_var = None
        self.available_space_label = None
        self.amount_needed_label = None
        self.setup_error_label = None
        self.setup_settings_panel = None
        self.start_button = None
        self.reset_button = None
        self.host_connection_label = None
        self.host_ip_label = None
        self.host_you_label = None
        self.host_status_label = None
        self.host_lobby_rows = {}
        self.copy_ip_button = None
        self.copy_default_ip_button = None

        self.editor_listbox = None
        self.editor_text_entry = None
        self.editor_difficulty_var = None
        self.editor_count_label = None
        self.editor_message_label = None
        self.editor_return_screen = "menu"

        self.show_main_menu()

    def default_player_names(self):
        return {player: f"Player {player}" for player in range(1, MAX_PLAYERS + 1)}

    def load_host_config(self):
        try:
            with HOST_CONFIG_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def save_host_config(self, player_name):
        player_name = str(player_name or "").strip()[:22]
        if not player_name:
            return
        try:
            with HOST_CONFIG_FILE.open("w", encoding="utf-8") as file:
                json.dump({"last_player_name": player_name}, file, indent=4)
        except OSError:
            pass

    def load_saved_player_name(self):
        data = self.load_host_config()
        saved_name = str(data.get("last_player_name", "")).strip()
        return saved_name[:22]

    def player_color(self, player):
        return PLAYER_COLORS.get(player, FALLBACK_PLAYER_COLOR)["main"]

    def player_dark(self, player):
        return PLAYER_COLORS.get(player, FALLBACK_PLAYER_COLOR)["dark"]

    def connected_client_ids(self):
        return sorted(self.client_conns)

    def connected_player_ids(self):
        players = [1]
        players.extend(self.connected_client_ids())
        return players

    def has_connected_clients(self):
        return bool(self.client_conns)

    def next_player_slot(self):
        for player in range(2, MAX_PLAYERS + 1):
            if player not in self.client_conns:
                return player
        return None

    def sync_primary_conn(self):
        self.conn = next(iter(self.client_conns.values()), None)

    def lobby_ready_payload(self):
        payload = {1: True}
        for player in self.connected_client_ids():
            payload[player] = bool(self.ready_states.get(player, False))
        return payload

    def active_game_players(self):
        players = list(self.match_player_ids or self.active_players or self.connected_player_ids())
        if 1 not in players:
            players.insert(0, 1)
        return sorted({player for player in players if 1 <= player <= MAX_PLAYERS})

    def board_cell_count(self, rows=None, cols=None):
        rows = self.board_rows if rows is None else rows
        cols = self.board_cols if cols is None else cols
        return rows * cols

    def board_defaults_for_player_count(self, player_count=None):
        player_count = player_count or len(self.connected_player_ids())
        size = max(GRID_SIZE, min(MAX_BOARD_SIZE, player_count + 3))
        return size, size

    def auto_score_target(self, rows=None, cols=None, player_count=None):
        rows = self.board_rows if rows is None else rows
        cols = self.board_cols if cols is None else cols
        player_count = max(1, player_count or len(self.active_game_players()))
        return max(1, math.ceil((rows * cols) / player_count))

    def impossible_task_count(self):
        return self.difficulty_counts().get("impossible", 0)

    def auto_impossible_tile_count(self, rows=None, cols=None):
        if not self.swap_mode_enabled:
            return 0
        cell_count = self.board_cell_count(rows, cols)
        if cell_count < 20:
            count = 0
        elif cell_count <= 35:
            count = 1
        elif cell_count <= 63:
            count = 2
        else:
            count = 3
        return max(0, min(count, cell_count, self.impossible_task_count()))

    def parse_impossible_tile_count(self, rows=None, cols=None):
        if not self.swap_mode_enabled:
            return 0
        rows = self.board_rows if rows is None else rows
        cols = self.board_cols if cols is None else cols
        cell_count = self.board_cell_count(rows, cols)
        raw_value = (
            self.impossible_tiles_var.get()
            if self.impossible_tiles_var is not None
            else "Auto"
        )
        text = str(raw_value or "Auto").strip()
        if text.lower() == "auto":
            return self.auto_impossible_tile_count(rows, cols)

        try:
            count = int(text)
        except (TypeError, ValueError):
            raise ValueError("Impossible Tiles must be a whole number or Auto.")
        if count < 0:
            raise ValueError("Impossible Tiles cannot be negative.")
        if count > cell_count:
            raise ValueError("Impossible Tiles cannot exceed the board space count.")
        available = self.impossible_task_count()
        if count > available:
            raise ValueError(f"You only have {available} impossible tasks.")
        return count

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

    def normalize_player_ids(self, raw_players, fallback=None):
        players = []
        if isinstance(raw_players, (list, tuple, set)):
            source = raw_players
        elif fallback is not None:
            source = fallback
        else:
            source = []

        for value in source:
            try:
                player = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= player <= MAX_PLAYERS and player not in players:
                players.append(player)
        if 1 not in players:
            players.insert(0, 1)
        return sorted(players)

    def player_colors_payload(self):
        return PLAYER_COLORS

    def swap_state_payload(self):
        return {
            "swap_charges": {
                player: int(self.swap_charges.get(player, 0))
                for player in range(1, MAX_PLAYERS + 1)
            },
            "forced_swap_players": sorted(
                player
                for player in self.forced_swap_players
                if 1 <= player <= MAX_PLAYERS
            ),
        }

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

    def make_default_task_data(self):
        tasks = [
            {"id": str(uuid.uuid4()), "text": text, "difficulty": difficulty}
            for text, difficulty in DEFAULT_TASKS
        ]
        return self.make_task_data(tasks, revision=1, timestamp=time.time())

    def make_task_data(self, tasks, revision=None, timestamp=None):
        if revision is None:
            revision = int(self.task_data.get("revision_number", 0)) + 1
        if timestamp is None:
            timestamp = time.time()
        normalized = self.normalize_tasks(tasks)
        data = {
            "revision_number": revision,
            "last_updated": timestamp,
            "tasks": normalized,
        }
        data["metadata"] = self.task_metadata(data)
        return data

    def normalize_tasks(self, tasks):
        normalized = []
        seen_ids = set()
        for task in tasks:
            task_id = str(task.get("id") or uuid.uuid4())
            while task_id in seen_ids:
                task_id = str(uuid.uuid4())
            seen_ids.add(task_id)

            text = str(task.get("text", "")).strip()
            difficulty = str(task.get("difficulty", "easy")).lower()
            if difficulty not in DIFFICULTIES:
                difficulty = "easy"
            if text:
                normalized.append(
                    {"id": task_id, "text": text[:120], "difficulty": difficulty}
                )
        return normalized

    def task_metadata(self, data=None):
        source = data if data is not None else self.task_data
        tasks = source.get("tasks", [])
        hash_source = [
            f"{task.get('id')}|{task.get('text')}|{task.get('difficulty')}"
            for task in sorted(tasks, key=lambda item: item.get("id", ""))
        ]
        digest = hashlib.sha256("\n".join(hash_source).encode("utf-8")).hexdigest()
        return {
            "task_count": len(tasks),
            "revision_number": int(source.get("revision_number", 0)),
            "last_updated": float(source.get("last_updated", 0)),
            "hash": digest,
        }

    def load_task_data(self):
        if TASKS_FILE.exists():
            try:
                with TASKS_FILE.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                normalized = self.make_task_data(
                    data.get("tasks", []),
                    revision=int(data.get("revision_number", 1)),
                    timestamp=float(data.get("last_updated", time.time())),
                )
                self.save_task_data(normalized)
                return normalized
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass

        data = self.make_default_task_data()
        self.save_task_data(data)
        return data

    def save_task_data(self, data=None):
        data = data if data is not None else self.task_data
        with TASKS_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def set_task_data(self, data, save=True):
        self.task_data = self.make_task_data(
            data.get("tasks", []),
            revision=int(data.get("revision_number", 1)),
            timestamp=float(data.get("last_updated", time.time())),
        )
        if save:
            self.save_task_data()

    def update_task_pool(self, tasks):
        self.task_data = self.make_task_data(tasks)
        self.save_task_data()
        self.board = self.empty_board()
        self.local_possible.clear()
        self.winner = None
        self.match_active = False
        if self.has_connected_clients() and not self.match_active:
            self.send_task_sync()

    def compare_task_metadata(self, left, right):
        left_revision = int(left.get("revision_number", 0))
        right_revision = int(right.get("revision_number", 0))
        if left_revision != right_revision:
            return 1 if left_revision > right_revision else -1

        left_time = float(left.get("last_updated", 0))
        right_time = float(right.get("last_updated", 0))
        if left_time != right_time:
            return 1 if left_time > right_time else -1

        left_count = int(left.get("task_count", 0))
        right_count = int(right.get("task_count", 0))
        if left_count != right_count:
            return 1 if left_count > right_count else -1
        return 0

    def difficulty_counts(self):
        counts = {difficulty: 0 for difficulty in DIFFICULTIES}
        for task in self.task_data.get("tasks", []):
            counts[task["difficulty"]] += 1
        return counts

    def default_setup_counts(self, rows=None, cols=None, impossible_count=None):
        cell_count = self.board_cell_count(rows, cols)
        counts = self.difficulty_counts()
        board_counts = {
            difficulty: counts.get(difficulty, 0) for difficulty in BOARD_DIFFICULTIES
        }
        if sum(board_counts.values()) == cell_count:
            return board_counts
        easy = max(0, math.ceil(cell_count * 0.4))
        medium = min(max(0, math.ceil(cell_count * 0.4)), max(0, cell_count - easy))
        hard = cell_count - easy - medium
        return {"easy": easy, "medium": medium, "hard": hard}

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

    def empty_board(self):
        cell_count = self.board_cell_count()
        tasks = self.task_data.get("tasks", [])[:cell_count]
        while len(tasks) < cell_count:
            tasks.append({"id": "", "text": "", "difficulty": "easy"})
        return [
            [
                self.make_board_cell(tasks[row * self.board_cols + col])
                for col in range(self.board_cols)
            ]
            for row in range(self.board_rows)
        ]

    def generate_board(self, requested_counts):
        cell_count = self.board_cell_count()
        chosen_tasks = []
        normal_total = sum(
            requested_counts.get(difficulty, 0) for difficulty in BOARD_DIFFICULTIES
        )
        if normal_total != cell_count:
            raise ValueError(f"Difficulty counts must add up to {cell_count}.")
        effective_counts = {
            difficulty: requested_counts.get(difficulty, 0)
            for difficulty in BOARD_DIFFICULTIES
        }
        impossible_count = (
            requested_counts.get("impossible", 0)
            if self.swap_mode_enabled
            else 0
        )
        replacements = impossible_count
        for difficulty in ("hard", "medium", "easy"):
            take = min(effective_counts[difficulty], replacements)
            effective_counts[difficulty] -= take
            replacements -= take
        if replacements > 0:
            raise ValueError("Impossible Tiles cannot replace more tasks than selected.")
        effective_counts["impossible"] = impossible_count

        for difficulty in DIFFICULTIES:
            pool = [
                task
                for task in self.task_data.get("tasks", [])
                if task["difficulty"] == difficulty
            ]
            needed = effective_counts.get(difficulty, 0)
            if len(pool) < needed:
                raise ValueError(
                    f"Not enough {difficulty} tasks. Need {needed}, have {len(pool)}."
                )
            if needed:
                chosen_tasks.extend(random.sample(pool, needed))

        random.shuffle(chosen_tasks)
        if len(chosen_tasks) != cell_count:
            raise ValueError(f"Generated board must contain exactly {cell_count} tasks.")
        return [
            [
                self.make_board_cell(chosen_tasks[row * self.board_cols + col])
                for col in range(self.board_cols)
            ]
            for row in range(self.board_rows)
        ]

    def clear_window(self):
        self.cancel_setup_sanity_check()
        self.cancel_tile_animations()
        self.cancel_timer_update()
        self.close_pending_dialog(resume=False)
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
        self.reset_button = None
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None
        self.timer_label = None
        self.countdown_label = None
        self.setup_settings_panel = None
        self.available_space_label = None
        self.amount_needed_label = None
        self.setup_error_label = None
        self.start_button = None
        self.host_connection_label = None
        self.host_ip_label = None
        self.host_you_label = None
        self.host_status_label = None
        self.copy_ip_button = None
        self.copy_default_ip_button = None
        self.host_lobby_rows = {}
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

    def cancel_setup_sanity_check(self):
        self.setup_generation += 1
        self.setup_rebuild_in_progress = False
        if self.setup_sanity_after_id is not None:
            try:
                self.root.after_cancel(self.setup_sanity_after_id)
            except tk.TclError:
                pass
            self.setup_sanity_after_id = None

    def widget_alive(self, widget):
        try:
            return widget is not None and widget.winfo_exists()
        except tk.TclError:
            return False

    def reset_connection_state(self):
        self.cancel_countdown()
        self.stop_heartbeat()
        self.cancel_pending_check()
        self.disconnected = False
        self.player = None
        self.is_host = False
        self.winner = None
        self.last_announced_winner = None
        self.match_active = False
        self.ready_states = {1: True}
        self.active_players = [1]
        self.match_player_ids = [1]
        self.board_rows = GRID_SIZE
        self.board_cols = GRID_SIZE
        self.score_target = SCORE_TARGET
        self.hard_verification_enabled = False
        self.swap_mode_enabled = False
        self.match_start_time = None
        self.match_end_time = None
        self.timer_label = None
        self.local_possible.clear()
        self.pending_review_pauses.clear()
        self.swap_charges = {player: 0 for player in range(1, MAX_PLAYERS + 1)}
        self.forced_swap_players = set()
        self.reroll_animation_counter = 0
        self.last_reroll_animation = None
        self.player_names = self.default_player_names()
        self.player_names[1] = self.load_saved_player_name() or "Player"
        self.close_sockets()

    def close_client_socket(self, player=None):
        if player is None:
            player = self.conn_players.get(self.conn)
        conn = self.client_conns.pop(player, None) if player is not None else self.conn
        if conn is None:
            return
        try:
            conn.close()
        except OSError:
            pass
        self.conn_players.pop(conn, None)
        if player is not None:
            self.ready_states.pop(player, None)
            self.last_pong_times.pop(player, None)
        self.sync_primary_conn()

    def close_sockets(self):
        self.stop_heartbeat()
        self.cancel_pending_check()
        self.pending_review_pauses.clear()
        sockets = list(self.client_conns.values())
        sockets.extend([self.conn, self.server_socket])
        for sock in sockets:
            if sock is None:
                continue
            try:
                sock.close()
            except OSError:
                pass
        self.client_conns = {}
        self.conn_players = {}
        self.last_pong_times = {}
        self.conn = None
        self.server_socket = None

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
        if difficulty not in DIFFICULTIES:
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

    def show_main_menu(self):
        self.current_screen = "menu"
        self.reset_connection_state()
        self.board = self.empty_board()
        self.local_possible.clear()
        self.tiles = []
        self.score_labels = {}
        self.score_bar = None
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None
        self.board_container = None
        self.board_canvas = None
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
        ).pack(pady=(0, 6))
        self.make_label(
            outer,
            "Build a task pool, sync it, then race to 13.",
            SUBTITLE_FONT,
            fg=MUTED_TEXT,
        ).pack(pady=(0, 18))

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
        self.name_entry.insert(0, self.load_saved_player_name() or "Player")
        self.name_entry.pack(fill="x", pady=(4, 14))

        self.make_button(outer, "Manage Tasks", self.show_task_editor).pack(
            fill="x", pady=(0, 10)
        )
        self.make_button(outer, "Host Game", self.host_game).pack(fill="x", pady=(0, 16))
        self.make_label(
            outer,
            self.format_task_meta_line(),
            SMALL_FONT,
            fg=MUTED_TEXT,
        ).pack(pady=(16, 0))
        self.make_label(
            outer,
            f"Task file: {TASKS_FILE.resolve()}",
            SMALL_FONT,
            fg=MUTED_TEXT,
            wraplength=360,
            justify="center",
        ).pack(pady=(6, 0))

    def format_task_meta_line(self):
        meta = self.task_metadata()
        counts = self.difficulty_counts()
        count_text = " ".join(
            f"{difficulty.title()} {counts.get(difficulty, 0)}"
            for difficulty in DIFFICULTIES
        )
        return (
            f"Tasks {meta['task_count']} | Rev {meta['revision_number']} | "
            f"{count_text}"
        )

    def get_entered_name(self, fallback):
        if self.name_entry is None:
            return fallback
        name = self.name_entry.get().strip()
        return name[:22] if name else fallback

    def get_local_ip(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except OSError:
            return socket.gethostbyname(socket.gethostname())

    def show_task_editor(self, return_screen="menu"):
        if self.match_active:
            return

        self.current_screen = "task_editor"
        self.editor_return_screen = return_screen
        self.clear_window()
        self.root.configure(bg=BG)

        outer = tk.Frame(self.root, bg=BG, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x", pady=(0, 10))
        self.make_label(top, "Task Pool", TITLE_FONT).pack(side="left")
        self.make_button(top, "Back", self.return_from_editor, width=9).pack(side="right")

        self.editor_count_label = self.make_label(
            outer, self.format_task_meta_line(), SMALL_FONT, fg=MUTED_TEXT
        )
        self.editor_count_label.pack(anchor="w", pady=(0, 8))

        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        scrollbar = tk.Scrollbar(left)
        scrollbar.pack(side="right", fill="y")
        self.editor_listbox = tk.Listbox(
            left,
            height=16,
            width=44,
            font=SMALL_FONT,
            bg=PANEL_BG,
            fg=TEXT,
            selectbackground=P1_DARK,
            selectforeground=TEXT,
            yscrollcommand=scrollbar.set,
            relief="solid",
            bd=1,
        )
        self.editor_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.editor_listbox.yview)
        self.editor_listbox.bind("<<ListboxSelect>>", self.load_selected_task)

        right = tk.Frame(body, bg=BG)
        right.pack(side="right", fill="y")

        self.make_label(right, "Task text", SUBTITLE_FONT).pack(anchor="w")
        self.editor_text_entry = tk.Entry(
            right,
            width=32,
            font=BODY_FONT,
            bg=PANEL_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
        )
        self.editor_text_entry.pack(fill="x", pady=(4, 12))

        self.make_label(right, "Difficulty", SUBTITLE_FONT).pack(anchor="w")
        self.editor_difficulty_var = tk.StringVar(value="easy")
        difficulty_menu = tk.OptionMenu(
            right, self.editor_difficulty_var, *DIFFICULTIES
        )
        difficulty_menu.config(
            font=BODY_FONT,
            fg=TEXT,
            bg=BUTTON_BG,
            activebackground=BUTTON_ACTIVE,
            activeforeground=TEXT,
            relief="flat",
            width=18,
        )
        difficulty_menu["menu"].config(bg=PANEL_BG, fg=TEXT)
        difficulty_menu.pack(fill="x", pady=(4, 14))

        self.make_button(right, "Add Task", self.add_task).pack(fill="x", pady=(0, 8))
        self.make_button(right, "Save Selected", self.edit_selected_task).pack(
            fill="x", pady=(0, 8)
        )
        self.make_button(right, "Remove Selected", self.remove_selected_task).pack(
            fill="x"
        )

        self.editor_message_label = self.make_label(
            outer, "", SMALL_FONT, fg=MUTED_TEXT, wraplength=520
        )
        self.editor_message_label.pack(fill="x", pady=(10, 0))

        self.refresh_task_editor()

    def return_from_editor(self):
        if self.editor_return_screen == "setup" and self.is_host:
            if self.has_connected_clients():
                self.show_setup_screen()
            else:
                self.show_host_waiting_lobby()
        elif self.editor_return_screen == "host_lobby" and self.is_host:
            self.show_host_waiting_lobby()
        elif self.editor_return_screen == "lobby" and self.conn:
            self.show_waiting_lobby()
        else:
            self.show_main_menu()

    def refresh_task_editor(self):
        if self.editor_listbox is None:
            return
        self.editor_listbox.delete(0, tk.END)
        for task in sorted(
            self.task_data.get("tasks", []), key=lambda item: (item["difficulty"], item["text"].lower())
        ):
            self.editor_listbox.insert(
                tk.END, f"[{task['difficulty']}] {task['text']}  <{task['id'][:8]}>"
            )
        if self.editor_count_label is not None:
            self.editor_count_label.config(text=self.format_task_meta_line())

    def selected_task_index(self):
        if self.editor_listbox is None:
            return None
        selection = self.editor_listbox.curselection()
        if not selection:
            return None
        display = self.editor_listbox.get(selection[0])
        marker = display.rsplit("<", 1)[-1].rstrip(">")
        for index, task in enumerate(self.task_data.get("tasks", [])):
            if task["id"].startswith(marker):
                return index
        return None

    def load_selected_task(self, _event=None):
        index = self.selected_task_index()
        if index is None:
            return
        task = self.task_data["tasks"][index]
        self.editor_text_entry.delete(0, tk.END)
        self.editor_text_entry.insert(0, task["text"])
        self.editor_difficulty_var.set(task["difficulty"])

    def get_editor_task_values(self):
        text = self.editor_text_entry.get().strip()
        difficulty = self.editor_difficulty_var.get()
        if difficulty not in DIFFICULTIES:
            difficulty = "easy"
        return text, difficulty

    def show_editor_message(self, text, color=MUTED_TEXT):
        if self.editor_message_label is not None:
            self.editor_message_label.config(text=text, fg=color)

    def add_task(self):
        text, difficulty = self.get_editor_task_values()
        if not text:
            self.show_editor_message("Enter task text before adding.", ERROR)
            return
        tasks = self.task_data["tasks"][:]
        tasks.append({"id": str(uuid.uuid4()), "text": text, "difficulty": difficulty})
        self.update_task_pool(tasks)
        self.editor_text_entry.delete(0, tk.END)
        self.refresh_task_editor()
        self.show_editor_message("Task added and saved.", GOOD)

    def edit_selected_task(self):
        index = self.selected_task_index()
        if index is None:
            self.show_editor_message("Select a task to edit.", ERROR)
            return
        text, difficulty = self.get_editor_task_values()
        if not text:
            self.show_editor_message("Task text cannot be empty.", ERROR)
            return
        tasks = self.task_data["tasks"][:]
        tasks[index] = {
            "id": tasks[index]["id"],
            "text": text,
            "difficulty": difficulty,
        }
        self.update_task_pool(tasks)
        self.refresh_task_editor()
        self.show_editor_message("Task updated and saved.", GOOD)

    def remove_selected_task(self):
        index = self.selected_task_index()
        if index is None:
            self.show_editor_message("Select a task to remove.", ERROR)
            return
        tasks = self.task_data["tasks"][:]
        removed = tasks.pop(index)
        self.update_task_pool(tasks)
        self.editor_text_entry.delete(0, tk.END)
        self.refresh_task_editor()
        self.show_editor_message(f"Removed: {removed['text']}", GOOD)

    def host_game(self):
        self.is_host = True
        self.player = 1
        self.winner = None
        self.match_active = False
        self.player_names = self.default_player_names()
        self.player_names[1] = self.get_entered_name("Player 1")
        self.save_host_config(self.player_names[1])
        self.ready_states = {1: True}
        self.active_players = [1]
        self.match_player_ids = [1]
        self.hard_verification_enabled = False
        self.client_conns = {}
        self.conn_players = {}
        self.last_pong_times = {}
        self.conn = None
        self.disconnected = False
        self.suppress_host_error = False

        local_ip = self.get_local_ip()
        self.host_ip_value = local_ip

        self.show_host_waiting_lobby()

        threading.Thread(target=self.host_thread, daemon=True).start()

    def show_host_waiting_lobby(self):
        self.current_screen = "host_waiting"
        self.clear_window()
        self.root.configure(bg=BG)
        self.host_lobby_rows = {}

        outer = tk.Frame(self.root, bg=BG, padx=20, pady=12)
        outer.pack(fill="both", expand=True)

        self.create_host_lobby_header(outer)
        self.create_host_identity_line(outer)

        middle = tk.Frame(outer, bg=BG)
        middle.pack(fill="x", pady=(0, 10))
        middle.grid_columnconfigure(0, weight=3, minsize=300)
        middle.grid_columnconfigure(1, weight=2, minsize=190)

        players = self.create_host_player_table(middle, pack_table=False)
        players.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        host_controls = tk.Frame(middle, bg=PANEL_BG, padx=12, pady=10)
        host_controls.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.make_label(
            host_controls, "Host Controls", SUBTITLE_FONT, fg=TEXT, bg=PANEL_BG
        ).pack(anchor="w", pady=(0, 8))
        self.make_label(
            host_controls,
            self.format_task_meta_line(),
            SMALL_FONT,
            fg=MUTED_TEXT,
            bg=PANEL_BG,
            wraplength=190,
            justify="left",
        ).pack(fill="x", pady=(0, 12))
        self.make_button(
            host_controls,
            "Manage Tasks",
            lambda: self.show_task_editor("host_lobby"),
            width=14,
        ).pack(fill="x", pady=(0, 8))
        self.make_button(
            host_controls, "Cancel Hosting", self.cancel_hosting, width=14
        ).pack(fill="x")

        self.host_status_label = self.make_label(
            outer, "", SMALL_FONT, fg=MUTED_TEXT, bg=BG, wraplength=480
        )
        self.host_status_label.pack(fill="x")
        self.refresh_host_lobby_display()

    def host_thread(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", PORT))
            self.server_socket.listen(MAX_PLAYERS - 1)
            self.server_socket.settimeout(1)

            while self.is_host and not self.disconnected:
                try:
                    conn, _addr = self.server_socket.accept()
                except socket.timeout:
                    continue

                if (
                    self.countdown_active
                    or self.match_active
                    or self.match_start_time is not None
                ):
                    try:
                        conn.sendall(
                            (
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": "Match already in progress.",
                                    }
                                )
                                + "\n"
                            ).encode("utf-8")
                        )
                        conn.close()
                    except OSError:
                        pass
                    continue

                player = self.next_player_slot()
                if player is None:
                    try:
                        conn.sendall(
                            (json.dumps({"type": "error", "message": "Lobby is full."}) + "\n").encode("utf-8")
                        )
                        conn.close()
                    except OSError:
                        pass
                    continue

                self.client_conns[player] = conn
                self.conn_players[conn] = player
                self.ready_states[player] = False
                self.last_pong_times[player] = time.time()
                self.player_names[player] = f"Player {player}"
                self.sync_primary_conn()
                self.start_reader_thread(conn, player)
                self.root.after(0, self.safe_refresh_host_lobby_display)
                self.root.after(0, self.start_heartbeat)
        except OSError as exc:
            if not self.disconnected and not self.suppress_host_error:
                self.root.after(0, lambda: self.show_error(f"Host error: {exc}"))
            self.suppress_host_error = False

    def cancel_hosting(self):
        self.suppress_host_error = True
        self.disconnected = True
        self.stop_heartbeat()
        self.close_sockets()
        self.show_main_menu()

    def start_heartbeat(self):
        self.stop_heartbeat()
        if not self.is_host or self.disconnected or not self.has_connected_clients():
            return
        now = time.time()
        for player in self.connected_client_ids():
            self.last_pong_times.setdefault(player, now)
        self.heartbeat_after_id = self.root.after(
            HEARTBEAT_INTERVAL_MS, self.heartbeat_tick
        )

    def stop_heartbeat(self):
        if self.heartbeat_after_id is not None:
            try:
                self.root.after_cancel(self.heartbeat_after_id)
            except tk.TclError:
                pass
            self.heartbeat_after_id = None

    def heartbeat_tick(self):
        self.heartbeat_after_id = None
        if not self.is_host or self.disconnected or not self.has_connected_clients():
            return

        now = time.time()
        for player in self.connected_client_ids():
            last_pong = self.last_pong_times.get(player, now)
            if now - last_pong > HEARTBEAT_TIMEOUT_SECONDS:
                self.mark_player_disconnected(
                    player, f"Player {player} connection timed out."
                )
                continue
            self.send_to_player(player, {"type": "ping", "time": now})

        if self.has_connected_clients():
            self.heartbeat_after_id = self.root.after(
                HEARTBEAT_INTERVAL_MS, self.heartbeat_tick
            )

    def mark_player_disconnected(self, player, reason=None):
        if not self.is_host:
            self.show_disconnected()
            return

        if player not in self.client_conns:
            return

        self.cancel_countdown()
        self.close_client_socket(player)
        reset_pending = self.reset_pending_tiles_for_player(player)
        self.forced_swap_players.discard(player)
        self.swap_charges[player] = 0
        self.player_names[player] = f"Player {player}"

        if self.match_start_time is None:
            self.match_start_time = None
            self.match_end_time = None
            if self.setup_error_label is not None and reason:
                try:
                    self.setup_error_label.config(text=reason)
                except tk.TclError:
                    self.setup_error_label = None
            try:
                self.refresh_host_lobby_display()
            except tk.TclError:
                pass
            self.send_lobby_state()
            if self.has_connected_clients():
                self.start_heartbeat()
            else:
                self.stop_heartbeat()
            return

        if self.status_label is not None:
            self.status_label.config(text=reason, fg=ERROR)
        if reset_pending:
            self.refresh_grid()
            self.update_scores()
        if self.has_connected_clients():
            self.start_heartbeat()
        else:
            self.stop_heartbeat()
        self.broadcast_state()

    def can_start_match(self, status_message=True):
        connected_clients = self.connected_client_ids()
        if not connected_clients:
            if status_message:
                self.show_setup_error("At least one client must connect before starting.")
            return False
        not_ready = [
            player
            for player in connected_clients
            if not self.ready_states.get(player, False)
        ]
        if not_ready:
            if status_message:
                names = ", ".join(
                    self.player_names.get(player, f"Player {player}")
                    for player in not_ready
                )
                self.show_setup_error(f"Waiting for {names} to ready up.")
            return False
        return True

    def show_setup_error(self, text):
        if self.setup_error_label is not None:
            try:
                self.setup_error_label.config(text=text)
            except tk.TclError:
                self.setup_error_label = None
        try:
            self.refresh_host_lobby_display()
        except tk.TclError:
            pass
        self.update_start_button_state()

    def show_waiting_lobby(self):
        self.clear_window()
        outer = tk.Frame(self.root, bg=BG, padx=24, pady=22)
        outer.pack(fill="both", expand=True)
        self.make_label(outer, "Connected", TITLE_FONT).pack(pady=(0, 12))
        self.make_label(
            outer,
            "Waiting for the host to choose difficulties and start.",
            BODY_FONT,
            fg=MUTED_TEXT,
            wraplength=360,
        ).pack(pady=(0, 16))
        self.make_label(outer, self.format_task_meta_line(), SMALL_FONT, fg=MUTED_TEXT).pack()

    def create_host_lobby_header(self, parent):
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", pady=(0, 8))
        self.make_label(header, "Task Knockout Lobby", TITLE_FONT, bg=BG).pack(
            side="left"
        )
        self.host_connection_label = self.make_label(
            header, "", SUBTITLE_FONT, fg=GOOD, bg=BG
        )
        self.host_connection_label.pack(side="right")

        ip_row = tk.Frame(parent, bg=BG)
        ip_row.pack(fill="x", pady=(0, 8))
        self.host_ip_label = self.make_label(
            ip_row, "", SMALL_FONT, fg=MUTED_TEXT, bg=BG
        )
        self.host_ip_label.pack(side="left")
        self.copy_ip_button = self.make_button(
            ip_row, "Copy IP", self.copy_host_ip, width=18
        )
        self.copy_ip_button.pack(side="right")

        share_ip_row = tk.Frame(parent, bg=BG)
        share_ip_row.pack(fill="x", pady=(0, 8))
        self.make_label(
            share_ip_row,
            f"For online play, share the IP address from your LAN/VPN tool if you use one. Default local IP: {DEFAULT_SHARE_IP}",
            SMALL_FONT,
            fg=MUTED_TEXT,
            bg=BG,
            wraplength=300,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
        self.copy_default_ip_button = self.make_button(
            share_ip_row, "Copy Default IP", self.copy_default_ip, width=18
        )
        self.copy_default_ip_button.pack(side="right")

    def create_host_identity_line(self, parent):
        self.host_you_label = self.make_label(
            parent, "", SUBTITLE_FONT, fg=TEXT, bg=BG
        )
        self.host_you_label.pack(anchor="w", pady=(0, 10))

    def create_host_player_table(self, parent, pack_table=True):
        table = tk.Frame(parent, bg=PANEL_BG, padx=12, pady=10)
        if pack_table:
            table.pack(fill="x", pady=(0, 12))
        table.grid_columnconfigure(1, weight=1)
        table.grid_columnconfigure(3, minsize=82)

        self.make_label(
            table, "Players", SUBTITLE_FONT, fg=TEXT, bg=PANEL_BG
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.make_label(
            table, "Status", SUBTITLE_FONT, fg=TEXT, bg=PANEL_BG
        ).grid(row=0, column=3, sticky="e", pady=(0, 8))

        for slot in range(1, LOBBY_SLOT_COUNT + 1):
            self.create_host_player_row(table, slot)
        return table

    def create_host_player_row(self, parent, slot):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.grid(row=slot, column=0, columnspan=4, sticky="ew", pady=1)
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
            width=9,
            anchor="w",
        )
        badge_label.grid(row=0, column=2, sticky="w", padx=(8, 8))

        status_label = tk.Label(
            row,
            text="",
            font=BODY_FONT,
            fg=MUTED_TEXT,
            bg=PANEL_BG,
            width=9,
            anchor="e",
        )
        status_label.grid(row=0, column=3, sticky="e")

        self.host_lobby_rows[slot] = {
            "square": square,
            "name": name_label,
            "badge": badge_label,
            "status": status_label,
        }

    def refresh_host_lobby_display(self):
        if self.widget_alive(self.host_connection_label):
            if self.disconnected:
                self.host_connection_label.config(text="Disconnected", fg=ERROR)
            elif self.has_connected_clients():
                self.host_connection_label.config(text="Connected", fg=GOOD)
            else:
                self.host_connection_label.config(text="Hosting", fg=GOOD)

        if self.widget_alive(self.host_ip_label):
            ip_text = self.host_ip_value or self.get_local_ip()
            self.host_ip_label.config(text=f"Hosting on {ip_text}:{PORT}")

        if self.widget_alive(self.host_you_label):
            self.host_you_label.config(
                text=f"You are: {self.player_names.get(1, 'Player 1')}"
            )

        for slot in range(1, LOBBY_SLOT_COUNT + 1):
            self.refresh_host_player_row(slot)

        if self.widget_alive(self.host_status_label):
            self.host_status_label.config(
                text=self.host_lobby_status_text(),
                fg=ERROR if self.disconnected else MUTED_TEXT,
            )
        self.update_start_button_state()

    def safe_refresh_host_lobby_display(self):
        try:
            self.refresh_host_lobby_display()
        except tk.TclError:
            pass

    def refresh_host_player_row(self, slot):
        row = self.host_lobby_rows.get(slot)
        if row is None:
            return
        if any(not self.widget_alive(widget) for widget in row.values()):
            self.host_lobby_rows.pop(slot, None)
            return

        try:
            if slot == 1:
                row["square"].config(text="", bg=self.player_color(1))
                row["name"].config(
                    text=self.player_names.get(1, "Player 1"), fg=TEXT
                )
                row["badge"].config(text="HOST/YOU", fg=GOOD)
                row["status"].config(text="Ready", fg=GOOD)
                return

            if slot in self.client_conns:
                ready = bool(self.ready_states.get(slot, False))
                row["square"].config(text="", bg=self.player_color(slot))
                row["name"].config(
                    text=self.player_names.get(slot, f"Player {slot}"), fg=TEXT
                )
                row["badge"].config(text="", fg=MUTED_TEXT)
                row["status"].config(
                    text="Ready" if ready else "Not Ready",
                    fg=GOOD if ready else MUTED_TEXT,
                )
                return

            row["square"].config(text="", bg=BORDER)
            row["name"].config(text="Waiting for player...", fg=MUTED_TEXT)
            row["badge"].config(text="", fg=MUTED_TEXT)
            row["status"].config(text="Empty", fg=MUTED_TEXT)
        except tk.TclError:
            self.host_lobby_rows.pop(slot, None)

    def host_lobby_status_text(self):
        if self.disconnected:
            return "Disconnected."
        if not self.has_connected_clients():
            return "Waiting for players to connect..."
        if not all(
            self.ready_states.get(player, False)
            for player in self.connected_client_ids()
        ):
            return "Waiting for all players to ready up..."
        return "Ready to start. Choose task counts, then start the match."

    def copy_host_ip(self):
        ip_text = self.host_ip_value or self.get_local_ip()
        self.root.clipboard_clear()
        self.root.clipboard_append(ip_text)
        self.root.update()
        if self.copy_ip_button is not None:
            self.copy_ip_button.config(text=f"Copied {ip_text}")
            self.root.after(
                1400,
                lambda: self.copy_ip_button is not None
                and self.copy_ip_button.config(text="Copy IP"),
            )

    def copy_default_ip(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(DEFAULT_SHARE_IP)
        self.root.update()
        if self.copy_default_ip_button is not None:
            self.copy_default_ip_button.config(text=f"Copied {DEFAULT_SHARE_IP}")
            self.root.after(
                1400,
                lambda: self.copy_default_ip_button is not None
                and self.copy_default_ip_button.config(text="Copy Default IP"),
            )

    def get_current_setup_field_values(self):
        fields = (
            "board_rows",
            "board_cols",
            "win_target",
            "impossible_tiles",
            "easy",
            "medium",
            "hard",
            "hard_verification",
            "swap_mode",
        )
        vars_by_field = {
            "board_rows": self.board_rows_var,
            "board_cols": self.board_cols_var,
            "win_target": self.win_target_var,
            "impossible_tiles": self.impossible_tiles_var,
            "easy": self.easy_var,
            "medium": self.medium_var,
            "hard": self.hard_var,
            "hard_verification": self.hard_verification_var,
            "swap_mode": self.swap_mode_var,
        }
        values = {}
        for field in fields:
            var = vars_by_field.get(field)
            if var is None:
                return None
            try:
                values[field] = var.get()
            except tk.TclError:
                return None
        return values

    def select_hard_verification(self, enabled):
        self.hard_verification_enabled = bool(enabled)
        if self.hard_verification_var is not None:
            self.hard_verification_var.set("on" if enabled else "off")
        self.refresh_hard_verification_buttons()
        if self.is_host and not self.match_active:
            self.send_lobby_state()

    def refresh_swap_mode_buttons(self):
        if self.swap_mode_var is None:
            return
        try:
            selected = self.swap_mode_var.get()
        except tk.TclError:
            return
        self.swap_mode_enabled = selected == "on"
        for value, button in self.swap_mode_buttons.items():
            try:
                active = value == selected
                button.config(
                    bg=P1_DARK if active else BUTTON_BG,
                    activebackground=P1_COLOR if active else BUTTON_ACTIVE,
                    fg=TEXT if active else MUTED_TEXT,
                )
            except tk.TclError:
                pass
        if (
            not self.is_building_setup_screen
            and self.widget_alive(self.available_space_label)
            and self.widget_alive(self.amount_needed_label)
        ):
            self.update_setup_amount_labels()

    def select_swap_mode(self, enabled):
        self.swap_mode_enabled = bool(enabled)
        if self.swap_mode_var is not None:
            self.swap_mode_var.set("on" if enabled else "off")
        self.refresh_swap_mode_buttons()
        if self.is_host and not self.match_active:
            self.send_lobby_state()

    def refresh_hard_verification_buttons(self):
        if self.hard_verification_var is None:
            return
        try:
            selected = self.hard_verification_var.get()
        except tk.TclError:
            return
        for value, button in self.hard_verification_buttons.items():
            try:
                active = value == selected
                button.config(
                    bg=P1_DARK if active else BUTTON_BG,
                    activebackground=P1_COLOR if active else BUTTON_ACTIVE,
                    fg=TEXT if active else MUTED_TEXT,
                )
            except tk.TclError:
                pass

    def show_setup_screen(self, allow_sanity_rebuild=True):
        current_setup_values = self.get_current_setup_field_values()
        self.cancel_setup_sanity_check()
        self.match_active = False
        self.clear_window()
        self.current_screen = "setup"
        self.setup_generation += 1
        setup_generation = self.setup_generation
        self.is_building_setup_screen = True
        self.root.configure(bg=BG)
        self.host_lobby_rows = {}

        outer = tk.Frame(self.root, bg=BG, padx=20, pady=16)
        outer.pack(fill="both", expand=True)

        self.create_host_lobby_header(outer)
        self.create_host_identity_line(outer)

        middle = tk.Frame(outer, bg=BG)
        middle.pack(fill="x", pady=(0, 3))
        middle.grid_columnconfigure(0, weight=3, minsize=300)
        middle.grid_columnconfigure(1, weight=2, minsize=190)
        middle.grid_rowconfigure(0, weight=1)

        players = self.create_host_player_table(middle, pack_table=False)
        players.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        players.grid_rowconfigure(LOBBY_SLOT_COUNT + 1, weight=1, minsize=12)

        player_controls = tk.Frame(players, bg=PANEL_BG)
        player_controls.grid(
            row=LOBBY_SLOT_COUNT + 2,
            column=0,
            columnspan=4,
            sticky="sew",
            pady=(8, 0),
        )
        player_controls.grid_columnconfigure(0, weight=1)
        player_controls.grid_columnconfigure(1, weight=1)

        self.hard_verification_var = tk.StringVar(
            value=(current_setup_values or {}).get("hard_verification", "off")
        )
        self.hard_verification_enabled = self.hard_verification_var.get() == "on"
        hard_verification_row = tk.Frame(player_controls, bg=PANEL_BG)
        hard_verification_row.grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        hard_verification_row.grid_columnconfigure(1, weight=1)
        self.make_label(
            hard_verification_row,
            "Hard Verification",
            SMALL_FONT,
            fg=TEXT,
            bg=PANEL_BG,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        toggle_buttons = tk.Frame(hard_verification_row, bg=PANEL_BG)
        toggle_buttons.grid(row=0, column=1, sticky="e")
        self.hard_verification_buttons = {}
        for value, label in (("off", "Off"), ("on", "On")):
            button = self.make_button(
                toggle_buttons,
                label,
                lambda enabled=value == "on": self.select_hard_verification(enabled),
                width=5,
            )
            button.config(font=SMALL_FONT, padx=5, pady=4)
            button.pack(side="left", padx=(0, 4) if value == "off" else (0, 0))
            self.hard_verification_buttons[value] = button
        self.hard_verification_var.trace_add(
            "write", lambda *_: self.refresh_hard_verification_buttons()
        )
        self.refresh_hard_verification_buttons()

        self.swap_mode_var = tk.StringVar(
            value=(current_setup_values or {}).get("swap_mode", "off")
        )
        self.swap_mode_enabled = self.swap_mode_var.get() == "on"
        swap_mode_row = tk.Frame(player_controls, bg=PANEL_BG)
        swap_mode_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        swap_mode_row.grid_columnconfigure(1, weight=1)
        self.make_label(
            swap_mode_row,
            "Swap Mode",
            SMALL_FONT,
            fg=TEXT,
            bg=PANEL_BG,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        swap_toggle_buttons = tk.Frame(swap_mode_row, bg=PANEL_BG)
        swap_toggle_buttons.grid(row=0, column=1, sticky="e")
        self.swap_mode_buttons = {}
        for value, label in (("off", "Off"), ("on", "On")):
            button = self.make_button(
                swap_toggle_buttons,
                label,
                lambda enabled=value == "on": self.select_swap_mode(enabled),
                width=5,
            )
            button.config(font=SMALL_FONT, padx=5, pady=4)
            button.pack(side="left", padx=(0, 4) if value == "off" else (0, 0))
            self.swap_mode_buttons[value] = button
        self.swap_mode_var.trace_add(
            "write", lambda *_: self.refresh_swap_mode_buttons()
        )
        self.refresh_swap_mode_buttons()

        self.make_button(
            player_controls,
            "Manage Tasks",
            lambda: self.show_task_editor("setup"),
            width=14,
        ).grid(row=2, column=0, sticky="ew", padx=(0, 4))
        self.make_button(
            player_controls, "Cancel Lobby", self.cancel_hosting, width=14
        ).grid(row=2, column=1, sticky="ew", padx=(4, 0))

        settings = tk.Frame(middle, bg=PANEL_BG, padx=12, pady=8)
        self.setup_settings_panel = settings
        settings.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        settings.grid_columnconfigure(1, weight=1)

        self.make_label(
            settings, "Match Settings", SUBTITLE_FONT, fg=TEXT, bg=PANEL_BG
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.make_label(
            settings,
            self.format_task_meta_line(),
            SMALL_FONT,
            fg=MUTED_TEXT,
            bg=PANEL_BG,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        default_rows, default_cols = self.board_defaults_for_player_count()
        self.board_rows_var = tk.StringVar(
            value=(current_setup_values or {}).get("board_rows", str(default_rows))
        )
        self.board_cols_var = tk.StringVar(
            value=(current_setup_values or {}).get("board_cols", str(default_cols))
        )
        self.win_target_var = tk.StringVar(
            value=(current_setup_values or {}).get("win_target", "Auto")
        )
        self.impossible_tiles_var = tk.StringVar(
            value=(current_setup_values or {}).get("impossible_tiles", "Auto")
        )

        for index, (label, var) in enumerate(
            (
            ("Board Rows", self.board_rows_var),
            ("Board Cols", self.board_cols_var),
            ("Win Target: Auto / value", self.win_target_var),
            ("Impossible Tiles: Auto / value", self.impossible_tiles_var),
            ),
            start=2,
        ):
            self.make_label(
                settings, label, BODY_FONT, fg=TEXT, bg=PANEL_BG
            ).grid(row=index, column=0, sticky="w", pady=2)
            entry = tk.Entry(
                settings,
                textvariable=var,
                width=6,
                font=BODY_FONT,
                bg=PANEL_BG,
                fg=TEXT,
                insertbackground=TEXT,
                relief="solid",
                bd=1,
                justify="center",
            )
            entry.grid(row=index, column=1, sticky="e", pady=2)

        self.available_space_label = self.make_label(
            settings, "", SMALL_FONT, fg=MUTED_TEXT, bg=PANEL_BG
        )
        self.available_space_label.grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(2, 6)
        )

        default_impossible_count = self.auto_impossible_tile_count(
            default_rows, default_cols
        )
        default_counts = self.default_setup_counts(
            default_rows, default_cols, default_impossible_count
        )
        self.easy_var = tk.StringVar(
            value=(current_setup_values or {}).get("easy", str(default_counts["easy"]))
        )
        self.medium_var = tk.StringVar(
            value=(current_setup_values or {}).get(
                "medium", str(default_counts["medium"])
            )
        )
        self.hard_var = tk.StringVar(
            value=(current_setup_values or {}).get("hard", str(default_counts["hard"]))
        )

        for index, (label, var) in enumerate(
            (
            ("Easy tasks", self.easy_var),
            ("Medium tasks", self.medium_var),
            ("Hard tasks", self.hard_var),
            ),
            start=7,
        ):
            self.make_label(
                settings, label, BODY_FONT, fg=TEXT, bg=PANEL_BG
            ).grid(row=index, column=0, sticky="w", pady=2)
            entry = tk.Entry(
                settings,
                textvariable=var,
                width=6,
                font=BODY_FONT,
                bg=PANEL_BG,
                fg=TEXT,
                insertbackground=TEXT,
                relief="solid",
                bd=1,
                justify="center",
            )
            entry.grid(row=index, column=1, sticky="e", pady=2)

        self.amount_needed_label = self.make_label(
            settings, "", SMALL_FONT, fg=MUTED_TEXT, bg=PANEL_BG
        )
        self.amount_needed_label.grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        preset_row = tk.Frame(settings, bg=PANEL_BG)
        preset_row.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for preset_name, label in (
            ("easy", "Easy Preset"),
            ("medium", "Medium Preset"),
            ("hard", "Hard Preset"),
        ):
            button = self.make_button(
                preset_row,
                label,
                lambda name=preset_name: self.apply_difficulty_preset(name),
                width=10,
            )
            button.config(font=SMALL_FONT, padx=4, pady=5)
            button.pack(side="left", fill="x", expand=True, padx=2)

        for var in (
            self.board_rows_var,
            self.board_cols_var,
            self.win_target_var,
            self.impossible_tiles_var,
            self.easy_var,
            self.medium_var,
            self.hard_var,
        ):
            var.trace_add("write", lambda *_: self.update_setup_amount_labels())
        self.update_setup_amount_labels()

        self.host_status_label = self.make_label(
            outer, "", SMALL_FONT, fg=MUTED_TEXT, bg=BG, wraplength=480
        )
        self.host_status_label.pack(fill="x", pady=(0, 2))

        self.setup_error_label = self.make_label(
            outer, "", SMALL_FONT, fg=ERROR, wraplength=420
        )
        self.setup_error_label.pack(fill="x", pady=(0, 2))

        self.countdown_label = self.make_label(
            outer,
            "",
            ("Arial", 22, "bold"),
            fg=TEXT,
            bg=BG,
            wraplength=420,
            justify="center",
        )
        self.update_countdown_display(self.countdown_remaining)

        self.start_button = self.make_button(outer, "Start Match", self.start_match)
        self.start_button.config(font=("Arial", 18, "bold"), pady=10, bg=P1_DARK)
        self.start_button.pack(fill="x")

        self.is_building_setup_screen = False
        self.refresh_host_lobby_display()
        self.update_start_button_state()
        self.schedule_setup_sanity_check(
            setup_generation, allow_rebuild=allow_sanity_rebuild
        )

    def schedule_setup_sanity_check(self, generation, allow_rebuild=True):
        if self.current_screen != "setup":
            return
        if self.setup_sanity_after_id is not None:
            try:
                self.root.after_cancel(self.setup_sanity_after_id)
            except tk.TclError:
                pass
            self.setup_sanity_after_id = None

        def check():
            self.setup_sanity_after_id = None
            self.verify_setup_screen_built(generation, allow_rebuild)

        try:
            self.setup_sanity_after_id = self.root.after(50, check)
        except tk.TclError:
            self.setup_sanity_after_id = None
            pass

    def setup_screen_is_complete(self):
        required_vars = (
            self.board_rows_var,
            self.board_cols_var,
            self.win_target_var,
            self.impossible_tiles_var,
            self.easy_var,
            self.medium_var,
            self.hard_var,
            self.hard_verification_var,
            self.swap_mode_var,
        )
        if any(var is None for var in required_vars):
            return False
        if (
            not self.widget_alive(self.start_button)
            or not self.widget_alive(self.setup_settings_panel)
            or not self.widget_alive(self.available_space_label)
            or not self.widget_alive(self.amount_needed_label)
        ):
            return False
        try:
            return (
                self.start_button.winfo_ismapped()
                and self.setup_settings_panel.winfo_ismapped()
            )
        except tk.TclError:
            return False

    def verify_setup_screen_built(self, generation, allow_rebuild=True):
        if (
            self.current_screen != "setup"
            or generation != self.setup_generation
            or self.match_active
            or self.is_building_setup_screen
        ):
            return
        if self.setup_screen_is_complete():
            return
        if allow_rebuild and not self.setup_rebuild_in_progress:
            self.setup_rebuild_in_progress = True
            self.show_setup_screen(allow_sanity_rebuild=False)

    def update_setup_amount_labels(self):
        if (
            not self.widget_alive(self.available_space_label)
            or not self.widget_alive(self.amount_needed_label)
        ):
            return

        try:
            rows = int(self.board_rows_var.get())
            cols = int(self.board_cols_var.get())
            if not (
                MIN_BOARD_SIZE <= rows <= MAX_BOARD_SIZE
                and MIN_BOARD_SIZE <= cols <= MAX_BOARD_SIZE
            ):
                raise ValueError
            available_space = self.board_cell_count(rows, cols)
        except (TypeError, ValueError, tk.TclError, AttributeError):
            if not (
                self.widget_alive(self.available_space_label)
                and self.widget_alive(self.amount_needed_label)
            ):
                return
            try:
                self.available_space_label.config(text="Available Space: -", fg=MUTED_TEXT)
                self.amount_needed_label.config(
                    text="Amount Needed: Enter valid numbers", fg=MUTED_TEXT
                )
            except tk.TclError:
                return
            self.update_start_button_state()
            return

        try:
            self.available_space_label.config(
                text=f"Available Space: {available_space}", fg=MUTED_TEXT
            )
        except tk.TclError:
            return

        try:
            self.parse_impossible_tile_count(rows, cols)
            task_counts = (
                int(self.easy_var.get()),
                int(self.medium_var.get()),
                int(self.hard_var.get()),
            )
            if any(value < 0 for value in task_counts):
                raise ValueError
            selected_tasks = sum(task_counts)
        except (TypeError, ValueError, tk.TclError, AttributeError):
            if not self.widget_alive(self.amount_needed_label):
                return
            try:
                self.amount_needed_label.config(
                    text="Amount Needed: Enter valid numbers", fg=MUTED_TEXT
                )
            except tk.TclError:
                return
            self.update_start_button_state()
            return

        amount_needed = available_space - selected_tasks
        if amount_needed > 0:
            text = f"Amount Needed: {amount_needed} more tasks"
            color = MUTED_TEXT
        elif amount_needed == 0:
            text = "Amount Needed: Complete"
            color = GOOD
        else:
            text = f"Amount Needed: {abs(amount_needed)} too many tasks"
            color = ERROR
        if not self.widget_alive(self.amount_needed_label):
            return
        try:
            self.amount_needed_label.config(text=text, fg=color)
        except tk.TclError:
            return
        self.update_start_button_state()

    def calculate_difficulty_preset_counts(self, total_cells, preset_name):
        preset = DIFFICULTY_PRESETS[preset_name]
        profile = preset["profile"]
        priority = preset["priority"]
        priority_index = {difficulty: index for index, difficulty in enumerate(priority)}
        raw_counts = {
            difficulty: total_cells * profile[difficulty]
            for difficulty in BOARD_DIFFICULTIES
        }
        counts = {
            difficulty: math.floor(raw_counts[difficulty])
            for difficulty in BOARD_DIFFICULTIES
        }
        remaining = total_cells - sum(counts.values())
        remainders = {
            difficulty: raw_counts[difficulty] - counts[difficulty]
            for difficulty in BOARD_DIFFICULTIES
        }
        order = sorted(
            BOARD_DIFFICULTIES,
            key=lambda difficulty: (
                -remainders[difficulty],
                priority_index.get(difficulty, len(BOARD_DIFFICULTIES)),
            ),
        )
        for difficulty in order[:remaining]:
            counts[difficulty] += 1
        return counts

    def apply_difficulty_preset(self, preset_name):
        try:
            rows = int(self.board_rows_var.get())
            cols = int(self.board_cols_var.get())
            if not (
                MIN_BOARD_SIZE <= rows <= MAX_BOARD_SIZE
                and MIN_BOARD_SIZE <= cols <= MAX_BOARD_SIZE
            ):
                raise ValueError
        except (TypeError, ValueError, tk.TclError, AttributeError):
            self.show_setup_error("Enter valid board rows/cols before applying preset.")
            return

        total_cells = self.board_cell_count(rows, cols)
        counts = self.calculate_difficulty_preset_counts(total_cells, preset_name)
        self.easy_var.set(str(counts["easy"]))
        self.medium_var.set(str(counts["medium"]))
        self.hard_var.set(str(counts["hard"]))
        self.update_setup_amount_labels()

        available = self.difficulty_counts()
        shortages = [
            f"you only have {available[difficulty]} {difficulty} tasks"
            for difficulty in BOARD_DIFFICULTIES
            if counts[difficulty] > available[difficulty]
        ]
        if shortages:
            self.show_setup_error("Preset applied, but " + "; ".join(shortages) + ".")
        elif self.setup_error_label is not None:
            self.setup_error_label.config(text="")

    def setup_settings_are_obviously_valid(self):
        if not self.is_host or not self.has_connected_clients():
            return False
        if any(
            not self.ready_states.get(player, False)
            for player in self.connected_client_ids()
        ):
            return False
        try:
            rows, cols, _target = self.parse_match_settings()
            self.parse_requested_counts(rows, cols)
        except (ValueError, AttributeError, tk.TclError):
            return False
        return True

    def update_start_button_state(self):
        if not self.widget_alive(self.start_button):
            return
        enabled = self.setup_settings_are_obviously_valid()
        try:
            self.start_button.config(
                state=tk.NORMAL if enabled else tk.DISABLED,
                bg=P1_DARK if enabled else BUTTON_BG,
                activebackground=P1_COLOR if enabled else BUTTON_BG,
            )
        except tk.TclError:
            self.start_button = None

    def send_lobby_state(self):
        self.send_message(
            {
                "type": "lobby_state",
                "names": self.player_names,
                "ready_states": self.lobby_ready_payload(),
                "connected_players": self.connected_player_ids(),
                "match_player_ids": self.match_player_ids,
                "player_colors": self.player_colors_payload(),
                "board_rows": self.board_rows,
                "board_cols": self.board_cols,
                "score_target": self.score_target,
                "hard_verification_enabled": self.hard_verification_enabled,
                "swap_mode_enabled": self.swap_mode_enabled,
                **self.swap_state_payload(),
                "max_players": MAX_PLAYERS,
            }
        )

    def update_countdown_display(self, seconds):
        if self.countdown_label is None:
            return
        try:
            if seconds is None:
                self.countdown_label.config(text="")
                self.countdown_label.pack_forget()
            else:
                self.countdown_label.config(text=f"Game starting in {seconds}...")
                if not self.countdown_label.winfo_ismapped():
                    if self.start_button is not None:
                        self.countdown_label.pack(
                            fill="x", pady=(0, 4), before=self.start_button
                        )
                    else:
                        self.countdown_label.pack(fill="x", pady=(0, 4))
        except tk.TclError:
            self.countdown_label = None

    def cancel_countdown(self):
        self.countdown_generation += 1
        if self.countdown_after_id is not None:
            try:
                self.root.after_cancel(self.countdown_after_id)
            except tk.TclError:
                pass
        self.countdown_active = False
        self.countdown_remaining = None
        self.countdown_after_id = None
        self.pending_start_counts = None
        self.update_countdown_display(None)

    def parse_match_settings(self):
        try:
            rows = int(self.board_rows_var.get())
            cols = int(self.board_cols_var.get())
        except (TypeError, ValueError):
            raise ValueError("Board rows and cols must be whole numbers.")

        if not (MIN_BOARD_SIZE <= rows <= MAX_BOARD_SIZE):
            raise ValueError(f"Board rows must be between {MIN_BOARD_SIZE} and {MAX_BOARD_SIZE}.")
        if not (MIN_BOARD_SIZE <= cols <= MAX_BOARD_SIZE):
            raise ValueError(f"Board cols must be between {MIN_BOARD_SIZE} and {MAX_BOARD_SIZE}.")

        player_count = len(self.connected_player_ids())
        target_text = (self.win_target_var.get() or "Auto").strip()
        if target_text.lower() == "auto":
            target = self.auto_score_target(rows, cols, player_count)
        else:
            try:
                target = int(target_text)
            except (TypeError, ValueError):
                raise ValueError("Win Target must be a whole number or Auto.")
            if target < 1 or target > rows * cols:
                raise ValueError(
                    "Win Target must be between 1 and the number of board spaces."
                )

        return rows, cols, target

    def parse_requested_counts(self, rows=None, cols=None):
        rows = self.board_rows if rows is None else rows
        cols = self.board_cols if cols is None else cols
        cell_count = rows * cols
        try:
            counts = {
                "easy": int(self.easy_var.get()),
                "medium": int(self.medium_var.get()),
                "hard": int(self.hard_var.get()),
            }
        except (TypeError, ValueError):
            raise ValueError("Difficulty counts must be whole numbers.")

        if any(value < 0 for value in counts.values()):
            raise ValueError("Difficulty counts cannot be negative.")
        total = sum(counts.values())
        if total != cell_count:
            raise ValueError(f"Difficulty counts must add up to {cell_count}.")
        counts["impossible"] = self.parse_impossible_tile_count(rows, cols)
        return counts

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

    def start_match(self):
        if not self.is_host:
            return
        if not self.can_start_match():
            return
        self.swap_mode_enabled = (
            self.swap_mode_var is not None and self.swap_mode_var.get() == "on"
        )
        self.hard_verification_enabled = (
            self.hard_verification_var is not None
            and self.hard_verification_var.get() == "on"
        )
        try:
            rows, cols, target = self.parse_match_settings()
            counts = self.parse_requested_counts(rows, cols)
        except ValueError as exc:
            self.show_setup_error(str(exc))
            return

        self.board_rows = rows
        self.board_cols = cols
        self.score_target = target
        self.pending_start_counts = counts
        if self.setup_error_label is not None:
            self.setup_error_label.config(text="")
        self.start_or_reset_countdown()

    def start_or_reset_countdown(self):
        if not self.can_start_match():
            return
        self.countdown_generation += 1
        if self.countdown_after_id is not None:
            try:
                self.root.after_cancel(self.countdown_after_id)
            except tk.TclError:
                pass

        self.winner = None
        self.last_announced_winner = None
        self.local_possible.clear()
        self.match_start_time = None
        self.match_end_time = None
        self.countdown_active = True
        self.countdown_remaining = 3
        generation = self.countdown_generation
        self.update_countdown_display(3)
        self.send_message(
            {
                "type": "start_countdown",
                "seconds": 3,
                "names": self.player_names,
                "connected_players": self.connected_player_ids(),
                "match_player_ids": self.match_player_ids,
                "player_colors": self.player_colors_payload(),
                "board_rows": self.board_rows,
                "board_cols": self.board_cols,
                "score_target": self.score_target,
                "hard_verification_enabled": self.hard_verification_enabled,
                "swap_mode_enabled": self.swap_mode_enabled,
                **self.swap_state_payload(),
            }
        )
        if not self.has_connected_clients():
            self.cancel_countdown()
            self.show_setup_error("All clients disconnected during countdown.")
            return
        self.countdown_after_id = self.root.after(
            1000, lambda gen=generation: self.countdown_tick(gen)
        )

    def countdown_tick(self, generation):
        if generation != self.countdown_generation:
            return
        if not self.is_host or self.match_active:
            return
        if not self.can_start_match(False):
            self.cancel_countdown()
            self.show_setup_error("A player disconnected or is no longer ready.")
            return

        self.countdown_remaining -= 1
        if self.countdown_remaining in (2, 1):
            seconds = self.countdown_remaining
            self.update_countdown_display(seconds)
            self.send_message(
                {
                    "type": "start_countdown",
                    "seconds": seconds,
                    "names": self.player_names,
                    "connected_players": self.connected_player_ids(),
                    "match_player_ids": self.match_player_ids,
                    "player_colors": self.player_colors_payload(),
                    "board_rows": self.board_rows,
                    "board_cols": self.board_cols,
                    "score_target": self.score_target,
                    "hard_verification_enabled": self.hard_verification_enabled,
                    "swap_mode_enabled": self.swap_mode_enabled,
                    **self.swap_state_payload(),
                }
            )
            if not self.has_connected_clients():
                self.cancel_countdown()
                self.show_setup_error("All clients disconnected during countdown.")
                return
            self.countdown_after_id = self.root.after(
                1000, lambda gen=generation: self.countdown_tick(gen)
            )
            return

        self.countdown_active = False
        self.countdown_remaining = None
        self.countdown_after_id = None
        self.update_countdown_display(None)
        self.begin_match(generation)

    def build_return_to_setup_message(self):
        return {
            "type": "return_to_setup",
            "names": self.player_names,
            "ready_states": self.lobby_ready_payload(),
            "connected_players": self.connected_player_ids(),
            "match_player_ids": [1],
            "player_colors": self.player_colors_payload(),
            "board_rows": self.board_rows,
            "board_cols": self.board_cols,
            "score_target": self.score_target,
            "hard_verification_enabled": self.hard_verification_enabled,
            "swap_mode_enabled": self.swap_mode_enabled,
            **self.swap_state_payload(),
            "max_players": MAX_PLAYERS,
        }

    def abort_match_start(self, failed_player, sent_players):
        self.cancel_countdown()
        self.cancel_timer_update()
        self.cancel_pending_check()
        self.match_active = False
        self.match_start_time = None
        self.match_end_time = None
        self.winner = None
        self.last_announced_winner = None
        self.local_possible.clear()
        self.match_player_ids = [1]
        self.active_players = self.connected_player_ids()

        if failed_player in self.client_conns:
            self.close_client_socket(failed_player)
            self.player_names[failed_player] = f"Player {failed_player}"

        self.ready_states = {
            1: True,
            **{player: False for player in self.connected_client_ids()},
        }

        return_message = self.build_return_to_setup_message()
        for player in sent_players:
            if player in self.client_conns:
                self.send_to_player(player, return_message)
        self.send_lobby_state()
        if self.has_connected_clients():
            self.start_heartbeat()
        else:
            self.stop_heartbeat()
        self.show_setup_error(f"Player {failed_player} disconnected before match start.")

    def begin_match(self, generation=None):
        if generation is not None and generation != self.countdown_generation:
            return
        if not self.is_host:
            return
        if self.match_active:
            return
        if not self.can_start_match():
            self.cancel_countdown()
            return

        try:
            self.swap_charges = {player: 0 for player in range(1, MAX_PLAYERS + 1)}
            self.forced_swap_players = set()
            self.reroll_animation_counter = 0
            self.last_reroll_animation = None
            self.board = self.generate_board(self.pending_start_counts)
        except ValueError as exc:
            self.countdown_active = False
            self.countdown_remaining = None
            self.countdown_after_id = None
            if self.setup_error_label is not None:
                self.setup_error_label.config(text=str(exc))
            return

        self.cancel_timer_update()
        self.match_start_time = time.time()
        self.match_end_time = None
        self.winner = None
        self.last_announced_winner = None
        self.local_possible.clear()
        self.match_player_ids = self.normalize_player_ids(self.connected_player_ids())
        self.active_players = list(self.match_player_ids)
        self.countdown_active = False
        self.countdown_remaining = None
        self.countdown_after_id = None
        self.update_countdown_display(None)
        start_message = {
            "type": "start_match",
            "names": self.player_names,
            "board": self.board,
            "winner": self.winner,
            "match_active": True,
            "match_start_time": self.match_start_time,
            "match_end_time": self.match_end_time,
            "board_rows": self.board_rows,
            "board_cols": self.board_cols,
            "score_target": self.score_target,
            "hard_verification_enabled": self.hard_verification_enabled,
            "swap_mode_enabled": self.swap_mode_enabled,
            "scores": self.get_scores(),
            **self.swap_state_payload(),
            "connected_players": self.connected_player_ids(),
            "players": self.match_player_ids,
            "match_player_ids": self.match_player_ids,
            "player_colors": self.player_colors_payload(),
        }
        sent_players = []
        for player in self.connected_client_ids():
            if not self.send_to_player(player, {**start_message, "player": player}):
                self.abort_match_start(player, sent_players)
                return
            sent_players.append(player)
        if not self.has_connected_clients():
            self.abort_match_start(0, sent_players)
            self.show_setup_error("All clients disconnected before match start.")
            return
        self.match_active = True
        self.start_heartbeat()
        self.show_game()
        self.start_pending_check()

    def show_game(self):
        self.current_screen = "game"
        self.clear_window()
        self.root.configure(bg=BG)

        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)

        top = tk.Frame(shell, bg=BG, padx=8, pady=8)
        top.pack(fill="x")

        title = f"{APP_TITLE} - You are {self.player_names[self.player]}"
        self.make_label(top, title, SUBTITLE_FONT, fg=TEXT).pack(side="left")

        reset_state = tk.NORMAL if self.is_host else tk.DISABLED
        self.reset_button = self.make_button(
            top, "Reset", self.reset_game, width=14, state=reset_state
        )
        self.reset_button.pack(side="right", padx=(8, 0))
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
        self.check_winner()
        self.start_timer_loop()

    def parse_time(self, value, fallback=None):
        if value is None:
            return fallback
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def format_elapsed_time(self, elapsed):
        minutes, seconds = divmod(max(0, int(elapsed)), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def start_timer_loop(self):
        self.cancel_timer_update()
        self.timer_generation += 1
        generation = self.timer_generation
        self.update_match_timer(generation)

    def start_pending_check(self):
        self.cancel_pending_check()
        if not self.is_host or not self.match_active or self.match_end_time is not None:
            return
        self.pending_check_generation += 1
        generation = self.pending_check_generation
        self.pending_check_after_id = self.root.after(
            PENDING_CHECK_INTERVAL_MS,
            lambda gen=generation: self.pending_check_tick(gen),
        )

    def cancel_pending_check(self):
        self.pending_check_generation += 1
        if self.pending_check_after_id is not None:
            try:
                self.root.after_cancel(self.pending_check_after_id)
            except tk.TclError:
                pass
            self.pending_check_after_id = None

    def pending_owner_is_active(self, player):
        if not isinstance(player, int) or not (1 <= player <= MAX_PLAYERS):
            return False
        if player not in self.active_game_players():
            return False
        return player == 1 or player in self.client_conns

    def reset_pending_cell(self, cell):
        cell["owner"] = None
        cell["status"] = STATUS_EMPTY
        cell["pending_owner"] = None
        cell["pending_until"] = None
        cell["pending_review"] = False
        cell["swap_reward_given"] = False

    def complete_pending_cell(self, cell):
        owner = cell["pending_owner"]
        cell["owner"] = owner
        cell["status"] = STATUS_COMPLETE
        cell["pending_owner"] = None
        cell["pending_until"] = None
        cell["pending_review"] = False
        self.award_impossible_swap_reward(cell, owner)

    def finish_pending_manual_change(self, row, col, check_for_winner=False):
        self.clear_pending_review_pause(row, col)
        self.local_possible.discard((row, col))
        self.refresh_grid()
        self.update_scores()
        if check_for_winner:
            self.check_winner()
        self.broadcast_state()

    def manual_award_pending_tile(self, row, col):
        if not self.is_host or not (0 <= row < self.board_rows and 0 <= col < self.board_cols):
            return False

        cell = self.board[row][col]
        if cell.get("status") != STATUS_PENDING:
            return False
        if not self.pending_owner_is_active(cell.get("pending_owner")):
            return False

        self.complete_pending_cell(cell)
        self.finish_pending_manual_change(row, col, check_for_winner=True)
        return True

    def manual_reset_pending_tile(self, row, col):
        if not self.is_host or not (0 <= row < self.board_rows and 0 <= col < self.board_cols):
            return False

        cell = self.board[row][col]
        if cell.get("status") != STATUS_PENDING:
            return False

        self.reset_pending_cell(cell)
        self.finish_pending_manual_change(row, col)
        return True

    def clear_pending_review_pause(self, row, col):
        self.pending_review_pauses.pop((row, col), None)
        if 0 <= row < self.board_rows and 0 <= col < self.board_cols:
            self.board[row][col]["pending_review"] = False

    def begin_pending_review_pause(self, row, col):
        cell = self.board[row][col]
        pending_until = self.parse_time(cell.get("pending_until"))
        remaining = 0.0 if pending_until is None else max(0.0, pending_until - time.time())
        self.pending_review_pauses[(row, col)] = {
            "pending_owner": cell.get("pending_owner"),
            "remaining": remaining,
        }
        cell["pending_review"] = True
        self.refresh_grid()
        self.broadcast_state()

    def end_pending_review_pause(self, row, col, resume=True):
        pause = self.pending_review_pauses.pop((row, col), None)
        if pause is None:
            return False
        if not (0 <= row < self.board_rows and 0 <= col < self.board_cols):
            return False

        cell = self.board[row][col]
        if (
            cell.get("status") == STATUS_PENDING
            and cell.get("pending_owner") == pause.get("pending_owner")
        ):
            if resume:
                cell["pending_until"] = time.time() + float(pause.get("remaining", 0.0))
            cell["pending_review"] = False
            self.refresh_grid()
            self.broadcast_state()
            return True
        return False

    def close_pending_dialog(self, resume=True):
        tile = self.pending_dialog_tile
        dialog = self.pending_dialog
        self.pending_dialog = None
        self.pending_dialog_tile = None
        if dialog is not None:
            try:
                dialog.destroy()
            except tk.TclError:
                pass
        if tile is not None:
            self.end_pending_review_pause(tile[0], tile[1], resume=resume)

    def pending_time_remaining_text(self, cell):
        pending_until = self.parse_time(cell.get("pending_until"))
        if pending_until is None:
            return "Auto-complete timer unavailable"
        remaining = max(0, int(math.ceil(pending_until - time.time())))
        return f"Auto-completes in: {remaining}s"

    def show_pending_tile_dialog(self, row, col):
        if not self.is_host or not (0 <= row < self.board_rows and 0 <= col < self.board_cols):
            return

        cell = self.board[row][col]
        if cell.get("status") != STATUS_PENDING:
            return

        self.close_pending_dialog()
        dialog = tk.Toplevel(self.root)
        self.pending_dialog = dialog
        self.pending_dialog_tile = (row, col)
        self.begin_pending_review_pause(row, col)
        dialog.title("Pending Task")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)

        pending_owner = cell.get("pending_owner")
        claimant = self.display_player_name(pending_owner) or "Unknown"
        claimant_active = self.pending_owner_is_active(pending_owner)

        outer = tk.Frame(dialog, bg=BG, padx=18, pady=16)
        outer.pack(fill="both", expand=True)
        self.make_label(
            outer,
            "Pending Task",
            SUBTITLE_FONT,
            fg=TEXT,
            bg=BG,
        ).pack(anchor="w", pady=(0, 10))
        self.make_label(
            outer,
            cell.get("text", ""),
            BODY_FONT,
            fg=TEXT,
            bg=BG,
            wraplength=340,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        self.make_label(
            outer,
            f"Difficulty: {cell.get('difficulty', 'easy')}",
            SMALL_FONT,
            fg=MUTED_TEXT,
            bg=BG,
        ).pack(anchor="w")
        self.make_label(
            outer,
            f"Pending claimant: {claimant}",
            SMALL_FONT,
            fg=GOOD if claimant_active else ERROR,
            bg=BG,
        ).pack(anchor="w", pady=(3, 0))
        self.make_label(
            outer,
            self.pending_time_remaining_text(cell),
            SMALL_FONT,
            fg=MUTED_TEXT,
            bg=BG,
        ).pack(anchor="w", pady=(3, 14))

        buttons = tk.Frame(outer, bg=BG)
        buttons.pack(fill="x")

        def award_and_close():
            self.manual_award_pending_tile(row, col)
            self.close_pending_dialog(resume=False)

        def reset_and_close():
            self.manual_reset_pending_tile(row, col)
            self.close_pending_dialog(resume=False)

        award_state = tk.NORMAL if claimant_active else tk.DISABLED
        self.make_button(
            buttons,
            "Award to claimant",
            award_and_close,
            width=16,
            state=award_state,
        ).pack(side="left", padx=(0, 6))
        self.make_button(
            buttons,
            "Reset tile",
            reset_and_close,
            width=10,
        ).pack(side="left", padx=(0, 6))
        self.make_button(
            buttons,
            "Cancel",
            self.close_pending_dialog,
            width=10,
        ).pack(side="left")
        dialog.protocol("WM_DELETE_WINDOW", self.close_pending_dialog)
        try:
            dialog.grab_set()
            dialog.focus_force()
        except tk.TclError:
            pass

    def process_pending_tiles(self):
        now = time.time()
        changed = False
        for row in range(self.board_rows):
            for col in range(self.board_cols):
                cell = self.board[row][col]
                if cell.get("status") != STATUS_PENDING:
                    continue

                owner = cell.get("pending_owner")
                pending_until = self.parse_time(cell.get("pending_until"))
                pause = self.pending_review_pauses.get((row, col))
                if pause is not None:
                    if (
                        pause.get("pending_owner") != owner
                        or not self.pending_owner_is_active(owner)
                    ):
                        self.clear_pending_review_pause(row, col)
                        self.reset_pending_cell(cell)
                    else:
                        continue
                elif (
                    not self.pending_owner_is_active(owner)
                    or pending_until is None
                ):
                    self.reset_pending_cell(cell)
                elif now >= pending_until:
                    self.complete_pending_cell(cell)
                else:
                    continue

                self.local_possible.discard((row, col))
                changed = True
        return changed

    def reset_pending_tiles_for_player(self, player):
        changed = False
        for row in range(self.board_rows):
            for col in range(self.board_cols):
                cell = self.board[row][col]
                if (
                    cell.get("status") == STATUS_PENDING
                    and cell.get("pending_owner") == player
                ):
                    self.clear_pending_review_pause(row, col)
                    self.reset_pending_cell(cell)
                    self.local_possible.discard((row, col))
                    changed = True
        return changed

    def pending_check_tick(self, generation=None):
        if generation is not None and generation != self.pending_check_generation:
            return
        self.pending_check_after_id = None
        if (
            not self.is_host
            or not self.match_active
            or self.match_end_time is not None
            or self.winner is not None
        ):
            return

        if self.process_pending_tiles():
            self.refresh_grid()
            self.update_scores()
            self.broadcast_state()

        if (
            self.is_host
            and self.match_active
            and self.match_end_time is None
            and self.winner is None
        ):
            self.pending_check_after_id = self.root.after(
                PENDING_CHECK_INTERVAL_MS,
                lambda gen=generation: self.pending_check_tick(gen),
            )

    def cancel_timer_update(self):
        self.timer_generation += 1
        if self.timer_after_id is not None:
            try:
                self.root.after_cancel(self.timer_after_id)
            except tk.TclError:
                pass
            self.timer_after_id = None

    def update_match_timer(self, generation=None):
        if generation is not None and generation != self.timer_generation:
            return

        if self.timer_label is None:
            return

        if self.match_start_time is None:
            elapsed = 0
        else:
            end_time = self.match_end_time
            now = end_time if end_time is not None else time.time()
            elapsed = max(0, int(now - self.match_start_time))

        try:
            minutes, seconds = divmod(elapsed, 60)
            self.timer_label.config(text=f"Time: {minutes:02d}:{seconds:02d}")
        except tk.TclError:
            self.timer_label = None
            self.timer_after_id = None
            return

        self.timer_after_id = None
        if (
            self.match_start_time is not None
            and self.match_end_time is None
            and self.winner is None
        ):
            self.timer_after_id = self.root.after(
                250,
                lambda gen=self.timer_generation: self.update_match_timer(gen),
            )

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

    def bring_window_forward(self):
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(500, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except tk.TclError:
            pass

    def update_winner_display(self, previous_winner=None):
        if self.winner is None:
            if self.winner_banner is not None:
                self.winner_banner.pack_forget()
            self.last_announced_winner = None
            if self.reset_button is not None:
                try:
                    self.reset_button.config(
                        text="Reset",
                        command=self.reset_game,
                        state=tk.NORMAL if self.is_host else tk.DISABLED,
                    )
                except tk.TclError:
                    self.reset_button = None
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
        if self.reset_button is not None:
            try:
                self.reset_button.config(
                    text="Return to Lobby",
                    command=self.reset_game,
                    state=tk.NORMAL if self.is_host else tk.DISABLED,
                )
            except tk.TclError:
                self.reset_button = None

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
            or self.winner is not None
            or not self.match_active
            or self.match_end_time is not None
        ):
            return "break"

        if self.is_host and self.board[row][col].get("status") == STATUS_PENDING:
            if mode == STATUS_COMPLETE:
                self.show_pending_tile_dialog(row, col)
            return "break"

        if self.player in self.forced_swap_players:
            changed, message = self.use_swap(self.player, row, col)
            if self.status_label is not None:
                self.status_label.config(
                    text=message
                    if not changed
                    else "Swap used. You can claim tiles again.",
                    fg=GOOD if changed else ERROR,
                )
            if changed:
                self.refresh_grid()
                self.animate_tile_reroll(row, col, self.player)
                self.update_scores()
                self.broadcast_state()
            return "break"

        if mode == STATUS_POSSIBLE:
            self.toggle_local_possible(row, col)
            return "break"

        if self.is_move_allowed(row, col, self.player, mode):
            self.apply_move(row, col, self.player, mode)
            self.refresh_grid()
            self.update_scores()
            self.check_winner()

            if self.is_host:
                self.broadcast_state()
            else:
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
        if self.player in self.forced_swap_players:
            if self.status_label is not None:
                self.status_label.config(
                    text="You must use Swap before claiming another tile.",
                    fg=ERROR,
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
        cell = self.board[row][col]
        owner = cell["owner"]
        current_status = cell["status"]

        if self.winner is not None:
            return False
        if player in self.forced_swap_players:
            return False

        if owner not in (None, player):
            return False

        if status == STATUS_COMPLETE:
            return (
                current_status == STATUS_EMPTY
                or (owner == player and current_status == STATUS_COMPLETE)
            )

        return False

    def apply_move(self, row, col, player, status):
        cell = self.board[row][col]

        if status == STATUS_COMPLETE and cell["owner"] == player:
            if cell["status"] == STATUS_COMPLETE:
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

    def current_board_task_ids(self):
        task_ids = set()
        for row in self.board:
            for cell in row:
                task_id = cell.get("task_id")
                if task_id:
                    task_ids.add(str(task_id))
        return task_ids

    def unused_replacement_task(self, difficulty):
        used_ids = self.current_board_task_ids()
        candidates = [
            task
            for task in self.task_data.get("tasks", [])
            if task.get("difficulty") == difficulty
            and task.get("id")
            and str(task.get("id")) not in used_ids
            and task.get("text")
        ]
        if not candidates:
            return None
        return random.choice(candidates)

    def use_swap(self, player, row, col):
        if (
            not self.match_active
            or self.match_end_time is not None
            or self.winner is not None
            or player not in self.active_game_players()
            or player not in self.forced_swap_players
            or self.swap_charges.get(player, 0) < 1
            or not isinstance(row, int)
            or not isinstance(col, int)
            or not (0 <= row < self.board_rows)
            or not (0 <= col < self.board_cols)
        ):
            return False, "You must use Swap before claiming another tile."

        cell = self.board[row][col]
        difficulty = cell.get("difficulty")
        if (
            cell.get("status") != STATUS_EMPTY
            or cell.get("owner") is not None
            or cell.get("pending_owner") is not None
            or difficulty not in BOARD_DIFFICULTIES
            or not cell.get("task_id")
            or not cell.get("text")
        ):
            return False, "You can only swap an empty non-impossible tile."

        replacement = self.unused_replacement_task(difficulty)
        if replacement is None:
            return False, "No unused tasks available for that difficulty."

        cell["task_id"] = replacement.get("id", "")
        cell["text"] = replacement.get("text", "")
        cell["difficulty"] = replacement.get("difficulty", difficulty)
        cell["owner"] = None
        cell["status"] = STATUS_EMPTY
        cell["pending_owner"] = None
        cell["pending_until"] = None
        cell["pending_review"] = False
        cell["swap_reward_given"] = False
        self.local_possible.discard((row, col))

        remaining = max(0, self.swap_charges.get(player, 0) - 1)
        self.swap_charges[player] = remaining
        if remaining <= 0:
            self.forced_swap_players.discard(player)
        self.reroll_animation_counter += 1
        self.last_reroll_animation = {
            "id": self.reroll_animation_counter,
            "row": row,
            "col": col,
            "player": player,
        }
        return True, "Swap used. You can claim tiles again."

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
                if cell["status"] == STATUS_COMPLETE and cell["owner"] in scores:
                    scores[cell["owner"]] += 1
        return scores

    def check_winner(self):
        scores = self.get_scores()
        previous_winner = self.winner
        if self.winner is None:
            for player in self.active_game_players():
                score = scores.get(player, 0)
                if score >= self.score_target:
                    self.winner = player
                    self.match_active = False
                    if self.match_end_time is None:
                        self.match_end_time = time.time()
                    break

        if self.winner is not None:
            self.match_active = False
            if self.match_end_time is None:
                self.match_end_time = time.time()
            self.cancel_timer_update()
            self.cancel_pending_check()
            self.update_match_timer()
            self.update_winner_display(previous_winner)
            if previous_winner is None:
                self.send_final_state_burst()

        return self.winner

    def build_state_message(self):
        return {
            "type": "state",
            "tile_state": self.get_tile_state(),
            "names": self.player_names,
            "winner": self.winner,
            "match_active": self.match_active,
            "match_start_time": self.match_start_time,
            "match_end_time": self.match_end_time,
            "board_rows": self.board_rows,
            "board_cols": self.board_cols,
            "score_target": self.score_target,
            "hard_verification_enabled": self.hard_verification_enabled,
            "swap_mode_enabled": self.swap_mode_enabled,
            "scores": self.get_scores(),
            **self.swap_state_payload(),
            "connected_players": self.connected_player_ids(),
            "players": self.active_game_players(),
            "match_player_ids": self.active_game_players(),
            "player_colors": self.player_colors_payload(),
            "reroll_animation": self.last_reroll_animation,
        }

    def send_final_state_burst(self):
        message = self.build_state_message()
        self.send_message(message)
        self.root.after(100, lambda msg=message: self.send_message(msg))
        self.root.after(300, lambda msg=message: self.send_message(msg))

    def get_tile_state(self):
        return [
            [
                self.get_tile_state_cell(self.board[row][col])
                for col in range(self.board_cols)
            ]
            for row in range(self.board_rows)
        ]

    def get_tile_state_cell(self, cell):
        normalized = self.normalize_board_cell(cell)
        return {
            "task_id": normalized["task_id"],
            "text": normalized["text"],
            "difficulty": normalized["difficulty"],
            "owner": normalized["owner"],
            "status": normalized["status"],
            "pending_owner": normalized["pending_owner"],
            "pending_until": normalized["pending_until"],
            "pending_review": normalized["pending_review"],
            "swap_reward_given": normalized["swap_reward_given"],
        }

    def apply_state_message(self, message):
        previous_winner = self.winner
        self.board_rows = int(message.get("board_rows", self.board_rows) or self.board_rows)
        self.board_cols = int(message.get("board_cols", self.board_cols) or self.board_cols)
        self.score_target = int(message.get("score_target", self.score_target) or self.score_target)
        self.hard_verification_enabled = bool(
            message.get("hard_verification_enabled", self.hard_verification_enabled)
        )
        self.swap_mode_enabled = bool(
            message.get("swap_mode_enabled", self.swap_mode_enabled)
        )
        self.apply_swap_state_message(message)
        if "board" in message:
            raw_board = message["board"]
            for row in range(self.board_rows):
                for col in range(self.board_cols):
                    if row < len(raw_board) and col < len(raw_board[row]):
                        self.board[row][col] = self.normalize_board_cell(raw_board[row][col])
                    if self.board[row][col]["status"] in (STATUS_COMPLETE, STATUS_PENDING):
                        self.local_possible.discard((row, col))
        else:
            tile_state = message.get("tile_state", [])
            for row in range(min(self.board_rows, len(tile_state))):
                for col in range(min(self.board_cols, len(tile_state[row]))):
                    state = tile_state[row][col]
                    cell = dict(self.board[row][col])
                    cell.update(state)
                    self.board[row][col] = self.normalize_board_cell(cell)
                    if self.board[row][col]["status"] in (STATUS_COMPLETE, STATUS_PENDING):
                        self.local_possible.discard((row, col))
        raw_names = message.get("names", self.player_names)
        self.player_names = {int(key): value for key, value in raw_names.items()}
        self.winner = message.get("winner")
        self.match_active = bool(message.get("match_active", self.match_active))

        if self.tiles:
            self.refresh_grid()
            self.update_scores()
            self.check_winner()
            self.update_winner_display(previous_winner)

    def broadcast_state(self):
        self.check_winner()
        message = self.build_state_message()
        self.send_message(message)
        if self.winner is not None:
            self.root.after(100, lambda msg=message: self.send_message(msg))

    def reset_game(self):
        if not self.is_host:
            return
        self.cancel_setup_sanity_check()
        self.cancel_countdown()
        self.cancel_timer_update()
        self.cancel_pending_check()
        self.cancel_tile_animations()
        self.close_pending_dialog(resume=False)
        self.match_active = False
        self.winner = None
        self.last_announced_winner = None
        self.match_start_time = None
        self.match_end_time = None
        self.timer_label = None
        self.local_possible.clear()
        self.pending_review_pauses.clear()
        self.board_canvas = None
        self.board_container = None
        self.tiles = []
        self.score_labels = {}
        self.score_bar = None
        self.reset_button = None
        self.status_label = None
        self.winner_banner = None
        self.winner_banner_name = None
        self.winner_banner_result = None
        self.swap_charges = {player: 0 for player in range(1, MAX_PLAYERS + 1)}
        self.forced_swap_players = set()
        self.reroll_animation_counter = 0
        self.last_reroll_animation = None
        self.match_player_ids = [1]
        self.active_players = self.connected_player_ids()
        self.board_rows, self.board_cols = self.board_defaults_for_player_count()
        self.score_target = self.auto_score_target(
            self.board_rows, self.board_cols, len(self.connected_player_ids())
        )
        self.ready_states = {1: True, **{player: False for player in self.connected_client_ids()}}
        self.hard_verification_enabled = False
        self.swap_mode_enabled = False
        self.send_message(
            {
                "type": "return_to_setup",
                "names": self.player_names,
                "ready_states": self.lobby_ready_payload(),
                "connected_players": self.connected_player_ids(),
                "match_player_ids": self.match_player_ids,
                "player_colors": self.player_colors_payload(),
                "board_rows": self.board_rows,
                "board_cols": self.board_cols,
                "score_target": self.score_target,
                "hard_verification_enabled": self.hard_verification_enabled,
                "swap_mode_enabled": self.swap_mode_enabled,
                **self.swap_state_payload(),
                "max_players": MAX_PLAYERS,
            }
        )
        if self.has_connected_clients():
            now = time.time()
            for player in self.connected_client_ids():
                self.last_pong_times[player] = now
            self.start_heartbeat()
        self.show_setup_screen()

    def send_task_sync(self, player=None):
        message = {
            "type": "task_sync",
            "task_data": self.task_data,
            "task_metadata": self.task_metadata(),
            "names": self.player_names,
            "ready_states": self.lobby_ready_payload(),
            "connected_players": self.connected_player_ids(),
            "match_player_ids": self.match_player_ids,
            "player_colors": self.player_colors_payload(),
            "board_rows": self.board_rows,
            "board_cols": self.board_cols,
            "score_target": self.score_target,
            "hard_verification_enabled": self.hard_verification_enabled,
            "swap_mode_enabled": self.swap_mode_enabled,
            **self.swap_state_payload(),
            "max_players": MAX_PLAYERS,
        }
        if player is None:
            self.send_message(message)
        else:
            self.send_to_player(player, message)

    def start_reader_thread(self, conn=None, player=None):
        active_conn = conn if conn is not None else self.conn
        threading.Thread(
            target=self.read_messages, args=(active_conn, player), daemon=True
        ).start()

    def read_messages(self, active_conn, player=None):
        try:
            if active_conn is None:
                return
            file = active_conn.makefile("r", encoding="utf-8")
            for line in file:
                message = json.loads(line)
                self.root.after(
                    0,
                    lambda msg=message, sender=player: self.handle_message(
                        msg, sender
                    ),
                )
            if not self.disconnected:
                if self.is_host and player in self.client_conns:
                    self.root.after(
                        0,
                        lambda pid=player: self.mark_player_disconnected(
                            pid, f"Player {pid} disconnected."
                        ),
                    )
                elif not self.is_host:
                    self.root.after(0, self.show_disconnected)
        except (OSError, ValueError, json.JSONDecodeError):
            if not self.disconnected:
                if self.is_host and player in self.client_conns:
                    self.root.after(
                        0,
                        lambda pid=player: self.mark_player_disconnected(
                            pid, f"Player {pid} disconnected."
                        ),
                    )
                elif not self.is_host:
                    self.root.after(0, self.show_disconnected)

    def handle_message(self, message, sender_player=None):
        msg_type = message.get("type")

        if msg_type == "join" and self.is_host:
            player = sender_player or int(message.get("player", 0) or 0)
            if player not in self.client_conns:
                return
            self.player_names[player] = (
                message.get("name") or f"Player {player}"
            )[:22]
            self.ready_states[player] = False
            self.last_pong_times[player] = time.time()
            self.start_heartbeat()
            self.send_to_player(
                player,
                {
                    "type": "welcome",
                    "player": player,
                    "names": self.player_names,
                    "ready_states": self.lobby_ready_payload(),
                    "connected_players": self.connected_player_ids(),
                    "match_player_ids": self.match_player_ids,
                    "player_colors": self.player_colors_payload(),
                    "board_rows": self.board_rows,
                    "board_cols": self.board_cols,
                    "score_target": self.score_target,
                    "hard_verification_enabled": self.hard_verification_enabled,
                    "swap_mode_enabled": self.swap_mode_enabled,
                    **self.swap_state_payload(),
                    "max_players": MAX_PLAYERS,
                },
            )
            client_meta = message.get("task_metadata", {})
            comparison = self.compare_task_metadata(self.task_metadata(), client_meta)
            if comparison >= 0:
                self.send_task_sync(player)
                self.show_setup_screen()
                self.send_lobby_state()
            else:
                self.send_to_player(player, {"type": "request_task_pool"})

        elif msg_type == "ready_state" and self.is_host:
            player = int(message.get("player", sender_player or 0) or 0)
            if player in self.client_conns and player == sender_player:
                self.ready_states[player] = bool(message.get("ready"))
                try:
                    self.refresh_host_lobby_display()
                except tk.TclError:
                    pass
                self.send_lobby_state()

        elif msg_type == "leave_lobby" and self.is_host:
            player = int(message.get("player", sender_player or 0) or 0)
            if player in self.client_conns and player == sender_player:
                self.mark_player_disconnected(player, f"Player {player} left the lobby.")

        elif msg_type == "pong" and self.is_host:
            if sender_player in self.client_conns:
                self.last_pong_times[sender_player] = time.time()

        elif msg_type == "request_task_pool":
            self.send_message(
                {
                    "type": "task_pool",
                    "task_data": self.task_data,
                    "task_metadata": self.task_metadata(),
                }
            )

        elif msg_type == "task_pool" and self.is_host:
            incoming = message.get("task_data", {})
            incoming_meta = message.get("task_metadata", {})
            if self.compare_task_metadata(incoming_meta, self.task_metadata()) >= 0:
                self.set_task_data(incoming)
            self.send_task_sync()
            self.show_setup_screen()
            self.send_lobby_state()

        elif msg_type == "task_sync":
            incoming = message.get("task_data", {})
            self.set_task_data(incoming)
            self.hard_verification_enabled = bool(
                message.get("hard_verification_enabled", self.hard_verification_enabled)
            )
            self.swap_mode_enabled = bool(
                message.get("swap_mode_enabled", self.swap_mode_enabled)
            )
            self.board = self.empty_board()
            self.local_possible.clear()
            if self.is_host:
                self.show_setup_screen()
            else:
                self.show_waiting_lobby()

        elif msg_type == "start_match":
            self.player = message.get("player", 2)
            raw_names = message.get("names", self.player_names)
            self.player_names = {int(key): value for key, value in raw_names.items()}
            self.hard_verification_enabled = bool(
                message.get("hard_verification_enabled", self.hard_verification_enabled)
            )
            self.swap_mode_enabled = bool(
                message.get("swap_mode_enabled", self.swap_mode_enabled)
            )
            self.board = message["board"]
            self.local_possible.clear()
            self.winner = message.get("winner")
            self.match_active = True
            self.show_game()

        elif msg_type == "move" and self.is_host:
            if self.winner is not None or not self.match_active or self.match_end_time is not None:
                self.send_message(self.build_state_message())
                return

            row = message.get("row")
            col = message.get("col")
            player = message.get("player")
            status = message.get("status")
            if sender_player not in self.client_conns:
                return
            if sender_player not in self.active_game_players():
                self.send_to_player(sender_player, self.build_state_message())
                return
            if player != sender_player:
                self.send_to_player(sender_player, self.build_state_message())
                return
            if self.valid_move_payload(row, col, player, status):
                if self.is_move_allowed(row, col, player, status):
                    self.apply_move(row, col, player, status)
                    self.refresh_grid()
                    self.update_scores()
                    self.check_winner()
            self.broadcast_state()

        elif msg_type == "use_swap" and self.is_host:
            row = message.get("row")
            col = message.get("col")
            player = message.get("player")
            if sender_player not in self.client_conns:
                return
            if sender_player not in self.active_game_players():
                self.send_to_player(sender_player, self.build_state_message())
                return
            if player != sender_player:
                self.send_to_player(sender_player, self.build_state_message())
                return
            if isinstance(row, int) and isinstance(col, int):
                changed, _message = self.use_swap(player, row, col)
                if changed:
                    self.refresh_grid()
                    self.animate_tile_reroll(row, col, player)
                    self.update_scores()
            self.broadcast_state()

        elif msg_type == "state":
            self.apply_state_message(message)

        elif msg_type == "return_to_setup":
            raw_names = message.get("names", self.player_names)
            self.player_names = {int(key): value for key, value in raw_names.items()}
            self.hard_verification_enabled = bool(
                message.get("hard_verification_enabled", self.hard_verification_enabled)
            )
            self.swap_mode_enabled = bool(
                message.get("swap_mode_enabled", self.swap_mode_enabled)
            )
            self.match_active = False
            self.winner = None
            self.last_announced_winner = None
            self.local_possible.clear()
            self.show_waiting_lobby()

    def valid_move_payload(self, row, col, player, status):
        return (
            isinstance(row, int)
            and isinstance(col, int)
            and 0 <= row < self.board_rows
            and 0 <= col < self.board_cols
            and isinstance(player, int)
            and 1 <= player <= MAX_PLAYERS
            and status == STATUS_COMPLETE
        )

    def send_to_player(self, player, message):
        conn = self.client_conns.get(player)
        if conn is None:
            return False

        try:
            data = json.dumps(message) + "\n"
            with self.lock:
                conn.sendall(data.encode("utf-8"))
            return True
        except OSError:
            if not self.disconnected:
                if self.is_host:
                    self.root.after(
                        0,
                        lambda pid=player: self.mark_player_disconnected(
                            pid, f"Player {pid} disconnected."
                        ),
                    )
                else:
                    self.root.after(0, self.show_disconnected)
            return False

    def send_message(self, message):
        if self.is_host:
            for player in self.connected_client_ids():
                self.send_to_player(player, message)
            return

        if self.conn is None:
            return

        try:
            data = json.dumps(message) + "\n"
            with self.lock:
                self.conn.sendall(data.encode("utf-8"))
        except OSError:
            if not self.disconnected:
                self.root.after(0, self.show_disconnected)

    def show_error(self, text):
        self.clear_window()
        self.root.configure(bg=BG)

        outer = tk.Frame(self.root, bg=BG, padx=24, pady=22)
        outer.pack(fill="both", expand=True)

        self.make_label(
            outer,
            text,
            BODY_FONT,
            fg=ERROR,
            bg=BG,
            wraplength=380,
        ).pack(pady=(0, 16))

        self.make_button(outer, "Back to Menu", self.show_main_menu).pack()

    def show_disconnected(self):
        if self.disconnected:
            return

        self.disconnected = True
        self.cancel_countdown()
        self.cancel_pending_check()
        self.close_sockets()
        self.match_active = False
        self.match_start_time = None
        self.match_end_time = None
        self.timer_label = None
        self.clear_window()
        self.root.configure(bg=BG)

        outer = tk.Frame(self.root, bg=BG, padx=24, pady=22)
        outer.pack(fill="both", expand=True)

        self.make_label(outer, "Disconnected.", TITLE_FONT, fg=ERROR).pack(
            pady=(0, 16)
        )
        self.make_button(outer, "Back to Menu", self.show_main_menu).pack()


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskKnockout(root)
    root.mainloop()
