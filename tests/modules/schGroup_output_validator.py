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


#select * from history where userid = 10201 and attributeid = 369 order by historyid desc
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



