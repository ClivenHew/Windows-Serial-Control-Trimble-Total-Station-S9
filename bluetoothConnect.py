"""
Bluetooth connection + discovery helpers for the Trimble total station.

Connection: wraps `sudo rfcomm connect <id> <mac> <channel>` (the command
you were previously running by hand in a separate terminal) so it can be
launched, monitored, retried, and cleanly torn down from within main.py.

Discovery: shells out to standard BlueZ command-line tools to list paired
devices, probe advertised RFCOMM/SPP channels, and check which local
rfcomm ids are free, so main.py can present a menu instead of requiring
the MAC/channel/id to be typed in blind.

Tools used:
    rfcomm        - connect/release bindings, list currently bound ids
    bluetoothctl  - lists paired devices (part of the `bluez` package)
    sdptool       - browses a device's advertised services/channels
                    (part of `bluez-utils` / older `bluez` on some distros;
                    install with `sudo apt install bluez-tools` if missing)

IMPORTANT - passwordless sudo:
`rfcomm connect` needs root privileges. Since this now runs from inside
Python (non-interactively), there is no terminal for `sudo` to prompt for
a password on. You have two options:

1. (Recommended) Allow your user to run *only* the rfcomm command as root
   without a password. Run `sudo visudo` and add a line such as:

       your_username ALL=(root) NOPASSWD: /usr/bin/rfcomm

   Replace `your_username` with `whoami`'s output and confirm the path
   with `which rfcomm`.

2. Run the whole Python program itself with sudo (`sudo python3 main.py`).
   Simpler, but then the script (and any bugs in it) run as root.

Without one of the above, `subprocess` will hang forever waiting on a sudo
password prompt that never appears.
"""

import os
import re
import subprocess
import time
import atexit


def release_rfcomm(rfcomm_id=0):
    """Release any existing binding on this rfcomm id. Never raises."""
    try:
        subprocess.run(
            ["sudo", "-n", "rfcomm", "release", str(rfcomm_id)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        pass


def stop_bluetooth(process, rfcomm_id=0):
    """Terminate a running rfcomm connect process and release the binding."""
    if process is not None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    release_rfcomm(rfcomm_id)


def connect_bluetooth(
    mac_address,
    channel=1,
    rfcomm_id=0,
    max_retries=5,
    retry_delay=5,
    connect_timeout=15,
):
    """
    Establish an RFCOMM link to the Trimble device over Bluetooth by
    launching `sudo rfcomm connect <id> <mac> <channel>` as a background
    process. That process must stay alive for as long as /dev/rfcommN is
    to remain usable, so its handle is returned to the caller, who is
    responsible for keeping it around and terminating it on shutdown
    (see stop_bluetooth) or on disconnect (see is_bluetooth_alive).

    Retries with a fixed delay between attempts, up to max_retries times.

    Returns:
        (process, device_path) on success
        (None, None) if every attempt failed
    """
    device_path = f"/dev/rfcomm{rfcomm_id}"

    for attempt in range(1, max_retries + 1):
        print(f"[Bluetooth] Connection attempt {attempt}/{max_retries} "
              f"to {mac_address} (channel {channel})...")

        # Clear out any stale binding before trying again
        release_rfcomm(rfcomm_id)
        time.sleep(1)

        try:
            process = subprocess.Popen(
                ["sudo", "-n", "rfcomm", "connect", str(rfcomm_id),
                 mac_address, str(channel)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as error:
            print(f"[Bluetooth] Failed to launch rfcomm: {error}")
            time.sleep(retry_delay)
            continue

        # Wait for the device node to appear, the process to die, or timeout
        start_time = time.time()
        connected = False

        while time.time() - start_time < connect_timeout:
            if process.poll() is not None:
                # rfcomm exited early (bad MAC, device off, auth failure,
                # missing NOPASSWD sudo rule, etc.) - this attempt failed
                break

            if os.path.exists(device_path):
                connected = True
                break

            time.sleep(0.5)

        if connected:
            print(f"[Bluetooth] Connected: {device_path}")
            return process, device_path

        # This attempt failed - clean up before retrying
        print(f"[Bluetooth] Attempt {attempt} failed or timed out "
              f"waiting for {device_path}.")

        leftover_output = ""
        try:
            if process.stdout:
                leftover_output = process.stdout.read(500)
        except Exception:
            pass
        if leftover_output.strip():
            print(f"[Bluetooth] rfcomm output: {leftover_output.strip()}")

        stop_bluetooth(process, rfcomm_id)

        if attempt < max_retries:
            print(f"[Bluetooth] Retrying in {retry_delay} seconds...\n")
            time.sleep(retry_delay)

    print("[Bluetooth] All connection attempts failed.")
    return None, None


def connect_bluetooth_cycle_ids(
    mac_address,
    channel,
    free_ids,
    retries_per_id=2,
    retry_delay=3,
    connect_timeout=15,
):
    """
    Try to establish the Bluetooth link starting from the lowest rfcomm id
    in `free_ids` and working upward, moving on to the next free id if the
    current one fails after `retries_per_id` attempts.

    This exists because a given id can occasionally fail to bind (stale
    kernel state, permission hiccup, etc.) even though `rfcomm` reports it
    as free - cycling to the next id is cheap and avoids getting stuck.

    Returns:
        (process, device_path, rfcomm_id) on success
        (None, None, None) if every free id was exhausted
    """
    for rfcomm_id in sorted(free_ids):
        print(f"\n[Bluetooth] Trying RFCOMM id {rfcomm_id}...")

        process, device_path = connect_bluetooth(
            mac_address=mac_address,
            channel=channel,
            rfcomm_id=rfcomm_id,
            max_retries=retries_per_id,
            retry_delay=retry_delay,
            connect_timeout=connect_timeout,
        )

        if process is not None:
            return process, device_path, rfcomm_id

        print(f"[Bluetooth] RFCOMM id {rfcomm_id} did not work, "
              f"moving to the next free id.")

    print("[Bluetooth] Exhausted all free RFCOMM ids - none worked.")
    return None, None, None


def is_bluetooth_alive(process, device_path):
    """
    Check whether the rfcomm connect process is still running and the
    device node still exists. If either is false, the Bluetooth link has
    dropped and a reconnect is needed.
    """
    if process is None:
        return False
    if process.poll() is not None:
        return False
    if not os.path.exists(device_path):
        return False
    return True


# --------------------------------------------------------------------------
# Discovery helpers - used to build the interactive connection menu in
# main.py. Each function shells out to a BlueZ command-line tool; if the
# tool isn't installed or the call fails, the function returns an empty
# result so main.py can fall back to manual entry rather than crashing.
# --------------------------------------------------------------------------

def get_paired_devices(timeout=5):
    """
    Return a list of (mac_address, name) tuples for paired Bluetooth
    devices, using `bluetoothctl devices Paired`. Falls back to
    `bluetoothctl devices` (all known devices) on older BlueZ versions
    that don't support the Paired filter. Returns [] on any failure.
    """
    for args in (["bluetoothctl", "devices", "Paired"],
                 ["bluetoothctl", "devices"]):
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            print("[Discovery] bluetoothctl not found - is bluez installed?")
            return []
        except subprocess.TimeoutExpired:
            continue

        if result.returncode != 0:
            continue

        devices = []
        for line in result.stdout.splitlines():
            # Lines look like: "Device 00:12:F3:21:50:78 Trimble S7"
            match = re.match(
                r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line.strip()
            )
            if match:
                devices.append((match.group(1), match.group(2)))

        if devices:
            return devices

    return []


def discover_channels(mac_address, service="SP", timeout=15):
    """
    Probe a paired device for advertised RFCOMM channels using sdptool.
    `service` defaults to "SP" (Serial Port profile), which is what the
    Trimble total stations use.

    Returns a sorted list of unique channel numbers (ints). Returns []
    if sdptool is missing, the device doesn't respond, or nothing is
    found within the timeout - callers should fall back to manual entry
    (channel 1 is the common default for SPP).
    """
    try:
        result = subprocess.run(
            ["sdptool", "search", "--bdaddr", mac_address, service],
            capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        print("[Discovery] sdptool not found - install with "
              "`sudo apt install bluez-tools` to enable channel discovery.")
        return []
    except subprocess.TimeoutExpired:
        print(f"[Discovery] Channel search timed out after {timeout}s.")
        return []

    channels = sorted({
        int(match) for match in re.findall(r"Channel:\s*(\d+)", result.stdout)
    })
    return channels


def get_bound_rfcomm_ids(timeout=5):
    """
    Return the set of rfcomm ids currently bound (in use), by parsing the
    output of `rfcomm` (no args, which lists all active bindings).
    Returns an empty set if none are bound or the command fails.
    """
    try:
        result = subprocess.run(
            ["rfcomm"], capture_output=True, text=True, timeout=timeout
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()

    bound = set()
    for line in result.stdout.splitlines():
        # Lines look like: "rfcomm0: 00:12:F3:21:50:78 channel 1 clean"
        match = re.match(r"rfcomm(\d+):", line.strip())
        if match:
            bound.add(int(match.group(1)))

    return bound


def get_free_rfcomm_ids(max_id=9):
    """Return a sorted list of unbound rfcomm ids in range [0, max_id]."""
    bound = get_bound_rfcomm_ids()
    return [i for i in range(max_id + 1) if i not in bound]

def cleanup_bluetooth_state(bluetooth_state):
    """
    Stop and release the Bluetooth connection stored in a mutable state
    dictionary.

    Expected dictionary keys:
        process
        rfcomm_id
    """
    process = bluetooth_state.get("process")
    rfcomm_id = bluetooth_state.get("rfcomm_id", 0)

    if process is not None:
        print("\n[Bluetooth] Releasing connection...")
        stop_bluetooth(process, rfcomm_id)

    bluetooth_state["process"] = None


def register_bluetooth_cleanup(bluetooth_state):
    """
    Register Bluetooth cleanup for normal program termination.

    SIGINT is intentionally not overridden here. This allows Ctrl+C to
    raise KeyboardInterrupt normally so the currently running operation,
    such as start_multitrack_search(), can catch it, return False, and
    return control to the main menu without closing the whole program.

    The atexit cleanup still releases Bluetooth when the program actually
    exits normally or because of an unhandled exception.
    """
    atexit.register(
        cleanup_bluetooth_state,
        bluetooth_state,
    )

