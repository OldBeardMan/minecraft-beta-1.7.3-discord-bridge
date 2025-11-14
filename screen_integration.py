"""
GNU Screen integration - sends commands to Minecraft screen session
"""
import subprocess
import os


def send_to_screen(command, session_name):
    """
    Sends a command to Minecraft screen session

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
