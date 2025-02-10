"""
This module computes the average response time (in seconds) 
between a user's message and the assistant's reply.
"""

import datetime


def compute_avg_response_time(messages):
    """
    Compute the average response time (in seconds) between a user's message and the assistant's reply.

    Args:
        messages (list): A list of dictionaries where each message contains:
            - 'role' (str): Either 'user' or 'assistant'.
            - 'content' (str): The message text.
            - 'timestamp' (str): The ISO-formatted timestamp.

    Returns:
        str: The average response time formatted as "<time> sec", or "N/A" if no valid pairs exist.
    """
    response_times = []

    # Loop through messages, looking for a user message followed by an assistant message.
    for i in range(len(messages) - 1):
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            # Ensure both messages have timestamps.
            if messages[i].get("timestamp") and messages[i + 1].get("timestamp"):
                t_user = datetime.datetime.fromisoformat(messages[i]["timestamp"])
                t_assistant = datetime.datetime.fromisoformat(messages[i + 1]["timestamp"])
                response_times.append((t_assistant - t_user).total_seconds())

    if response_times:
        avg_time = sum(response_times) / len(response_times)
        return f"{avg_time:.1f} sec"

    return "N/A"  # Removed unnecessary else
