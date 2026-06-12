# Task-Knockout

Task-Knockout is a small multiplayer task-board race game made with Python and Tkinter.

One player hosts the game, the other players connect as clients, and everyone races to complete tasks on a shared board. The host can choose board size, task difficulty amounts, hard verification, swap mode, and more.

It is mostly meant as a fun “play random games and complete random objectives” type of tool.

## Features

* Multiplayer host/client setup
* Up to 5 players
* Custom task pool through `tasks.json`
* Easy / Medium / Hard / Impossible task difficulties
* Hard Verification mode
* Swap Mode with reroll animations
* Local saved names and last-used IPs
* Built-in task manager on the host side
* Works over LAN, or over VPN tools if needed

## Requirements

* Python 3.10 or newer
* No extra Python packages needed

Tkinter is included with most normal Python installs.
On some Linux installs, you may need to install Tkinter separately, for example `python3-tk`.

## Files

The main files are:

```text
taskknockout_host.py
taskknockout_client.py
tasks.json
.gitignore
```

Generated local config files are created automatically when the app runs. You do not need to download or edit them manually.

## How to Play on the Same PC

This is the easiest way to test it.

1. Open a terminal in the game folder.
2. Start the host:

```bash
python taskknockout_host.py
```

3. Open another terminal in the same folder.
4. Start the client:

```bash
python taskknockout_client.py
```

5. On the client, use:

```text
127.0.0.1
```

6. Connect, ready up, then start the match from the host window.

## How to Play on LAN

Use this if everyone is on the same Wi-Fi / local network.

1. The host runs:

```bash
python taskknockout_host.py
```

2. The host clicks `Host Game`.
3. The host shares the IP shown in the host window.
4. Other players run:

```bash
python taskknockout_client.py
```

5. Clients enter the host IP and connect.
6. Everyone readies up.
7. The host chooses settings and starts the match.

The default port is:

```text
5000
```

If clients cannot connect, the host may need to allow Python through the firewall.

## Playing Online

LAN is recommended because it is the simplest.

If LAN is not an option, you can use a VPN/LAN tool such as Hamachi, Radmin VPN, ZeroTier, or something similar.

Basic idea:

1. Everyone joins the same VPN network.
2. The host starts `taskknockout_host.py`.
3. The host shares their VPN/LAN IP.
4. Clients enter that IP in `taskknockout_client.py`.
5. Connect and play normally.

Do not use `127.0.0.1` for other people connecting to you.
That only works when the host and client are on the same computer.

## Host Controls

The host can:

* Manage the task pool
* Choose board rows and columns
* Choose win target
* Choose Easy / Medium / Hard task amounts
* Enable or disable Hard Verification
* Enable or disable Swap Mode
* Start and reset matches

## Task Pool

Tasks are stored in:

```text
tasks.json
```

You can edit tasks from inside the host app using `Manage Tasks`.

The task pool supports:

```text
easy
medium
hard
impossible
```

Impossible tasks are mainly used with Swap Mode.

## Hard Verification

When Hard Verification is on, hard tasks do not complete instantly.

Instead, they enter a pending state and complete after a short timer, unless the host reviews them manually.

## Swap Mode

Swap Mode adds impossible tasks and lets players earn swaps.

When a player completes an impossible task, they earn a swap and must use it before claiming another tile. A swap rerolls an empty normal tile into a different task of the same difficulty.

## Local Config Files

The app may create these files automatically:

```text
taskknockout_host_config.json
taskknockout_client_config.json
```

They save small local things like player names or last-used IPs.

These files are ignored by Git and should not be uploaded publicly.

## Common Issues

### Client cannot connect

Try these:

* Make sure the host app is running.
* Make sure the client is using the correct host IP.
* Make sure everyone is on the same LAN or VPN network.
* Allow Python through the host computer’s firewall.
* Make sure port `5000` is not blocked.

### 127.0.0.1 does not work for my friend

`127.0.0.1` only means “this computer.”

Use the host’s LAN IP or VPN IP instead.

### Tasks are missing or weird

Make sure `tasks.json` is in the same folder as `taskknockout_host.py`.

## License

This project is released under the MIT License.

You can use it, modify it, and share it for free.
