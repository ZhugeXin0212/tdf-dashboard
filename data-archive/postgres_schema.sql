-- ============================================================
-- Postgres schema for the Tour de France Dashboard (cloud deployment)
-- These are the 10 FINAL output tables (not the 3 raw staging tables
-- riders/results/exits from schema.sql). Each table's data is loaded
-- directly from the corresponding CSV file in table/, which has
-- already been verified against the SQLite derivation logic in
-- schema.sql.
-- ============================================================

DROP TABLE IF EXISTS gc_standing;
DROP TABLE IF EXISTS award_team;
DROP TABLE IF EXISTS award_ind;
DROP TABLE IF EXISTS exit_record;
DROP TABLE IF EXISTS result;
DROP TABLE IF EXISTS stage;
DROP TABLE IF EXISTS location;
DROP TABLE IF EXISTS rider;
DROP TABLE IF EXISTS team;
DROP TABLE IF EXISTS country;

-- COUNTRY: identified by ISO 3166-1 alpha-3 code
CREATE TABLE country (
    country_code CHAR(3) PRIMARY KEY,
    country_name VARCHAR(60)
);

-- TEAM: identified by team name, belongs to exactly one country
CREATE TABLE team (
    team VARCHAR(50) PRIMARY KEY,
    team_country_code CHAR(3) REFERENCES country(country_code),
    leader_bib INTEGER
);

-- RIDER: identified by bib number, belongs to one team and one country
CREATE TABLE rider (
    bib INTEGER PRIMARY KEY,
    rider_name VARCHAR(50),
    dob DATE,
    team VARCHAR(50) REFERENCES team(team),
    rider_country_code CHAR(3) REFERENCES country(country_code)
);

-- LOCATION: start/finish location name, only locations used in a stage
CREATE TABLE location (
    location VARCHAR(30) PRIMARY KEY
);

-- STAGE: one row per race day
CREATE TABLE stage (
    stage_id INTEGER PRIMARY KEY,
    day DATE,
    type VARCHAR(25),
    length NUMERIC(5,1),
    start_location VARCHAR(30) REFERENCES location(location),
    finish_location VARCHAR(30) REFERENCES location(location)
);

-- RESULT: one row per rider per stage completed
CREATE TABLE result (
    day DATE,
    rank INTEGER,
    bib INTEGER REFERENCES rider(bib),
    time INTEGER,
    bonus INTEGER,
    penalty INTEGER,
    PRIMARY KEY (day, bib)
);

-- EXIT_RECORD: rider withdrawal events (named exit_record instead of
-- EXIT, since EXIT is a reserved-adjacent keyword in some Postgres
-- tooling, so exit_record avoids any ambiguity)
CREATE TABLE exit_record (
    bib INTEGER REFERENCES rider(bib),
    stage_id INTEGER REFERENCES stage(stage_id),
    reason VARCHAR(15)
);

-- AWARD_IND: General Classification final ranking (riders who
-- completed all 21 stages)
CREATE TABLE award_ind (
    rank INTEGER,
    bib INTEGER REFERENCES rider(bib),
    adjusted_time INTEGER
);

-- AWARD_TEAM: Best Team award final ranking
CREATE TABLE award_team (
    team VARCHAR(50) REFERENCES team(team),
    aggregate_time INTEGER,
    rank INTEGER
);

-- GC_STANDING: daily cumulative GC standing after each completed stage
-- (supports stage-by-stage cumulative trend analysis in the dashboard)
CREATE TABLE gc_standing (
    day DATE,
    bib INTEGER REFERENCES rider(bib),
    cumulative_time INTEGER,
    gc_rank INTEGER,
    PRIMARY KEY (day, bib)
);
