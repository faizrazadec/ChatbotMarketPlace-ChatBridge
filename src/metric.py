import datetime


def compute_avg_response_time(messages):
    """
    Compute the average response time (in seconds) between a user's message and the assistant's reply.
    Assumes that messages is a list of dicts with 'role', 'content', and 'timestamp' keys.
    """
    response_times = []
    # Loop through messages, looking for a user message followed by an assistant message.
    for i in range(len(messages) - 1):
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            # Ensure both messages have timestamps.
            if messages[i].get("timestamp") and messages[i + 1].get("timestamp"):
                t_user = datetime.datetime.fromisoformat(messages[i]["timestamp"])
                t_assistant = datetime.datetime.fromisoformat(
                    messages[i + 1]["timestamp"]
                )
                response_times.append((t_assistant - t_user).total_seconds())
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        return f"{avg_time:.1f} sec"
    else:
        return "N/A"
