import sys
import ctypes

# Windows Virtual Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_KEYUP = 0x0002

def _send_vk_key(vk_code: int, repeat_count: int = 1):
    """Sends a native Windows User32 virtual key press and release event."""
    if sys.platform != "win32":
        return
    for _ in range(repeat_count):
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)

def set_system_volume(action: str = "up", steps: int = 5) -> str:
    """
    Adjust host Windows system master volume or mute state.
    
    Args:
        action: 'up', 'down', 'mute', or 'unmute'.
        steps: Number of volume steps to change (defaults to 5, where 1 step ≈ 2% volume).
    """
    if sys.platform != "win32":
        return "Error: System volume control is only supported on Windows host machines."
        
    act = action.lower().strip()
    steps = max(1, min(50, steps))
    
    if act == "up":
        _send_vk_key(VK_VOLUME_UP, steps)
        return f"🔊 System volume increased by {steps} steps."
    elif act == "down":
        _send_vk_key(VK_VOLUME_DOWN, steps)
        return f"🔉 System volume decreased by {steps} steps."
    elif act in ["mute", "unmute", "toggle_mute"]:
        _send_vk_key(VK_VOLUME_MUTE, 1)
        return "🔇 System audio mute toggled."
    else:
        return f"Error: Unknown volume action '{action}'. Supported actions: 'up', 'down', 'mute', 'unmute'."

def control_media_playback(action: str = "play_pause") -> str:
    """
    Control active Windows media playback (Spotify, YouTube, Chrome/Edge audio, Media Player).
    
    Args:
        action: 'play', 'pause', 'play_pause', 'next', 'previous', or 'stop'.
    """
    if sys.platform != "win32":
        return "Error: Media control is only supported on Windows host machines."
        
    act = action.lower().strip()
    
    if act in ["play", "pause", "play_pause", "toggle"]:
        _send_vk_key(VK_MEDIA_PLAY_PAUSE, 1)
        return "⏯️ Media playback play/pause toggled."
    elif act in ["next", "skip", "forward"]:
        _send_vk_key(VK_MEDIA_NEXT_TRACK, 1)
        return "⏭️ Skipped to next track."
    elif act in ["previous", "prev", "back", "rewind"]:
        _send_vk_key(VK_MEDIA_PREV_TRACK, 1)
        return "⏮️ Returned to previous track."
    elif act in ["stop"]:
        _send_vk_key(VK_MEDIA_STOP, 1)
        return "⏹️ Media playback stopped."
    else:
        return f"Error: Unknown media action '{action}'. Supported actions: 'play_pause', 'next', 'previous', 'stop'."

def register(mcp):
    """Register system volume and media tools on the FastMCP server."""
    mcp.tool()(set_system_volume)
    mcp.tool()(control_media_playback)
