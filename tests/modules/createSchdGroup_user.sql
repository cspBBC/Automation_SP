-- ensure a valid user exists for tests
-- this should match the real table used by the stored procedure
SELECT 1 FROM UserDetails WHERE UD_UserID = 10201
