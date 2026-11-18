"""
GNU Screen integration - sends commands to Minecraft screen session
"""
import subprocess

# Characters that GNU screen's `stuff` command interprets specially:
#   ^X   -> control character (e.g. ^M = Enter)
#   \ooo -> octal escape (e.g. \015 = Enter)
#   $VAR -> environment variable expansion
# Letting any of these through would allow a Discord user to inject
# arbitrary console commands (e.g. "hi^Mop attacker").
SCREEN_SPECIAL_CHARS = set('^\\$')


def sanitize_for_console(text):
    """
    Makes untrusted text safe to pass to the server console via screen.

    Removes newlines, control/non-printable characters, Minecraft color
    codes (§) and characters screen interprets specially.
    """
    text = text.replace('\r', ' ').replace('\n', ' ')
    return ''.join(
        ch for ch in text
        if ch.isprintable() and ch != '§' and ch not in SCREEN_SPECIAL_CHARS
    ).strip()


def send_to_screen(command, session_name):
    """
    Sends a command to Minecraft screen session.
    The command MUST already be sanitized with sanitize_for_console().

    Args:
        command (str): Command to send
        session_name (str): Screen session name

    Returns:
        bool: True if success, False if error
    """
    try:
        result = subprocess.run(
            ['screen', '-S', session_name, '-X', 'stuff', f"{command}\r"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode == 0:
            return True
        else:
            print(f"Error sending to screen: {result.stderr.decode()}")
            return False

    except FileNotFoundError:
        print("screen is not installed")
        return False
    except Exception as e:
        print(f"Error sending to screen: {e}")
        return False
