# Task Knockout

Task Knockout is a multiplayer task-race board game built with Python and Tkinter.
Players join a host over a local network or VPN, race to complete randomized video
game challenges, and claim tiles on a shared board until someone reaches the score
target.

The game is designed for challenge runs, variety gaming, party streams, or any
session where everyone is playing their own game and racing to prove they completed
the same style of task first.

Important: the host app only hosts games. Host-to-host connecting is not supported;
players who want to join a lobby should use `taskknockout_client.py`.

## Features

- Host-managed lobby for up to 5 total players.
- Dedicated host and client apps.
- Custom task pool stored in `tasks.json`.
- Task difficulties: `easy`, `medium`, `hard`, and `impossible`.
- Configurable board size from 1x1 to 8x8.
- Configurable win target, including an automatic target based on board size and
  player count.
- Difficulty presets for quick setup.
- Optional Hard Verification mode for delayed approval on harder tasks.
- Optional Swap Mode with impossible tiles and task rerolls.
- Ready checks, countdown, match timer, score bar, and winner banner.
- Basic heartbeat handling for disconnected players.

## Requirements

- Python 3.10 or newer
- Tkinter, which is included with most standard Python installations
- All players must be able to reach the host on TCP port `5000`

No third-party Python packages are required.

## Files

| File | Purpose |
| --- | --- |
| `taskknockout_host.py` | Main host app. It hosts matches and manages tasks. |
| `taskknockout_client.py` | Lightweight client app for players joining a host. |
| `tasks.json` | Saved task pool used to generate boards. |
| `README.md` | Project guide. |

The app will also create (or update if there is one) small local config files to remember the last used player
name or host IP. (It's in the same folder/place that the script is in.)

## Included Task Pool

FYI: this project includes a pre-made `tasks.json` file for convenience. You do
not have to come up with a large task list before playing; the included file gives
you a starting pool of easy, medium, hard, and impossible tasks right away.

You can still edit, remove, or add tasks from inside the host app with
**Manage Tasks**.

## Hosting A Game

Run `taskknockout_host.py`, enter your player name, then click **Host Game**.
The lobby shows the IP address and port that clients should use.

For players on the same computer, clients can connect to:

```text
127.0.0.1
```

For players on the same local network, share the host machine's local IP address (which can also be copied)
For online play, Hamachi is recommended or you can use the IP address provided by your LAN/VPN tool.

The host can:

- Manage the task pool before starting.
- See connected players and ready states.
- Choose board rows and columns.
- Choose the win target or leave it on `Auto`.
- Choose the number of easy, medium, and hard tasks.
- Enable or disable Hard Verification.
- Enable or disable Swap Mode.
- Start the match once at least one client is connected and all clients are ready.

## Joining A Game

Run `taskknockout_client.py`, enter your name, enter the host IP, then click
**Connect**. Once connected, click **READY** and wait for the host to start.

The host is always Player 1. Joined players are assigned the next available slot.

## Match Setup

The host controls the board before the match begins.

| Setting | Description |
| --- | --- |
| Board Rows | Number of board rows. Must be between `1` and `8`. |
| Board Cols | Number of board columns. Must be between `1` and `8`. |
| Win Target | Number of claimed tiles needed to win. Use `Auto` or a whole number. |
| Easy Tasks | Number of easy tasks on the board. |
| Medium Tasks | Number of medium tasks on the board. |
| Hard Tasks | Number of hard tasks on the board. |
| Impossible Tiles | Number of impossible tasks when Swap Mode is enabled (Default is off). Use `Auto` or a whole number. |

Easy, medium, and hard task counts must add up to the number of spaces on the
board. If Swap Mode is enabled, impossible tiles replace some of those normal
tasks when the board is generated.

## How To Play

Each tile contains a task. Complete the task in your game, then claim the tile in
Task Knockout. Your color fills the tile and your score increases by one.

The first player to reach the win target wins. When a winner is found, the match
timer stops and the winner banner appears for everyone.

### Controls

| Action | Control |
| --- | --- |
| Claim an empty tile | Left click the tile |
| Unclaim your own completed tile | Left click your completed tile again |
| Mark a tile as possible | Shift + left click |
| Remove your possible marker | Shift + left click the tile again |
| Review a pending tile as host | Host left clicks the pending tile |

Possible markers are local helper marks. They help you remember tasks you may be
able to complete, but they do not claim the tile and are not a shared score state.
Impossible tiles cannot be marked as possible.

## Hard Verification

When Hard Verification is off, claiming a tile completes it immediately.

When Hard Verification is on:

- Hard tasks enter a pending state for 10 seconds.
- Impossible tasks enter a pending state for 30 seconds.
- The host can click a pending tile to review it and if needed ask for proof from the player that did it.
- The host may award the tile to the claimant or reset the tile.
- If the host does not intervene, the pending tile auto-completes when the timer
  finishes.

Opening the host review dialog pauses that tile's auto-complete timer until the
dialog is closed.

## Swap Mode

Swap Mode adds impossible tiles to the board. Impossible tiles are meant to be
high-risk, high-reward tasks.

When a player completes an impossible tile, they earn a swap charge and must use
that swap before claiming another tile. To use a swap, click an empty,
non-impossible tile. The game rerolls that tile into another unused task of the
same difficulty.

Swap notes:

- Swaps only work on empty Easy, Medium, or Hard difficulty tiles.
- Completed, pending, owned, and impossible tiles cannot be swapped.
- The replacement task is unused on the current board and it has the same difficulty.
- Keeping extra easy, medium, and hard tasks in `tasks.json` gives Swap Mode more
  room to reroll tiles.

When **Impossible Tiles** is set to `Auto`, the game chooses a small number based
on board size. Very small boards (Less than 20) get no impossible tiles.

## Technical Breakdown

This section explains how the main match systems work internally.

### Board Generation

The host generates the board when the countdown finishes. The board size is:

```text
Board Rows x Board Cols
```

The easy, medium, and hard task counts must add up to that board size. The host
then randomly samples tasks from `tasks.json` for each difficulty and shuffles the
final board.

For example, a 5x5 board has 25 spaces, so easy + medium + hard must equal 25.

### Auto Win Target

When **Win Target** is set to `Auto`, the game uses:

```text
ceil(board spaces / active players)
```

That means a 5x5 board with 2 players uses `ceil(25 / 2)`, so the target is 13.

### Impossible Tile Calculation

Impossible tiles only matter when Swap Mode is enabled. If Swap Mode is off, the
impossible tile count is always 0.

When **Impossible Tiles** is set to `Auto`, the game calculates the count from the
board size:

| Board spaces | Auto impossible tiles |
| --- | --- |
| Fewer than 20 | 0 |
| 20 to 35 | 1 |
| 36 to 63 | 2 |
| 64 or more | 3 |

The final number is also capped by the number of impossible tasks available in
`tasks.json`, so the game will not request more impossible tasks than actually
exist (So if you wanted 20 Impossible tasks but only have 10 in the `tasks.json` file then it won't start a game).

### How Impossible Tiles Replace Other Tasks

Impossible tiles do not add extra spaces to the board. They replace normal tasks
after the host has already chosen easy, medium, and hard counts.

Replacement order is:

```text
hard -> medium -> easy
```

So if the host sets a 25-space board with:

```text
Easy: 10
Medium: 10
Hard: 5
Impossible Tiles: 2
```

the final generated board becomes:

```text
Easy: 10
Medium: 10
Hard: 3
Impossible: 2
```
Another example:

A 25-space board with:

```text
Easy: 10
Medium: 10
Hard: 5
Impossible Tiles: 20
```

the final generated board becomes:

```text
Easy: 5
Medium: 0
Hard: 0
Impossible: 20
```
Impossible tiles replace hard tasks first. If there are not enough hard tasks to replace, the remaining replacements come from medium tasks, then easy tasks.

### Swap Rerolls

Completing an impossible tile in Swap Mode gives that player a swap charge. The
player must spend the swap before claiming another tile.

When the player clicks a valid tile to spend the swap, the game:

1. Checks that the tile is empty, normal difficulty, and not pending or owned.
2. Looks for unused tasks in `tasks.json` with the same difficulty as that tile.
3. Randomly chooses one unused replacement task.
4. Replaces the tile's task text and ID.
5. Spends one swap charge.

The rerolled tile keeps the same difficulty. A hard tile rerolls into another hard
task, a medium tile into another medium task, and an easy tile into another easy
task. Impossible tiles cannot be rerolled this way.

If no unused task of that difficulty is available, the swap fails and the player
must pick a different valid tile.

### Hard Verification Timing

When Hard Verification is on, hard and impossible claims become pending before
they count as completed.

```text
Hard task: 10 seconds pending
Impossible task: 30 seconds pending
```

If the timer finishes, the tile is awarded automatically. If the host opens the
pending review dialog, the timer pauses until the dialog closes. The host can then
award the tile to the claimant or reset it back to empty.

## Managing Tasks

Click **Manage Tasks** in the host app to open the task editor.

You can:

- Add a task.
- Edit the selected task.
- Remove the selected task.
- Choose a task difficulty.

Tasks are saved to `tasks.json`. The host syncs the active task pool to connected
players when they join or when the pool changes before a match.

Each task has:

- A unique ID.
- Task text.
- A difficulty value.

Valid difficulty values are:

```text
easy
medium
hard
impossible
```

## Network Notes

Task Knockout uses TCP port `5000`.

If clients cannot connect:

- Make sure the host app is running and hosting a lobby.
- Confirm the clients are using the correct host IP.
- Allow Python through the host computer's firewall.
- If playing online, use a VPN/LAN tool and share that tool's IP address.
- Use `127.0.0.1` only when the client is running on the same computer as the host.

Clients cannot join once a match is already in progress.

## Troubleshooting

**The Start Match button is disabled.**  
At least one client must be connected, every connected client must be ready, and
the task counts must match the board size.

**The game says there are not enough tasks.**  
Add more tasks for the missing difficulty in **Manage Tasks**, or lower that
difficulty's count in match setup.

**A swap does not work.**  
The selected tile must be empty, normal difficulty, and have an unused replacement
task of the same difficulty available.

**A player disconnected.**  
The host removes that player from the active connection list. Pending tiles owned
by that player are reset.

## Development Notes

This project uses only the Python standard library:

- `tkinter` for the UI
- `socket` and `threading` for networking
- `json` for task/config storage

There is no build step. Run the Python scripts directly from the project folder.

## License

This project is released under the MIT License.

You can use it, modify it, and share it for free.
