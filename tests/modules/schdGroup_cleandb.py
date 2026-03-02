# Cleanup helpers for the scenario can live here.
from ..helpers.generic_query_helpers import execute_statement


def get_cleanup_sql(created_team_id: int) -> list:
    """Return cleanup SQL statements for removing test artifacts.

    Uses parameterized queries to prevent SQL injection.

    Args:
        created_team_id: The team ID to clean up

    Returns:
        List of tuples: (sql_with_placeholders, params_list)
    """
    return [
        ("DELETE FROM SchedulingGroupsTeamsLinks WHERE schedulingteamid = ?", [created_team_id]),
        ("DELETE FROM Exported_rota WHERE schedulingteamid = ?", [created_team_id]),
        ("DELETE FROM MasterRotas WHERE teamid = ?", [created_team_id]),
        ("DELETE FROM SchedulingTeams WHERE schedulingteamid = ?", [created_team_id])
    ]


def cleanup_scheduling_team(scheduling_team_id: int):
    """Execute cleanup for a scheduling team.

    Removes all test artifacts related to the given team ID.
    Uses parameterized queries to prevent SQL injection.
    Returns the count of rows deleted.
    """
    cleanup_sqls = get_cleanup_sql(scheduling_team_id)
    total_deleted = 0
    
    for sql, params in cleanup_sqls:
        try:
            affected = execute_statement(sql, params)
            total_deleted += affected
        except Exception as e:
            pass
    
    return total_deleted


