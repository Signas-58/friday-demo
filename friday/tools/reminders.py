import datetime
from typing import Optional
from friday.database import save_reminder, list_pending_reminders_db, delete_reminder_db

def schedule_reminder(message: str, delay_minutes: float = 0, time_str: str = "") -> str:
    """
    Schedule a reminder for F.R.I.D.A.Y. to notify the user.
    
    Args:
        message: The reminder topic or text (e.g. 'check server logs', 'drink water').
        delay_minutes: Number of minutes from now to trigger the reminder (e.g. 15 or 0.5).
        time_str: Optional specific time of day today (e.g. '14:30' or '09:00'). Ignored if delay_minutes > 0.
    """
    now = datetime.datetime.now()
    target_time = None
    
    if delay_minutes and delay_minutes > 0:
        target_time = now + datetime.timedelta(minutes=delay_minutes)
    elif time_str:
        try:
            parts = [int(p) for p in time_str.strip().split(":")]
            hour = parts[0]
            minute = parts[1] if len(parts) > 1 else 0
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                # If target time is earlier today, schedule for tomorrow
                target_time += datetime.timedelta(days=1)
        except Exception:
            return f"Error: Could not parse time format '{time_str}'. Use HH:MM format (e.g. 14:30)."
    else:
        # Default to 5 minutes if neither provided
        target_time = now + datetime.timedelta(minutes=5)
    
    remind_at_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    remind_at_display = target_time.strftime("%I:%M %p").lstrip("0")
    
    reminder_id = save_reminder(message, remind_at_str)
    return f"⏰ Reminder #{reminder_id} set for {remind_at_display}: '{message}'."

def list_reminders() -> str:
    """List all active pending reminders."""
    reminders = list_pending_reminders_db()
    if not reminders:
        return "No pending reminders found."
    
    lines = ["📋 **Active Reminders:**"]
    for r in reminders:
        lines.append(f"- **ID #{r['id']}**: {r['message']} *(Scheduled for: {r['remind_at']})*")
    return "\n".join(lines)

def delete_reminder(reminder_id: int) -> str:
    """Cancel / remove a scheduled reminder by its ID number."""
    success = delete_reminder_db(reminder_id)
    if success:
        return f"Successfully deleted reminder #{reminder_id}."
    return f"Error: Reminder #{reminder_id} was not found or has already been triggered."

def register(mcp):
    """Register reminder tools on the FastMCP server."""
    mcp.tool()(schedule_reminder)
    mcp.tool()(list_reminders)
    mcp.tool()(delete_reminder)
