# Harvested by harvest_parts.py
# capability : CAP-0004 (track streak)
# from       : habit-tracker @ c9d2b6b72fbf8f4008aa9b29d0e4f48f584949e8
# source     : app.py:215-253
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def calculate_streaks(log_dates):
    if not log_dates:
        return 0,0,0
    
    log_dates = sorted([d for d in log_dates if isinstance(d, date)])
    
    total_completions = len(log_dates)
    longest_streak = 0
    current_streak = 0 
    streak = 1

    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # check if streak is in log
    if log_dates[-1] == today:
        current_streak = 1
    else:
        current_streak = 0

    # logs in order
    for i in range(1, len(log_dates)):
        prev = log_dates[i - 1]
        curr = log_dates[i]
        if(curr - prev).days == 1:
            streak +=1
        else:
            streak = 1

        if curr == today:
            current_streak = streak
        elif curr == yesterday and today not in log_dates:
            current_streak = streak

        longest_streak = max(longest_streak, streak)

    longest_streak = max(longest_streak, current_streak)

    return total_completions, current_streak, longest_streak
