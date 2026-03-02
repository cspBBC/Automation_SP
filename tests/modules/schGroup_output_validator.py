from ..helpers.generic_query_helpers import execute_query
from typing import Dict, Any


# scenario-specific wrappers -------------------------------------------------

def getSchdGrpDetails(scheduling_team_id: int) -> Dict[str, Any]:
    """Fetch the scheduling-team row using hard‑coded SQL.

    The query resides here so that test modules only depend on a single
    function.  ``generic_query_helpers`` merely runs whatever SQL it is given
    and returns the result as a list of dicts.
    """
    print(f"\n[getSchdGrpDetails] Querying team details...")
    sql = """
        SELECT *
        FROM SchedulingTeams
        WHERE schedulingteamid = ?
    """
    print(f"  Params: [{scheduling_team_id}]")
    results = execute_query(sql, [scheduling_team_id])
    print(f"  Result count: {len(results)}")
    if results:
        row = results[0]
        print(f"  Columns: {list(row.keys())}")
        print(f"  Key fields: schedulingTeamId={row.get('schedulingTeamId')}, schedulingTeamName={row.get('schedulingTeamName')}, isActive={row.get('isActive')}")
    return results[0] if results else {}



def validateSchdGrpActive(scheduling_team_id: int) -> bool:
    """Return ``True`` if the scheduling team is active.

    Uses hard‑coded SQL to check the isActive column for the given team ID.
    """
    print(f"\n[validateSchdGrpActive] Checking active flag...")
    sql = """
        SELECT isActive
        FROM SchedulingTeams
        WHERE schedulingteamid = ?
    """
    print(f"  Params: [{scheduling_team_id}]")
    results = execute_query(sql, [scheduling_team_id])
    print(f"  Result count: {len(results)}")
    if results:
        is_active = results[0].get('isActive', False) == 1
        print(f"  isActive value: {results[0].get('isActive', 'NULL')}")
        print(f"  Result: {'ACTIVE (1)' if is_active else 'INACTIVE (0)'}")
        return is_active
    print(f"  Result: NOT FOUND")
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
    print(f"\n[getSchdGrpHistory] Querying history records...")
    sql = """
        SELECT *
        FROM History
        WHERE userid = ? AND attributeid = ?
        ORDER BY historyid DESC
    """
    print(f"  Params: [user_id={user_id}, team_id={scheduling_team_id}]")
    results = execute_query(sql, [user_id, scheduling_team_id])
    print(f"  Result count: {len(results)}")
    if results:
        # show the keys we received so callers can understand column names
        print(f"  Row keys: {list(results[0].keys())}")
    for idx, row in enumerate(results):
        # case-insensitive access for columns that may vary in casing
        hid = row.get('HistoryID') if 'HistoryID' in row else row.get('historyid')
        datetime_val = row.get('DateTime') if 'DateTime' in row else row.get('datetime')
        history_text = row.get('History') if 'History' in row else row.get('history', '')
        print(f"    [{idx}] HistoryID={hid}, DateTime={datetime_val}, Text={history_text[:100]}...")
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
    print(f"\n[validateSchdGrpHistoryExists] Validating history count...")
    history = getSchdGrpHistory(scheduling_team_id, user_id)
    
    if not history:
        print(f"  Result: FAILED - No history records found")
        return False
    
    print(f"  Found {len(history)} record(s)")
    if expected_count is not None:
        match = len(history) == expected_count
        print(f"  Expected count: {expected_count}, Actual: {len(history)}, Result: {'PASS' if match else 'FAIL'}")
        return match
    
    print(f"  Result: PASS - History exists")
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
    print(f"\n[validateSchdGrpHistoryAction] Validating history action...")
    history = getSchdGrpHistory(scheduling_team_id, user_id)
    
    if not history:
        print(f"  Result: FAILED - No history records found")
        return False
    
    # Check if the History text field contains the expected action (case-insensitive key)
    latest_row = history[0]
    latest_history_text = latest_row.get('History') if 'History' in latest_row else latest_row.get('history', '')
    latest_history_text = latest_history_text.lower()
    expected_action_lower = expected_action.lower()
    match = expected_action_lower in latest_history_text
    print(f"  Looking for: '{expected_action}'")
    print(f"  Latest history: {latest_history_text[:150]}...")
    print(f"  Result: {'PASS' if match else 'FAIL'}")
    return match

# create  method for select * from SchedulingGroupsTeamsLinks where schedulingteamid = 368
def getSchdGrpTeamLinks(scheduling_team_id: int) -> Dict[str, Any]:
    """Fetch the scheduling team links using hard‑coded SQL."""
    print(f"\n[getSchdGrpTeamLinks] Querying team links...")
    sql = """
        SELECT *
        FROM SchedulingGroupsTeamsLinks
        WHERE schedulingteamid = ?
    """
    print(f"  Params: [{scheduling_team_id}]")
    results = execute_query(sql, [scheduling_team_id])
    print(f"  Result count: {len(results)}")
    for idx, row in enumerate(results):
        print(f"    [{idx}] {row}")
    return results if results else []



