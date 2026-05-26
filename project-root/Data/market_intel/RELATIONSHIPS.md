# Dataset Relationships

```mermaid
erDiagram
    COMPANIES ||--o{ LINKEDIN_JOBS : company_id
    COMPANIES ||--o{ TWITTER_STREAM : company_id
    COMPANIES ||--o{ GITHUB_EVENTS : company_id
    COMPANIES ||--o{ TECH_BLOGS : company_id
    COMPANIES ||--o{ REDDIT_DISCUSSIONS : company_id
    COMPANIES ||--o{ HACKERNEWS_POSTS : company_id
    COMPANIES ||--o{ YOUTUBE_AI_CONTENT : company_id
    COMPANIES ||--o{ STARTUP_FUNDING : company_id
    COMPANIES ||--o{ PRODUCTHUNT_LAUNCHES : company_id
    COMPANIES ||--o{ NEWS_MEDIA_MENTIONS : company_id
    COMPANIES ||--o{ KAGGLE_ML_ACTIVITY : company_id
    MARKET_EVENTS }o--o{ GOOGLE_TRENDS : event_refs
    MARKET_EVENTS }o--o{ NEWS_MEDIA_MENTIONS : source_reference
```

Primary relationships:

- `company_id` is the core entity key across operational and social datasets.
- `tech_topic`, `topic`, `keyword`, and `tag` represent the same trend taxonomy at different source layers.
- `market_events.csv` encodes shock windows that influence trend spikes, sentiment shifts, volatility, hiring, and funding behavior.
- Funding and hiring are intentionally linked through company-level signals rather than strict one-to-one row joins.
