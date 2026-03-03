"""Scheduling Group Validators - Validators for scheduling team tests."""

from validation_layer.generic_validators import execute_query
from typing import Dict, Any, List


class _SimpleLogger:
    def info(self, msg, *args, **kwargs):
        try:
            print(msg % args)
        except Exception:
            print(msg, args)

    def debug(self, msg, *args, **kwargs):
        try:
            print(msg % args)
        except Exception:
            print(msg, args)

    def warning(self, msg, *args, **kwargs):
        try:
            print(msg % args)
        except Exception:
            print(msg, args)


logger = _SimpleLogger()


def getSchdGrpDetails(scheduling_team_id: int) -> Dict[str, Any]:
    """Fetch the scheduling-team row using hard‑coded SQL."""
    logger.info("[getSchdGrpDetails] Querying team details...")
    sql = """
        SELECT *
        FROM SchedulingTeams
        WHERE schedulingteamid = ?
    """
    logger.debug("  Params: [%s]", scheduling_team_id)
    results = execute_query(sql, [scheduling_team_id])
    logger.debug("  Result count: %d", len(results))
    if results:
        row = results[0]
        logger.debug("  Columns: %s", list(row.keys()))
        logger.info("  Key fields: schedulingTeamId=%s, schedulingTeamName=%s, isActive=%s",
                    row.get('schedulingTeamId'), row.get('schedulingTeamName'), row.get('isActive'))
    return results[0] if results else {}


def validateSchdGrpActive(scheduling_team_id: int) -> bool:
    """Return ``True`` if the scheduling team is active."""
    logger.info("[validateSchdGrpActive] Checking active flag...")
    sql = """
        SELECT isActive
        FROM SchedulingTeams
        WHERE schedulingteamid = ?
    """
    logger.debug("  Params: [%s]", scheduling_team_id)
    results = execute_query(sql, [scheduling_team_id])
    logger.debug("  Result count: %d", len(results))
    if results:
        is_active = results[0].get('isActive', False) == 1
        logger.debug("  isActive value: %s", results[0].get('isActive', 'NULL'))
        logger.info("  Result: %s", 'ACTIVE (1)' if is_active else 'INACTIVE (0)')
        return is_active
    logger.info("  Result: NOT FOUND")
    return False


def getSchdGrpHistory(scheduling_team_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Fetch history records for a scheduling team."""
    logger.info("[getSchdGrpHistory] Querying history records...")
    sql = """
        SELECT *
        FROM History
        WHERE userid = ? AND attributeid = ?
        ORDER BY historyid DESC
    """
    logger.debug("  Params: [user_id=%s, team_id=%s]", user_id, scheduling_team_id)
    results = execute_query(sql, [user_id, scheduling_team_id])
    logger.debug("  Result count: %d", len(results))
    if not results:
        return []

    logger.debug("  Row keys: %s", list(results[0].keys()))

    normalized: List[Dict[str, Any]] = []
    for idx, raw_row in enumerate(results):
        # make a mutable copy
        row = dict(raw_row)
        hid = row.get('HistoryID') if 'HistoryID' in row else row.get('historyid')
        datetime_val = row.get('DateTime') if 'DateTime' in row else row.get('datetime')
        history_text = row.get('History') if 'History' in row else row.get('history', '') or ''

        # heuristics to detect operation type from history text or type fields
        op = None
        htext = history_text.lower()
        if 'created by' in htext or 'created on' in htext:
            op = 'create'
        elif 'record updated' in htext or 'changed from' in htext or 'record upd' in htext or 'updated by' in htext:
            op = 'edit'
        else:
            # fall back to explicit type/subtype fields if present
            ht = (row.get('HistoryType') or row.get('historytype') or '')
            hst = (row.get('HistorySubType') or row.get('historysubtype') or '')
            combined = f"{ht}".lower() + f"/{hst}".lower()
            if 'create' in combined:
                op = 'create'
            elif 'edit' in combined or 'update' in combined:
                op = 'edit'
            else:
                op = 'unknown'

        row['operation'] = op
        normalized.append(row)

        logger.info("    [%d] HistoryID=%s, DateTime=%s, Operation=%s, Text=%s...", idx, hid, datetime_val, op, history_text[:100])

    return normalized


def validateSchdGrpHistoryExists(scheduling_team_id: int, user_id: int, expected_count: int = None) -> bool:
    """Validate that history records exist for a scheduling team."""
    logger.info("[validateSchdGrpHistoryExists] Validating history count...")
    history = getSchdGrpHistory(scheduling_team_id, user_id)
    
    if not history:
        logger.warning("  Result: FAILED - No history records found")
        return False
    
    logger.info("  Found %d record(s)", len(history))
    if expected_count is not None:
        match = len(history) == expected_count
        logger.info("  Expected count: %s, Actual: %d, Result: %s", expected_count, len(history), 'PASS' if match else 'FAIL')
        return match
    
    logger.info("  Result: PASS - History exists")
    return len(history) > 0


def validateSchdGrpHistoryAction(scheduling_team_id: int, user_id: int, expected_action: str) -> bool:
    """Validate that the most recent history record has a specific action."""
    logger.info("[validateSchdGrpHistoryAction] Validating history action...")
    history = getSchdGrpHistory(scheduling_team_id, user_id)
    
    if not history:
        logger.warning("  Result: FAILED - No history records found")
        return False
    
    latest_row = history[0]
    latest_history_text = latest_row.get('History') if 'History' in latest_row else latest_row.get('history', '')
    latest_history_text = (latest_history_text or '').lower()
    expected_action_lower = expected_action.lower()
    match = expected_action_lower in latest_history_text
    logger.info("  Looking for: '%s'", expected_action)
    logger.debug("  Latest history: %s...", latest_history_text[:150])
    logger.info("  Result: %s", 'PASS' if match else 'FAIL')
    return match


def getSchdGrpTeamLinks(scheduling_team_id: int) -> List[Dict[str, Any]]:
    """Fetch the scheduling team links using hard‑coded SQL."""
    logger.info("[getSchdGrpTeamLinks] Querying team links...")
    sql = """
        SELECT *
        FROM SchedulingGroupsTeamsLinks
        WHERE schedulingteamid = ?
    """
    logger.debug("  Params: [%s]", scheduling_team_id)
    results = execute_query(sql, [scheduling_team_id])
    logger.debug("  Result count: %d", len(results))
    for idx, row in enumerate(results):
        logger.info("    [%d] %s", idx, row)
    return results if results else []


def validateUserCanAccessTeam(scheduling_team_id: int, user_id: int, user_division_id: int = None) -> bool:
    """Validate that a user has permission to access a scheduling team."""
    logger.info("[validateUserCanAccessTeam] Checking access for user %s to team %s...", user_id, scheduling_team_id)
    if user_division_id:
        logger.debug("  User division restriction: %s", user_division_id)
    
    sql = """
        SELECT t.SchedulingTeamID
        FROM SchedulingTeams t
        LEFT JOIN Divisions d ON d.DivisionID = t.DivisionID
        WHERE t.SchedulingTeamID = ?
          AND (
              t.CreatedBy = ?
              OR EXISTS (
                  SELECT 1
                  FROM UserRoles r
                  INNER JOIN Divisions d2 ON d2.DivisionID = r.UR_DivisionId
                  WHERE r.UR_UserID = ?
                    AND r.UR_EndDate >= CAST(GETDATE() AS DATE)
                    AND (r.UR_RoleID = 1 OR d2.DivisionID = t.DivisionID)
              )
          )
    """
    logger.debug("  Params: [team_id=%s, user_id=%s]", scheduling_team_id, user_id)
    results = execute_query(sql, [scheduling_team_id, user_id, user_id])
    logger.debug("  Result count: %d", len(results))
    can_access = len(results) > 0
    logger.info("  Result: %s", 'CAN ACCESS' if can_access else 'CANNOT ACCESS')
    return can_access
