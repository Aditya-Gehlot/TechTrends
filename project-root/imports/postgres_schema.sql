-- PostgreSQL schema and CSV copy examples for TechTrends market intelligence datasets.
-- Adjust file paths to your local environment before running.

CREATE SCHEMA IF NOT EXISTS techtrends;

CREATE TABLE IF NOT EXISTS techtrends.companies (
    company_id TEXT PRIMARY KEY,
    company TEXT,
    country TEXT,
    country_code TEXT,
    region TEXT,
    sector TEXT,
    stage TEXT,
    reference_type TEXT,
    dominant_topics TEXT
);

CREATE TABLE IF NOT EXISTS techtrends.linkedin_jobs (
    job_id TEXT PRIMARY KEY,
    posted_at TIMESTAMP,
    company TEXT,
    role TEXT,
    location TEXT,
    salary_usd NUMERIC,
    experience_years INT,
    skills TEXT,
    job_description TEXT,
    company_id TEXT,
    country TEXT,
    region TEXT,
    tech_category TEXT,
    hiring_index NUMERIC,
    funding_signal NUMERIC,
    sentiment_score NUMERIC,
    trend_score NUMERIC,
    popularity_growth_pct NUMERIC,
    volatility_metric NUMERIC,
    innovation_score NUMERIC,
    adoption_score NUMERIC,
    risk_indicator TEXT,
    source_platform TEXT
);

CREATE TABLE IF NOT EXISTS techtrends.twitter_stream (
    tweet_id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    username TEXT,
    followers BIGINT,
    tech_topic TEXT,
    sentiment TEXT,
    likes BIGINT,
    retweets BIGINT,
    content TEXT,
    company_id TEXT,
    company TEXT,
    country TEXT,
    region TEXT,
    trend_score NUMERIC,
    sentiment_score NUMERIC,
    funding_estimate_musd NUMERIC,
    hiring_activity_index NUMERIC,
    hashtags TEXT,
    popularity_growth_pct NUMERIC,
    volatility_metric NUMERIC,
    ai_summary TEXT,
    risk_indicator TEXT,
    innovation_score NUMERIC,
    adoption_score NUMERIC,
    source_reference TEXT
);

-- Repeat table patterns as needed for the other CSVs.
-- Example bulk load:
-- \copy techtrends.companies FROM 'Data/market_intel/companies.csv' CSV HEADER;
-- \copy techtrends.linkedin_jobs FROM 'Data/linkedin_jobs.csv' CSV HEADER;
-- \copy techtrends.twitter_stream FROM 'Data/twitter_stream.csv' CSV HEADER;
