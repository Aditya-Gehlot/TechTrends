# Market Intelligence Dataset Catalog

This catalog documents the synthetic datasets generated for TechTrends. The data is designed to be CSV-ready and realistic enough for analytics, reporting, and ML prototyping while remaining synthetic.

## linkedin_jobs.csv

Rows: `26723`

### Schema

| Field | Description |
|---|---|
| `job_id` | Unique job posting identifier |
| `posted_at` | Posting timestamp |
| `company_id` | Cross-dataset company key |
| `company` | Employer or startup name |
| `role` | Job title |
| `location` | City |
| `country` | Country name |
| `salary_usd` | Estimated annual compensation in USD |
| `skills` | Comma-separated skills and tools |
| `tech_category` | Primary technology trend represented by the role |
| `hiring_index` | Hiring demand proxy influenced by market conditions |
| `risk_indicator` | Operational or market risk label |

### Sample Records

```json
[
  {
    "job_id": "JOB-100000",
    "posted_at": "2025-01-02T08:00:00",
    "company": "OpenAI",
    "role": "Applied Scientist",
    "location": "Austin",
    "salary_usd": 194784.0,
    "experience_years": 9,
    "skills": "Prompt Engineering, Inference, Serving, PyTorch, Diffusion",
    "job_description": "OpenAI is hiring a Applied Scientist in Austin to scale generative ai initiatives across enterprise and developer workflows. The team is focused on data platform integration while supporting regional go-to-market launches. Candidates should be comfortable with Prompt Engineering, Inference, Serving and cross-functional delivery in a fast-moving market.",
    "company_id": "CMP-001",
    "country": "United States",
    "region": "North America",
    "tech_category": "Generative AI",
    "hiring_index": 71.47,
    "funding_signal": 1.13,
    "sentiment_score": 0.189,
    "trend_score": 55.68,
    "popularity_growth_pct": -1.31,
    "volatility_metric": 8.96,
    "innovation_score": 88.07,
    "adoption_score": 69.1,
    "risk_indicator": "low",
    "source_platform": "LinkedIn"
  },
  {
    "job_id": "JOB-100001",
    "posted_at": "2025-01-03T10:00:00",
    "company": "OpenAI",
    "role": "LLM Engineer",
    "location": "San Francisco",
    "salary_usd": 157323.0,
    "experience_years": 3,
    "skills": "Tokenization, Fine-tuning, Transformers, Evaluation, PyTorch",
    "job_description": "OpenAI is hiring a LLM Engineer in San Francisco to scale llm initiatives across enterprise and developer workflows. The team is focused on global availability while supporting internal platform teams. Candidates should be comfortable with Tokenization, Fine-tuning, Transformers and cross-functional delivery in a fast-moving market.",
    "company_id": "CMP-001",
    "country": "United States",
    "region": "North America",
    "tech_category": "LLM",
    "hiring_index": 68.65,
    "funding_signal": 1.13,
    "sentiment_score": 0.157,
    "trend_score": 53.52,
    "popularity_growth_pct": -3.54,
    "volatility_metric": 8.54,
    "innovation_score": 90.9,
    "adoption_score": 75.96,
    "risk_indicator": "low",
    "source_platform": "LinkedIn"
  }
]
```

### Expected Analytics Usage

- hiring trend dashboards
- regional salary benchmarking
- funding-to-hiring lag analysis

### Suggested ML Use-Cases

- hiring demand forecasting
- salary regression
- location recommendation

## twitter_stream.csv

Rows: `26789`

### Schema

| Field | Description |
|---|---|
| `tweet_id` | Unique social post identifier |
| `created_at` | Tweet timestamp |
| `tech_topic` | Primary technology topic |
| `company_id` | Referenced company |
| `followers` | Audience size of author |
| `likes` | Engagement count |
| `retweets` | Reshare count |
| `sentiment_score` | Continuous sentiment signal |
| `volatility_metric` | Daily instability proxy |
| `ai_summary` | Generated digest of conversation context |

### Sample Records

```json
[
  {
    "tweet_id": "TWT-200000",
    "created_at": "2025-01-01T05:19:00",
    "username": "model_51932",
    "followers": 128570,
    "tech_topic": "AI Agents",
    "sentiment": "positive",
    "likes": 5089,
    "retweets": 1140,
    "content": "Windsurf keeps showing up in AI Agents discussions as teams focus on developer adoption. #AIAgents #UK #windsurf",
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United Kingdom",
    "region": "Europe",
    "trend_score": 49.96,
    "sentiment_score": 0.393,
    "funding_estimate_musd": 176.79,
    "hiring_activity_index": 52.73,
    "hashtags": "#AIAgents|#UK|#windsurf",
    "popularity_growth_pct": 3.82,
    "volatility_metric": 9.43,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "moderate",
    "innovation_score": 88.9,
    "adoption_score": 65.28,
    "source_reference": "https://x.example.com/CMP-015/200000"
  },
  {
    "tweet_id": "TWT-200001",
    "created_at": "2025-01-01T21:38:00",
    "username": "agent_92460",
    "followers": 23247,
    "tech_topic": "AI Agents",
    "sentiment": "positive",
    "likes": 2696,
    "retweets": 1086,
    "content": "Replit keeps showing up in AI Agents discussions as teams focus on agent quality. #AIAgents #CN #replit",
    "company_id": "CMP-014",
    "company": "Replit",
    "country": "China",
    "region": "Asia",
    "trend_score": 44.14,
    "sentiment_score": 0.206,
    "funding_estimate_musd": 163.46,
    "hiring_activity_index": 45.68,
    "hashtags": "#AIAgents|#CN|#replit",
    "popularity_growth_pct": 4.51,
    "volatility_metric": 8.73,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "low",
    "innovation_score": 93.37,
    "adoption_score": 66.21,
    "source_reference": "https://x.example.com/CMP-014/200001"
  }
]
```

### Expected Analytics Usage

- sentiment and buzz monitoring
- trend spike detection
- regional share-of-voice reporting

### Suggested ML Use-Cases

- sentiment classification
- engagement prediction
- duplicate detection

## github_events.csv

Rows: `16090`

### Schema

| Field | Description |
|---|---|
| `event_id` | Unique repository activity identifier |
| `event_time` | Event date |
| `repository` | Repository slug |
| `language` | Main implementation language |
| `stars_added` | Stars gained on event day |
| `forks_added` | Forks gained on event day |
| `contributors` | Estimated contributor count |
| `topic` | Mapped technology trend |

### Sample Records

```json
[
  {
    "event_id": "GIT-300000",
    "event_time": "2025-01-01T00:00:00",
    "repository": "openai/ai-agents-platform",
    "language": "Python",
    "stars_added": 343,
    "forks_added": 125,
    "contributors": 22,
    "topic": "AI Agents",
    "event_type": "push",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "region": "North America",
    "issue_count": 17,
    "watchers_added": 58,
    "release_flag": false,
    "trend_score": 56.34,
    "popularity_growth_pct": 1.37,
    "volatility_metric": 7.67,
    "innovation_score": 88.7,
    "adoption_score": 69.08,
    "risk_indicator": "low",
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption."
  },
  {
    "event_id": "GIT-300001",
    "event_time": "2025-01-01T00:00:00",
    "repository": "openai/llm-sdk",
    "language": "Python",
    "stars_added": 346,
    "forks_added": 169,
    "contributors": 10,
    "topic": "LLM",
    "event_type": "push",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "region": "North America",
    "issue_count": 7,
    "watchers_added": 91,
    "release_flag": false,
    "trend_score": 56.34,
    "popularity_growth_pct": 1.37,
    "volatility_metric": 7.67,
    "innovation_score": 88.7,
    "adoption_score": 69.08,
    "risk_indicator": "low",
    "ai_summary": "Developers are comparing tooling choices around llm as budget owners ask for faster ROI and clearer governance. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption."
  }
]
```

### Expected Analytics Usage

- open-source momentum scoring
- repo health analysis
- developer ecosystem correlation studies

### Suggested ML Use-Cases

- star/fork growth modeling
- repo anomaly detection
- topic popularity forecasting

## tech_blogs.csv

Rows: `5592`

### Schema

| Field | Description |
|---|---|
| `article_id` | Unique article identifier |
| `published_at` | Publication timestamp |
| `source` | Blog platform or publication |
| `topic` | Primary theme |
| `title` | Article headline |
| `views` | Estimated article views |
| `summary` | Article summary text |

### Sample Records

```json
[
  {
    "article_id": "ART-400000",
    "published_at": "2025-01-01T00:00:00",
    "source": "InfoQ",
    "author": "Maya Patel",
    "topic": "AI Agents",
    "title": "AI Agents developer demand in 2025: what Windsurf signals imply",
    "views": 68343,
    "reading_time_minutes": 8,
    "summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United Arab Emirates",
    "region": "Middle East",
    "trend_score": 42.71,
    "sentiment_score": 0.176,
    "funding_estimate_musd": 45.94,
    "hiring_activity_index": 60.08,
    "hashtags": "#aiagents|#AE",
    "popularity_growth_pct": 2.71,
    "volatility_metric": 7.42,
    "risk_indicator": "low",
    "innovation_score": 91.14,
    "adoption_score": 71.66,
    "source_reference": "https://blog.example.com/400000"
  },
  {
    "article_id": "ART-400001",
    "published_at": "2025-01-04T00:00:00",
    "source": "Engineering Blog",
    "author": "Ava Tanaka",
    "topic": "AI Agents",
    "title": "AI Agents open-source momentum in 2025: what Anthropic signals imply",
    "views": 27928,
    "reading_time_minutes": 5,
    "summary": "Anthropic teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "company_id": "CMP-002",
    "company": "Anthropic",
    "country": "France",
    "region": "Europe",
    "trend_score": 41.86,
    "sentiment_score": 0.328,
    "funding_estimate_musd": 30.63,
    "hiring_activity_index": 52.38,
    "hashtags": "#aiagents|#FR",
    "popularity_growth_pct": 2.36,
    "volatility_metric": 7.45,
    "risk_indicator": "low",
    "innovation_score": 91.98,
    "adoption_score": 61.34,
    "source_reference": "https://blog.example.com/400001"
  }
]
```

### Expected Analytics Usage

- content engagement dashboards
- topic narrative analysis
- innovation storytelling analysis

### Suggested ML Use-Cases

- summary quality ranking
- topic classification
- engagement prediction

## stackoverflow_questions.csv

Rows: `8945`

### Schema

| Field | Description |
|---|---|
| `question_id` | Question identifier |
| `created_at` | Question timestamp |
| `tag` | Primary technical tag |
| `views` | Question views |
| `answers` | Answer count |
| `accepted_answer` | Whether accepted solution exists |

### Sample Records

```json
[
  {
    "question_id": "SO-500000",
    "created_at": "2025-01-01T00:00:00",
    "tag": "AI Agents",
    "views": 5434,
    "answers": 11,
    "score": 56,
    "accepted_answer": false,
    "title": "Best production pattern for AI Agents with Replit stack?",
    "body_preview": "Our team is deploying ai agents workloads and seeing issues around throughput. We use components similar to Replit and need guidance for production-ready patterns.",
    "company_id": "CMP-014",
    "company": "Replit",
    "country": "India",
    "trend_score": 43.61,
    "sentiment_score": 0.274,
    "popularity_growth_pct": 1.38,
    "volatility_metric": 7.09,
    "innovation_score": 88.51,
    "adoption_score": 67.29,
    "risk_indicator": "low",
    "source_reference": "https://stackoverflow.example.com/questions/500000"
  },
  {
    "question_id": "SO-500001",
    "created_at": "2025-01-01T00:00:00",
    "tag": "AI Agents",
    "views": 4618,
    "answers": 8,
    "score": 29,
    "accepted_answer": false,
    "title": "How to scale AI Agents workloads without runaway cost?",
    "body_preview": "Our team is deploying ai agents workloads and seeing issues around latency. We use components similar to Anthropic and need guidance for production-ready patterns.",
    "company_id": "CMP-002",
    "company": "Anthropic",
    "country": "Germany",
    "trend_score": 43.62,
    "sentiment_score": 0.016,
    "popularity_growth_pct": 3.89,
    "volatility_metric": 7.67,
    "innovation_score": 94.6,
    "adoption_score": 67.77,
    "risk_indicator": "low",
    "source_reference": "https://stackoverflow.example.com/questions/500001"
  }
]
```

### Expected Analytics Usage

- developer pain-point analysis
- question volume forecasting
- support burden estimation

### Suggested ML Use-Cases

- answer likelihood prediction
- topic difficulty clustering
- support load forecasting

## google_trends.csv

Rows: `97000`

### Schema

| Field | Description |
|---|---|
| `date` | Daily trend observation date |
| `keyword` | Tracked topic keyword |
| `trend_score` | Normalized interest score |
| `region` | Country code |
| `popularity_growth_pct` | Day-over-day growth |

### Sample Records

```json
[
  {
    "date": "2025-01-01",
    "keyword": "AI Agents",
    "trend_score": 48,
    "region": "US",
    "country": "United States",
    "tech_category": "AI Agents",
    "sentiment_score": 0.132,
    "popularity_growth_pct": 0.64,
    "volatility_metric": 6.77,
    "innovation_score": 89.73,
    "adoption_score": 63.67,
    "risk_indicator": "low",
    "event_refs": ""
  },
  {
    "date": "2025-01-01",
    "keyword": "AI Agents",
    "trend_score": 44,
    "region": "IN",
    "country": "India",
    "tech_category": "AI Agents",
    "sentiment_score": 0.274,
    "popularity_growth_pct": 1.38,
    "volatility_metric": 7.09,
    "innovation_score": 88.51,
    "adoption_score": 67.29,
    "risk_indicator": "low",
    "event_refs": ""
  }
]
```

### Expected Analytics Usage

- time-series trend dashboards
- market seasonality analysis
- country-level momentum comparison

### Suggested ML Use-Cases

- multivariate time-series forecasting
- changepoint detection
- volatility classification

## reddit_discussions.csv

Rows: `12531`

### Schema

| Field | Description |
|---|---|
| `reddit_post_id` | Discussion identifier |
| `subreddit` | Source community |
| `upvotes` | Community endorsement count |
| `comments` | Reply count |
| `company_id` | Referenced company |

### Sample Records

```json
[
  {
    "reddit_post_id": "RDT-600000",
    "created_at": "2025-01-01T14:12:00",
    "subreddit": "r/artificial",
    "username": "agent_90206",
    "topic": "AI Agents",
    "title": "Is AI Agents still underhyped or already overheating?",
    "body": "Seeing more teams mention AgentForge whenever ai agents comes up. Feels like adoption is real in China, but the debate around security keeps resurfacing.",
    "upvotes": 830,
    "comments": 163,
    "sentiment_score": 0.15,
    "company_id": "CMP-031",
    "company": "AgentForge",
    "country": "China",
    "region": "Asia",
    "trend_score": 44.14,
    "funding_estimate_musd": 31.81,
    "hiring_activity_index": 37.98,
    "hashtags": "#aiagents|#CN",
    "popularity_growth_pct": 4.51,
    "volatility_metric": 8.73,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "low",
    "innovation_score": 93.37,
    "adoption_score": 66.21,
    "source_reference": "https://reddit.example.com/600000"
  },
  {
    "reddit_post_id": "RDT-600001",
    "created_at": "2025-01-05T16:18:00",
    "subreddit": "r/datascience",
    "username": "cloud_60551",
    "topic": "AI Agents",
    "title": "Is AI Agents still underhyped or already overheating?",
    "body": "Seeing more teams mention Anthropic whenever ai agents comes up. Feels like adoption is real in Singapore, but the debate around moats keeps resurfacing.",
    "upvotes": 829,
    "comments": 194,
    "sentiment_score": 0.252,
    "company_id": "CMP-002",
    "company": "Anthropic",
    "country": "Singapore",
    "region": "Asia",
    "trend_score": 46.78,
    "funding_estimate_musd": 13.95,
    "hiring_activity_index": 42.72,
    "hashtags": "#aiagents|#SG",
    "popularity_growth_pct": -0.03,
    "volatility_metric": 6.05,
    "ai_summary": "Developers are comparing tooling choices around ai agents as budget owners ask for faster ROI and clearer governance. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "low",
    "innovation_score": 90.32,
    "adoption_score": 66.45,
    "source_reference": "https://reddit.example.com/600001"
  }
]
```

### Expected Analytics Usage

- community sentiment mining
- hype-cycle monitoring
- anomaly detection on discussion bursts

### Suggested ML Use-Cases

- stance detection
- community segmentation
- engagement forecasting

## hackernews_posts.csv

Rows: `775`

### Schema

| Field | Description |
|---|---|
| `hn_post_id` | HN item identifier |
| `title` | Story title |
| `points` | HN points |
| `comments` | HN comment count |

### Sample Records

```json
[
  {
    "hn_post_id": "HN-700000",
    "created_at": "2025-01-01T14:00:00",
    "title": "AgentForge and the new economics of ai agents",
    "domain": "snowflake.com",
    "topic": "AI Agents",
    "points": 181,
    "comments": 57,
    "company_id": "CMP-031",
    "company": "AgentForge",
    "country": "United States",
    "trend_score": 47.96,
    "sentiment_score": 0.086,
    "popularity_growth_pct": 0.64,
    "volatility_metric": 6.77,
    "innovation_score": 89.73,
    "adoption_score": 63.67,
    "risk_indicator": "low",
    "ai_summary": "Developers are comparing tooling choices around ai agents as budget owners ask for faster ROI and clearer governance. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://news.ycombinator.com/item?id=700000"
  },
  {
    "hn_post_id": "HN-700001",
    "created_at": "2025-01-03T20:00:00",
    "title": "Windsurf and the new economics of ai agents",
    "domain": "snowflake.com",
    "topic": "AI Agents",
    "points": 191,
    "comments": 86,
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United States",
    "trend_score": 45.54,
    "sentiment_score": 0.026,
    "popularity_growth_pct": 0.87,
    "volatility_metric": 8.28,
    "innovation_score": 96.64,
    "adoption_score": 73.65,
    "risk_indicator": "low",
    "ai_summary": "Windsurf teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://news.ycombinator.com/item?id=700001"
  }
]
```

### Expected Analytics Usage

- early technical attention tracking
- influencer-domain analysis

### Suggested ML Use-Cases

- story ranking
- comment volume forecasting

## youtube_ai_content.csv

Rows: `3393`

### Schema

| Field | Description |
|---|---|
| `video_id` | Video identifier |
| `channel` | Channel name |
| `views` | Video views |
| `watch_time_minutes` | Estimated aggregate watch time |

### Sample Records

```json
[
  {
    "video_id": "YT-800000",
    "published_at": "2025-01-02T19:00:00",
    "channel": "Cloud Native Bytes",
    "topic": "AI Agents",
    "company_id": "CMP-009",
    "company": "Scale AI",
    "title": "AI Agents market update: what Scale AI says about 2026 demand",
    "views": 80638,
    "likes": 5625,
    "comments": 716,
    "watch_time_minutes": 89424,
    "country": "United Kingdom",
    "sentiment_score": 0.535,
    "trend_score": 46.55,
    "funding_estimate_musd": 8.39,
    "hiring_activity_index": 38.73,
    "hashtags": "#aiagents|#AI|#UK",
    "popularity_growth_pct": -6.83,
    "volatility_metric": 9.54,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 02, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "moderate",
    "innovation_score": 92.27,
    "adoption_score": 64.83,
    "source_reference": "https://youtube.example.com/watch?v=800000"
  },
  {
    "video_id": "YT-800001",
    "published_at": "2025-01-02T17:00:00",
    "channel": "Machine Learning Street Talk",
    "topic": "AI Agents",
    "company_id": "CMP-009",
    "company": "Scale AI",
    "title": "AI Agents market update: what Scale AI says about 2026 demand",
    "views": 39701,
    "likes": 2218,
    "comments": 260,
    "watch_time_minutes": 92037,
    "country": "France",
    "sentiment_score": 0.191,
    "trend_score": 44.43,
    "funding_estimate_musd": 28.24,
    "hiring_activity_index": 36.26,
    "hashtags": "#aiagents|#AI|#FR",
    "popularity_growth_pct": 1.25,
    "volatility_metric": 9.41,
    "ai_summary": "Scale AI teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "moderate",
    "innovation_score": 94.79,
    "adoption_score": 69.42,
    "source_reference": "https://youtube.example.com/watch?v=800001"
  }
]
```

### Expected Analytics Usage

- creator economy analysis
- education demand tracking
- topic attention mix by format

### Suggested ML Use-Cases

- view prediction
- channel recommendation
- topic lifecycle analysis

## startup_funding.csv

Rows: `241`

### Schema

| Field | Description |
|---|---|
| `funding_event_id` | Funding round identifier |
| `company_id` | Company key |
| `round_type` | Round or capital event type |
| `amount_musd` | Announced amount in USD millions |
| `valuation_musd` | Synthetic but plausible valuation estimate |
| `estimated_hiring_impact_pct` | Expected hiring lift after funding |

### Sample Records

```json
[
  {
    "funding_event_id": "FND-900000",
    "announced_at": "2025-02-15T00:00:00",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United States",
    "region": "North America",
    "tech_category": "AI Agents",
    "round_type": "Tender Offer",
    "amount_musd": 107.98,
    "valuation_musd": 1256.19,
    "lead_investor": "Sequoia",
    "sentiment_score": 0.325,
    "trend_score": 50.89,
    "estimated_hiring_impact_pct": 2.17,
    "risk_indicator": "low",
    "innovation_score": 89.24,
    "adoption_score": 73.21,
    "source_reference": "https://funding.example.com/900000"
  },
  {
    "funding_event_id": "FND-900001",
    "announced_at": "2025-02-16T00:00:00",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United States",
    "region": "North America",
    "tech_category": "Enterprise AI",
    "round_type": "Strategic Round",
    "amount_musd": 350.0,
    "valuation_musd": 7030.32,
    "lead_investor": "Accel",
    "sentiment_score": 0.14,
    "trend_score": 50.64,
    "estimated_hiring_impact_pct": 2.96,
    "risk_indicator": "low",
    "innovation_score": 78.69,
    "adoption_score": 79.82,
    "source_reference": "https://funding.example.com/900001"
  }
]
```

### Expected Analytics Usage

- capital allocation analysis
- funding-to-growth forecasting
- valuation benchmarking

### Suggested ML Use-Cases

- funding round classification
- post-funding hiring impact modeling
- valuation range estimation

## producthunt_launches.csv

Rows: `2400`

### Schema

| Field | Description |
|---|---|
| `launch_id` | Launch identifier |
| `product_name` | Product Hunt launch name |
| `category` | Product category |
| `upvotes` | Launch upvotes |
| `comments` | Launch comments |

### Sample Records

```json
[
  {
    "launch_id": "PH-950000",
    "launched_at": "2026-02-05T00:00:00",
    "company_id": "CMP-015",
    "company": "Windsurf",
    "product_name": "Windsurf Flow",
    "category": "Developer Tools",
    "topic": "Automation",
    "upvotes": 110,
    "comments": 18,
    "country": "United States",
    "trend_score": 48.92,
    "sentiment_score": 0.176,
    "popularity_growth_pct": -5.75,
    "volatility_metric": 10.63,
    "funding_estimate_musd": 30.19,
    "innovation_score": 82.83,
    "adoption_score": 76.36,
    "risk_indicator": "low",
    "ai_summary": "Windsurf teams are discussing how automation is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://producthunt.example.com/posts/950000"
  },
  {
    "launch_id": "PH-950001",
    "launched_at": "2025-03-19T00:00:00",
    "company_id": "CMP-028",
    "company": "LangChain",
    "product_name": "LangChain Copilot",
    "category": "Analytics",
    "topic": "Open Source AI",
    "upvotes": 178,
    "comments": 31,
    "country": "United States",
    "trend_score": 46.74,
    "sentiment_score": 0.295,
    "popularity_growth_pct": 5.47,
    "volatility_metric": 11.35,
    "funding_estimate_musd": 31.91,
    "innovation_score": 88.47,
    "adoption_score": 71.01,
    "risk_indicator": "low",
    "ai_summary": "Developers are comparing tooling choices around open source ai as budget owners ask for faster ROI and clearer governance. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://producthunt.example.com/posts/950001"
  }
]
```

### Expected Analytics Usage

- launch velocity tracking
- product demand testing
- top-of-funnel product discovery analytics

### Suggested ML Use-Cases

- launch success prediction
- category recommendation

## news_media_mentions.csv

Rows: `4656`

### Schema

| Field | Description |
|---|---|
| `mention_id` | News mention identifier |
| `headline` | Media headline |
| `mention_count` | Burst count proxy |
| `source` | News outlet |

### Sample Records

```json
[
  {
    "mention_id": "NEWS-980000",
    "published_at": "2025-01-03T02:00:00",
    "source": "Reuters",
    "topic": "AI Agents",
    "company_id": "CMP-002",
    "company": "Anthropic",
    "headline": "Anthropic sees stronger enterprise pull for ai agents",
    "country": "Singapore",
    "region": "Asia",
    "mention_count": 34,
    "trend_score": 47.19,
    "sentiment_score": 0.446,
    "funding_estimate_musd": 22.26,
    "hiring_activity_index": 48.55,
    "hashtags": "#aiagents|#SG",
    "popularity_growth_pct": -1.26,
    "volatility_metric": 6.83,
    "ai_summary": "Anthropic teams are discussing how ai agents is moving from experimentation into production buying cycles. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "low",
    "innovation_score": 93.91,
    "adoption_score": 67.21,
    "source_reference": "https://news.example.com/980000"
  },
  {
    "mention_id": "NEWS-980001",
    "published_at": "2025-01-07T21:00:00",
    "source": "Semafor",
    "topic": "AI Agents",
    "company_id": "CMP-031",
    "company": "AgentForge",
    "headline": "AgentForge sees stronger enterprise pull for ai agents",
    "country": "Germany",
    "region": "Europe",
    "mention_count": 29,
    "trend_score": 44.57,
    "sentiment_score": 0.07,
    "funding_estimate_musd": 25.49,
    "hiring_activity_index": 41.89,
    "hashtags": "#aiagents|#DE",
    "popularity_growth_pct": 4.21,
    "volatility_metric": 8.03,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 07, 2025 reflect both hype and practical deployment pressure. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "low",
    "innovation_score": 86.92,
    "adoption_score": 64.94,
    "source_reference": "https://news.example.com/980001"
  }
]
```

### Expected Analytics Usage

- earned media monitoring
- reputation risk dashboards
- topic burst detection

### Suggested ML Use-Cases

- reputation risk scoring
- headline sentiment analysis
- burst forecasting

## kaggle_ml_activity.csv

Rows: `3200`

### Schema

| Field | Description |
|---|---|
| `kaggle_activity_id` | Activity identifier |
| `competition_name` | Competition or theme |
| `kernels_created` | Notebook creation count |
| `dataset_downloads` | Download activity |
| `medal_rate` | Top submission share proxy |

### Sample Records

```json
[
  {
    "kaggle_activity_id": "KGL-990000",
    "activity_date": "2025-04-25T00:00:00",
    "competition_name": "Agent Reasoning Benchmark",
    "topic": "LLM",
    "company_id": "CMP-018",
    "company": "Mistral AI",
    "country": "Japan",
    "kernels_created": 42,
    "notebook_votes": 615,
    "dataset_downloads": 1657,
    "medal_rate": 0.219,
    "trend_score": 56.88,
    "sentiment_score": 0.165,
    "popularity_growth_pct": 0.78,
    "volatility_metric": 5.86,
    "innovation_score": 89.86,
    "adoption_score": 78.67,
    "risk_indicator": "low",
    "ai_summary": "Analysts note that llm usage patterns on Apr 25, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://kaggle.example.com/activity/990000"
  },
  {
    "kaggle_activity_id": "KGL-990001",
    "activity_date": "2025-03-05T00:00:00",
    "competition_name": "GPU Cost Forecasting",
    "topic": "Inference Optimization",
    "company_id": "CMP-004",
    "company": "NVIDIA",
    "country": "Japan",
    "kernels_created": 7,
    "notebook_votes": 112,
    "dataset_downloads": 212,
    "medal_rate": 0.201,
    "trend_score": 22.7,
    "sentiment_score": 0.301,
    "popularity_growth_pct": -1.73,
    "volatility_metric": 8.97,
    "innovation_score": 84.5,
    "adoption_score": 60.53,
    "risk_indicator": "low",
    "ai_summary": "NVIDIA teams are discussing how inference optimization is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://kaggle.example.com/activity/990001"
  }
]
```

### Expected Analytics Usage

- ML community activity monitoring
- competition-to-adoption trend analysis

### Suggested ML Use-Cases

- competition popularity forecasting
- talent signal extraction

## companies.csv

Rows: `39`

### Schema

| Field | Description |
|---|---|
| `company_id` | Primary company key |
| `company` | Company name |
| `country` | HQ country |
| `sector` | Business category |
| `dominant_topics` | Main trend themes |

### Sample Records

```json
[
  {
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United States",
    "country_code": "US",
    "region": "North America",
    "sector": "AI Platform",
    "stage": "private",
    "reference_type": "real_reference",
    "dominant_topics": "AI Agents, LLM, Generative AI, Enterprise AI"
  },
  {
    "company_id": "CMP-002",
    "company": "Anthropic",
    "country": "United States",
    "country_code": "US",
    "region": "North America",
    "sector": "AI Platform",
    "stage": "private",
    "reference_type": "real_reference",
    "dominant_topics": "AI Agents, LLM, Enterprise AI"
  }
]
```

### Expected Analytics Usage

- entity resolution
- company segmentation
- master data management

### Suggested ML Use-Cases

- entity graph features
- cross-source enrichment

## market_events.csv

Rows: `13`

### Schema

| Field | Description |
|---|---|
| `event_id` | Market event key |
| `event_date` | Event anchor date |
| `window_days` | Decay window |
| `title` | Description |
| `topic_impacts` | JSON of topic-specific shocks |

### Sample Records

```json
[
  {
    "event_id": "EVT-001",
    "event_date": "2025-01-22",
    "window_days": 10,
    "title": "Agentic coding workflows move from demos to pilots",
    "topic_impacts": "{\"AI Agents\": 12, \"Developer Tools\": 8, \"Enterprise AI\": 6}",
    "sentiment_shift": 0.07
  },
  {
    "event_id": "EVT-002",
    "event_date": "2025-03-12",
    "window_days": 14,
    "title": "Robotics model announcement lifts embodied AI interest",
    "topic_impacts": "{\"Robotics\": 18, \"Edge AI\": 10, \"LLM\": 4}",
    "sentiment_shift": 0.05
  }
]
```

### Expected Analytics Usage

- event-driven analytics
- shock attribution
- change-point explanation

### Suggested ML Use-Cases

- event attribution features
- causal impact analysis
