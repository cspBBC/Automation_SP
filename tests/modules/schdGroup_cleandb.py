# Cleanup helpers for the scenario can live here.
# This module intentionally minimal for now; extend as needed.
from ..helpers.generic_query_helpers import execute_query


def cleanup_scheduling_team(scheduling_team_id: int):
    """Remove test artifacts related to a scheduling team.

    Example cleanup SQL can be implemented here when required.
    """
    sql = """
        DELETE FROM SchedulingGroupsTeamsLinks WHERE schedulingteamid = ?
    """
    execute_query(sql, [scheduling_team_id])
