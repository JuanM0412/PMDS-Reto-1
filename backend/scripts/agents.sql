-- =============================================================================
-- agents.sql
-- Schema creation script for the agents backend.
-- Run against a PostgreSQL database to set up all required tables.
-- =============================================================================

-- Create the dedicated schema
CREATE SCHEMA IF NOT EXISTS agents;

-- Drop table if it already exists (useful for local resets)
DROP TABLE IF EXISTS agents.agent_logs;

-- -------------------------------------------------------------------------
-- agents.agent_logs
-- Stores the result of each agent execution issued by the n8n pipeline.
-- One row is inserted every time n8n completes a step (including feedback
-- re-runs). The same (uuid, agent) pair can appear multiple times.
--
-- Columns
--   id            Serial primary key.
--   input         Original input or context sent to the agent.
--   uuid          Identifier for the user session / run (from the frontend).
--   agent         Pipeline step number, 1 through 6.
--   artefact      JSONB blob returned by n8n: {"artifact_type": [...data...]}.
--   justification Free-text justification provided by n8n upon flow completion.
--   added         JSON-encoded list of items added (from changes_made.added).
--   modified      JSON-encoded list of items modified (from changes_made.modified).
--   deleted       JSON-encoded list of items deleted (from changes_made.removed).
--   timestamp     UTC date-time when the record was created.
-- -------------------------------------------------------------------------
CREATE TABLE agents.agent_logs (
    id            SERIAL          PRIMARY KEY,
    input         TEXT            NOT NULL,
    uuid          VARCHAR(128)    NOT NULL,
    agent         INTEGER,
    artefact      JSONB           NOT NULL,
    justification TEXT,
    added         TEXT,
    modified      TEXT,
    deleted       TEXT,
    timestamp     TIMESTAMP       NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- Indexes for common query patterns
CREATE INDEX idx_agent_logs_uuid          ON agents.agent_logs (uuid);
CREATE INDEX idx_agent_logs_uuid_agent    ON agents.agent_logs (uuid, agent);
CREATE INDEX idx_agent_logs_timestamp     ON agents.agent_logs (timestamp DESC);
