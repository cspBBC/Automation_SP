---
description: Describe when these instructions should be loaded
# applyTo: 'Describe when these instructions should be loaded' # when provided, instructions will automatically be added to the request context when the pattern matches an attached file
---

To acheive below artchitecture, using files of existing framework ONLY , no need to add extra logic or code files to the framework, just use the existing files and add the necessary code in those files to acheive the below architecture.

*** Title: High-Level Architecture

TEST FRAMEWORK

Components

Test Data (CSV/XLS)

Test Engine

Database Connector

SQL Server (Stored Procs)

Report Generator

HTML Reports

Flow (visual)
Test Data → Test Engine ↔ Database Connector → SQL Server
Test Engine ↓ Report Generator ↓ HTML Reports

Footer: © 2025 HCLTech | Confidential — HCLTech

Slide 3 — Detailed Component Architecture

Title: Detailed Component Architecture

Data Layer

Test Cases

Input Parameters

Expected Results

Data Loader Factory

CSV Loader

Excel Loader

JSON Loader

Test Engine Layer

Test Case Builder

Test Runner

Parameter Manager

Test Validator

Database Layer

Database Connection Manager

Connection Pool

Transaction Manager

Store Procedure Executor

Validation Layer

Result Validator

Return Code Validation

Row Count

Column Value Validator

Reporting Layer

HTML Reports

Report Output (Files/Emails)

Footer: © 2025 HCLTech | Confidential

Slide 4 — Test Execution Flow

Title: Test Execution Flow

Initial Steps

START

Load Configuration

Database.yaml

Test_config.yaml

Load Test Data

Test_cases.csv

Input_param.csv

expected_results.csv

Build Test Cases

Parse & validate data

Create test objects

Connect to Database

Establish connection pool

Verify connectivity

For Each Test Case

Begin Transaction

Prepare Parameters

Convert data types

Handle NULL values

Execute Stored Procedure

Call with parameters

Capture results

Capture errors

Validate Results

Return code

Row count

Column values

Output parameters

Record results

Rollback Transaction

Finalization

Aggregate Results

Calculate pass rate

Collect failures

Gather metrics

Generate Reports

HTML Reports

Send Notifications

Email Summary

Footer: © 2025 HCLTech | Confidential

End-to-End Flow Summary (Simplified)

Config + test data loaded

Test cases constructed

DB connection established

For each test

Start transaction

Prepare inputs

Execute stored procedure

Validate outputs

Record result

Rollback

Aggregate metrics

Generate HTML report

Send summary notification