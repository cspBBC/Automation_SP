from ..helpers.generic_query_helpers import execute_query
from typing import Dict, Any


# scenario-specific wrappers -------------------------------------------------

def getSchdGrpDetails(scheduling_team_id: int) -> Dict[str, Any]:
    """Fetch the scheduling-team row using hard‑coded SQL.

    The query resides here so that test modules only depend on a single
    function.  ``generic_query_helpers`` merely runs whatever SQL it is given
    and returns the result as a list of dicts.
    """
    sql = """
        SELECT *
        FROM SchedulingTeams
        WHERE schedulingteamid = ?
    """
    results = execute_query(sql, [scheduling_team_id])
    return results[0] if results else {}



def validateSchdGrpActive(scheduling_team_id: int) -> bool:
    """Return ``True`` if the scheduling team is active.

    Uses hard‑coded SQL to check the isActive column for the given team ID.
    """
    sql = """
        SELECT isActive
        FROM SchedulingTeams
        WHERE schedulingteamid = ?
    """
    results = execute_query(sql, [scheduling_team_id])
    if results:
        return results[0].get('isActive', False) == 1
    return False


def getSchdGrpHistory(scheduling_team_id: int, user_id: int) -> list:
    """Fetch history records for a scheduling team.

    Returns all audit trail records (create, update, delete actions) for the given team,
    ordered by most recent first (descending historyid).

    Args:
        scheduling_team_id: The team ID to fetch history for
        user_id: The user ID who performed the action

    Returns:
        List of history dictionaries, or empty list if none found
    """
    sql = """
        SELECT *
        FROM History
        WHERE userid = ? AND attributeid = ?
        ORDER BY historyid DESC
    """
    results = execute_query(sql, [user_id, scheduling_team_id])
    return results if results else []


def validateSchdGrpHistoryExists(scheduling_team_id: int, user_id: int, expected_count: int = None) -> bool:
    """Validate that history records exist for a scheduling team.

    Can optionally verify a specific count of records.

    Args:
        scheduling_team_id: The team ID
        user_id: The user who performed the action
        expected_count: Optional - expected number of history records

    Returns:
        True if records exist (and count matches if provided), False otherwise
    """
    history = getSchdGrpHistory(scheduling_team_id, user_id)
    
    if not history:
        return False
    
    if expected_count is not None:
        return len(history) == expected_count
    
    return len(history) > 0


def validateSchdGrpHistoryAction(scheduling_team_id: int, user_id: int, expected_action: str) -> bool:
    """Validate that the most recent history record has a specific action.

    Args:
        scheduling_team_id: The team ID
        user_id: The user who performed the action
        expected_action: The expected action (e.g., 'Created', 'Record updated', 'DELETE')

    Returns:
        True if latest action matches, False otherwise
    """
    history = getSchdGrpHistory(scheduling_team_id, user_id)
    
    if not history:
        return False
    
    # Check if the History text field contains the expected action
    latest_history_text = history[0].get('History', '').lower()
    return expected_action.lower() in latest_history_text

# create  method for select * from SchedulingGroupsTeamsLinks where schedulingteamid = 368
def getSchdGrpTeamLinks(scheduling_team_id: int) -> Dict[str, Any]:
    """Fetch the scheduling team links using hard‑coded SQL."""
    sql = """
        SELECT *
        FROM SchedulingGroupsTeamsLinks
        WHERE schedulingteamid = ?
    """
    results = execute_query(sql, [scheduling_team_id])
    return results if results else []



