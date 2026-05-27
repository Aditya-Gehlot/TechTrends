# Market Intelligence Dataset Catalog

This catalog documents the synthetic datasets generated for TechTrends. The data is designed to be CSV-ready and realistic enough for analytics, reporting, and ML prototyping while remaining synthetic.

## linkedin_jobs.csv

Rows: `54562`

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
    "hiring_index": 72.82,
    "funding_signal": 1.13,
    "sentiment_score": 0.189,
    "trend_score": 57.27,
    "popularity_growth_pct": -1.19,
    "volatility_metric": 8.93,
    "innovation_score": 88.07,
    "adoption_score": 69.1,
    "risk_indicator": "low",
    "source_platform": "LinkedIn"
  },
  {
    "job_id": "JOB-100001",
    "posted_at": "2025-01-02T08:00:00",
    "company": "OpenAI",
    "role": "Generative AI Product Engineer",
    "location": "New York",
    "salary_usd": 185097.0,
    "experience_years": 4,
    "skills": "Diffusion, Serving, Inference, Prompt Engineering, PyTorch",
    "job_description": "OpenAI is hiring a Generative AI Product Engineer in New York to scale generative ai initiatives across enterprise and developer workflows. The team is focused on cost-efficient inference while supporting production customers. Candidates should be comfortable with Diffusion, Serving, Inference and cross-functional delivery in a fast-moving market.",
    "company_id": "CMP-001",
    "country": "United States",
    "region": "North America",
    "tech_category": "Generative AI",
    "hiring_index": 72.82,
    "funding_signal": 1.13,
    "sentiment_score": 0.189,
    "trend_score": 57.27,
    "popularity_growth_pct": -1.19,
    "volatility_metric": 8.93,
    "innovation_score": 88.07,
    "adoption_score": 69.1,
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

Rows: `54182`

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
    "created_at": "2025-01-01T06:55:00",
    "username": "ml_26824",
    "followers": 17343,
    "tech_topic": "AI Agents",
    "sentiment": "negative",
    "likes": 3207,
    "retweets": 891,
    "content": "Cursor keeps showing up in AI Agents discussions as teams focus on developer adoption. #AIAgents #US #cursor",
    "company_id": "CMP-013",
    "company": "Cursor",
    "country": "United States",
    "region": "North America",
    "trend_score": 51.72,
    "sentiment_score": -0.204,
    "funding_estimate_musd": 158.52,
    "hiring_activity_index": 49.66,
    "hashtags": "#AIAgents|#US|#cursor",
    "popularity_growth_pct": 0.6,
    "volatility_metric": 6.76,
    "ai_summary": "Cursor teams are discussing how ai agents is moving from experimentation into production buying cycles. Interest is still present, but reliability, cost, and security concerns are slowing near-term expansion for some teams.",
    "risk_indicator": "low",
    "innovation_score": 89.73,
    "adoption_score": 63.67,
    "source_reference": "https://x.example.com/CMP-013/200000"
  },
  {
    "tweet_id": "TWT-200001",
    "created_at": "2025-01-01T23:28:00",
    "username": "data_11366",
    "followers": 15509,
    "tech_topic": "AI Agents",
    "sentiment": "positive",
    "likes": 3408,
    "retweets": 1329,
    "content": "Windsurf keeps showing up in AI Agents discussions as teams focus on developer adoption. #AIAgents #US #windsurf",
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United States",
    "region": "North America",
    "trend_score": 51.72,
    "sentiment_score": 0.399,
    "funding_estimate_musd": 188.04,
    "hiring_activity_index": 57.73,
    "hashtags": "#AIAgents|#US|#windsurf",
    "popularity_growth_pct": 0.6,
    "volatility_metric": 6.76,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "low",
    "innovation_score": 89.73,
    "adoption_score": 63.67,
    "source_reference": "https://x.example.com/CMP-015/200001"
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

Rows: `33002`

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
    "event_time": "2025-01-06T00:00:00",
    "repository": "openai/llm-starter",
    "language": "Python",
    "stars_added": 295,
    "forks_added": 93,
    "contributors": 16,
    "topic": "LLM",
    "event_type": "discussion",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "region": "North America",
    "issue_count": 6,
    "watchers_added": 59,
    "release_flag": false,
    "trend_score": 57.39,
    "popularity_growth_pct": 2.15,
    "volatility_metric": 9.95,
    "innovation_score": 91.33,
    "adoption_score": 71.39,
    "risk_indicator": "low",
    "ai_summary": "OpenAI teams are discussing how llm is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption."
  },
  {
    "event_id": "GIT-300001",
    "event_time": "2025-01-06T00:00:00",
    "repository": "openai/ai-agents-ops",
    "language": "Python",
    "stars_added": 271,
    "forks_added": 139,
    "contributors": 13,
    "topic": "AI Agents",
    "event_type": "release",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "region": "North America",
    "issue_count": 10,
    "watchers_added": 61,
    "release_flag": true,
    "trend_score": 57.39,
    "popularity_growth_pct": 2.15,
    "volatility_metric": 9.95,
    "innovation_score": 91.33,
    "adoption_score": 71.39,
    "risk_indicator": "low",
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 06, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption."
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

Rows: `11468`

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
    "published_at": "2025-01-02T00:00:00",
    "source": "Dev.to",
    "author": "Maya Garcia",
    "topic": "AI Agents",
    "title": "AI Agents buying signals in 2025: what OpenAI signals imply",
    "views": 9809,
    "reading_time_minutes": 6,
    "summary": "OpenAI teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "Canada",
    "region": "North America",
    "trend_score": 45.27,
    "sentiment_score": 0.21,
    "funding_estimate_musd": 37.64,
    "hiring_activity_index": 51.87,
    "hashtags": "#aiagents|#CA",
    "popularity_growth_pct": 1.98,
    "volatility_metric": 7.85,
    "risk_indicator": "low",
    "innovation_score": 90.86,
    "adoption_score": 69.0,
    "source_reference": "https://blog.example.com/400000"
  },
  {
    "article_id": "ART-400001",
    "published_at": "2025-01-02T00:00:00",
    "source": "Hugging Face Blog",
    "author": "Kenji Dubois",
    "topic": "AI Agents",
    "title": "AI Agents open-source momentum in 2025: what OpenAI signals imply",
    "views": 15740,
    "reading_time_minutes": 5,
    "summary": "Analysts note that ai agents usage patterns on Jan 02, 2025 reflect both hype and practical deployment pressure. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "Canada",
    "region": "North America",
    "trend_score": 45.27,
    "sentiment_score": 0.21,
    "funding_estimate_musd": 24.91,
    "hiring_activity_index": 51.98,
    "hashtags": "#aiagents|#CA",
    "popularity_growth_pct": 1.98,
    "volatility_metric": 7.85,
    "risk_indicator": "low",
    "innovation_score": 90.86,
    "adoption_score": 69.0,
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

Rows: `18470`

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
    "views": 5870,
    "answers": 6,
    "score": 74,
    "accepted_answer": true,
    "title": "Best production pattern for AI Agents with LangChain stack?",
    "body_preview": "Our team is deploying ai agents workloads and seeing issues around hallucination risk. We use components similar to LangChain and need guidance for production-ready patterns.",
    "company_id": "CMP-028",
    "company": "LangChain",
    "country": "United Arab Emirates",
    "trend_score": 46.07,
    "sentiment_score": 0.176,
    "popularity_growth_pct": 2.51,
    "volatility_metric": 7.38,
    "innovation_score": 91.14,
    "adoption_score": 71.66,
    "risk_indicator": "low",
    "source_reference": "https://stackoverflow.example.com/questions/500000"
  },
  {
    "question_id": "SO-500001",
    "created_at": "2025-01-01T00:00:00",
    "tag": "AI Agents",
    "views": 5317,
    "answers": 8,
    "score": 57,
    "accepted_answer": true,
    "title": "How to scale AI Agents workloads without runaway cost?",
    "body_preview": "Our team is deploying ai agents workloads and seeing issues around schema drift. We use components similar to OpenAI and need guidance for production-ready patterns.",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United Arab Emirates",
    "trend_score": 46.07,
    "sentiment_score": 0.176,
    "popularity_growth_pct": 2.51,
    "volatility_metric": 7.38,
    "innovation_score": 91.14,
    "adoption_score": 71.66,
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
    "trend_score": 52,
    "region": "US",
    "country": "United States",
    "tech_category": "AI Agents",
    "sentiment_score": 0.132,
    "popularity_growth_pct": 0.6,
    "volatility_metric": 6.76,
    "innovation_score": 89.73,
    "adoption_score": 63.67,
    "risk_indicator": "low",
    "event_refs": ""
  },
  {
    "date": "2025-01-01",
    "keyword": "AI Agents",
    "trend_score": 47,
    "region": "IN",
    "country": "India",
    "tech_category": "AI Agents",
    "sentiment_score": 0.274,
    "popularity_growth_pct": 1.28,
    "volatility_metric": 7.07,
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

Rows: `25348`

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
    "created_at": "2025-01-02T18:07:00",
    "subreddit": "r/devops",
    "username": "model_60000",
    "topic": "AI Agents",
    "title": "Is AI Agents still underhyped or already overheating?",
    "body": "Seeing more teams mention Windsurf whenever ai agents comes up. Feels like adoption is real in United Kingdom, but the debate around security keeps resurfacing.",
    "upvotes": 842,
    "comments": 191,
    "sentiment_score": 0.335,
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United Kingdom",
    "region": "Europe",
    "trend_score": 50.32,
    "funding_estimate_musd": 27.05,
    "hiring_activity_index": 46.38,
    "hashtags": "#aiagents|#UK",
    "popularity_growth_pct": -6.34,
    "volatility_metric": 9.43,
    "ai_summary": "Developers are comparing tooling choices around ai agents as budget owners ask for faster ROI and clearer governance. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "moderate",
    "innovation_score": 92.27,
    "adoption_score": 64.83,
    "source_reference": "https://reddit.example.com/600000"
  },
  {
    "reddit_post_id": "RDT-600001",
    "created_at": "2025-01-02T13:06:00",
    "subreddit": "r/artificial",
    "username": "secure_56416",
    "topic": "AI Agents",
    "title": "Is AI Agents still underhyped or already overheating?",
    "body": "Seeing more teams mention Windsurf whenever ai agents comes up. Feels like adoption is real in United Kingdom, but the debate around moats keeps resurfacing.",
    "upvotes": 851,
    "comments": 181,
    "sentiment_score": 0.236,
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United Kingdom",
    "region": "Europe",
    "trend_score": 50.32,
    "funding_estimate_musd": 20.01,
    "hiring_activity_index": 49.15,
    "hashtags": "#aiagents|#UK",
    "popularity_growth_pct": -6.34,
    "volatility_metric": 9.43,
    "ai_summary": "Windsurf teams are discussing how ai agents is moving from experimentation into production buying cycles. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "moderate",
    "innovation_score": 92.27,
    "adoption_score": 64.83,
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

Rows: `1538`

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
    "created_at": "2025-01-02T12:00:00",
    "title": "Windsurf and the new economics of ai agents",
    "domain": "huggingface.co",
    "topic": "AI Agents",
    "points": 219,
    "comments": 99,
    "company_id": "CMP-015",
    "company": "Windsurf",
    "country": "United States",
    "trend_score": 48.92,
    "sentiment_score": 0.284,
    "popularity_growth_pct": -5.42,
    "volatility_metric": 11.48,
    "innovation_score": 89.4,
    "adoption_score": 61.84,
    "risk_indicator": "moderate",
    "ai_summary": "Developers are comparing tooling choices around ai agents as budget owners ask for faster ROI and clearer governance. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://news.ycombinator.com/item?id=700000"
  },
  {
    "hn_post_id": "HN-700001",
    "created_at": "2025-01-02T19:00:00",
    "title": "OpenAI and the new economics of ai agents",
    "domain": "github.com",
    "topic": "AI Agents",
    "points": 199,
    "comments": 68,
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United States",
    "trend_score": 48.92,
    "sentiment_score": -0.102,
    "popularity_growth_pct": -5.42,
    "volatility_metric": 11.48,
    "innovation_score": 89.4,
    "adoption_score": 61.84,
    "risk_indicator": "moderate",
    "ai_summary": "OpenAI teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
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

Rows: `6942`

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
    "published_at": "2025-01-03T02:00:00",
    "channel": "Two Minute Papers",
    "topic": "AI Agents",
    "company_id": "CMP-002",
    "company": "Anthropic",
    "title": "AI Agents market update: what Anthropic says about 2026 demand",
    "views": 44849,
    "likes": 3036,
    "comments": 636,
    "watch_time_minutes": 36058,
    "country": "United Kingdom",
    "sentiment_score": 0.051,
    "trend_score": 53.05,
    "funding_estimate_musd": 18.63,
    "hiring_activity_index": 47.14,
    "hashtags": "#aiagents|#AI|#UK",
    "popularity_growth_pct": 5.42,
    "volatility_metric": 11.1,
    "ai_summary": "Anthropic teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "moderate",
    "innovation_score": 88.95,
    "adoption_score": 71.1,
    "source_reference": "https://youtube.example.com/watch?v=800000"
  },
  {
    "video_id": "YT-800001",
    "published_at": "2025-01-03T07:00:00",
    "channel": "Machine Learning Street Talk",
    "topic": "AI Agents",
    "company_id": "CMP-015",
    "company": "Windsurf",
    "title": "AI Agents market update: what Windsurf says about 2026 demand",
    "views": 12777,
    "likes": 384,
    "comments": 50,
    "watch_time_minutes": 24553,
    "country": "United Kingdom",
    "sentiment_score": 0.213,
    "trend_score": 53.05,
    "funding_estimate_musd": 23.33,
    "hiring_activity_index": 45.52,
    "hashtags": "#aiagents|#AI|#UK",
    "popularity_growth_pct": 5.42,
    "volatility_metric": 11.1,
    "ai_summary": "Windsurf teams are discussing how ai agents is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "risk_indicator": "moderate",
    "innovation_score": 88.95,
    "adoption_score": 71.1,
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

Rows: `482`

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
    "announced_at": "2025-01-19T00:00:00",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United States",
    "region": "North America",
    "tech_category": "AI Agents",
    "round_type": "Growth Round",
    "amount_musd": 136.02,
    "valuation_musd": 987.81,
    "lead_investor": "SoftBank",
    "sentiment_score": 0.264,
    "trend_score": 55.92,
    "estimated_hiring_impact_pct": 2.0,
    "risk_indicator": "low",
    "innovation_score": 89.78,
    "adoption_score": 72.37,
    "source_reference": "https://funding.example.com/900000"
  },
  {
    "funding_event_id": "FND-900001",
    "announced_at": "2025-01-22T00:00:00",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "United States",
    "region": "North America",
    "tech_category": "Generative AI",
    "round_type": "Growth Round",
    "amount_musd": 150.29,
    "valuation_musd": 2578.7,
    "lead_investor": "Lightspeed",
    "sentiment_score": 0.015,
    "trend_score": 65.52,
    "estimated_hiring_impact_pct": 3.07,
    "risk_indicator": "low",
    "innovation_score": 91.79,
    "adoption_score": 71.29,
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

Rows: `3880`

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
    "category": "Infrastructure",
    "topic": "Automation",
    "upvotes": 157,
    "comments": 27,
    "country": "United States",
    "trend_score": 51.59,
    "sentiment_score": -0.035,
    "popularity_growth_pct": -5.62,
    "volatility_metric": 10.6,
    "funding_estimate_musd": 15.48,
    "innovation_score": 82.83,
    "adoption_score": 76.93,
    "risk_indicator": "low",
    "ai_summary": "Developers are comparing tooling choices around automation as budget owners ask for faster ROI and clearer governance. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
    "source_reference": "https://producthunt.example.com/posts/950000"
  },
  {
    "launch_id": "PH-950001",
    "launched_at": "2025-03-19T00:00:00",
    "company_id": "CMP-028",
    "company": "LangChain",
    "product_name": "LangChain Copilot",
    "category": "Security",
    "topic": "Developer Tools",
    "upvotes": 180,
    "comments": 35,
    "country": "United States",
    "trend_score": 48.33,
    "sentiment_score": 0.463,
    "popularity_growth_pct": 5.38,
    "volatility_metric": 11.33,
    "funding_estimate_musd": 26.24,
    "innovation_score": 88.47,
    "adoption_score": 71.15,
    "risk_indicator": "low",
    "ai_summary": "Developers are comparing tooling choices around developer tools as budget owners ask for faster ROI and clearer governance. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
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

Rows: `9514`

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
    "published_at": "2025-01-01T21:00:00",
    "source": "The Information",
    "topic": "AI Agents",
    "company_id": "CMP-015",
    "company": "Windsurf",
    "headline": "Windsurf sees stronger enterprise pull for ai agents",
    "country": "United Kingdom",
    "region": "Europe",
    "mention_count": 37,
    "trend_score": 53.73,
    "sentiment_score": -0.192,
    "funding_estimate_musd": 26.99,
    "hiring_activity_index": 51.61,
    "hashtags": "#aiagents|#UK",
    "popularity_growth_pct": 3.54,
    "volatility_metric": 9.37,
    "ai_summary": "Analysts note that ai agents usage patterns on Jan 01, 2025 reflect both hype and practical deployment pressure. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "moderate",
    "innovation_score": 88.9,
    "adoption_score": 65.28,
    "source_reference": "https://news.example.com/980000"
  },
  {
    "mention_id": "NEWS-980001",
    "published_at": "2025-01-01T05:00:00",
    "source": "TechCrunch",
    "topic": "AI Agents",
    "company_id": "CMP-002",
    "company": "Anthropic",
    "headline": "Anthropic sees stronger enterprise pull for ai agents",
    "country": "United Kingdom",
    "region": "Europe",
    "mention_count": 43,
    "trend_score": 53.73,
    "sentiment_score": 0.02,
    "funding_estimate_musd": 19.44,
    "hiring_activity_index": 60.82,
    "hashtags": "#aiagents|#UK",
    "popularity_growth_pct": 3.54,
    "volatility_metric": 9.37,
    "ai_summary": "Developers are comparing tooling choices around ai agents as budget owners ask for faster ROI and clearer governance. The conversation is active, though buyers continue to separate pilot noise from repeatable production value.",
    "risk_indicator": "moderate",
    "innovation_score": 88.9,
    "adoption_score": 65.28,
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

Rows: `6400`

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
    "competition_name": "Cyber Incident Detection",
    "topic": "LLM",
    "company_id": "CMP-001",
    "company": "OpenAI",
    "country": "Japan",
    "kernels_created": 48,
    "notebook_votes": 716,
    "dataset_downloads": 1887,
    "medal_rate": 0.223,
    "trend_score": 56.88,
    "sentiment_score": 0.16,
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
    "competition_name": "Cyber Incident Detection",
    "topic": "Inference Optimization",
    "company_id": "CMP-018",
    "company": "Mistral AI",
    "country": "Japan",
    "kernels_created": 8,
    "notebook_votes": 117,
    "dataset_downloads": 443,
    "medal_rate": 0.208,
    "trend_score": 22.92,
    "sentiment_score": 0.275,
    "popularity_growth_pct": -1.7,
    "volatility_metric": 8.97,
    "innovation_score": 84.5,
    "adoption_score": 60.62,
    "risk_indicator": "low",
    "ai_summary": "Mistral AI teams are discussing how inference optimization is moving from experimentation into production buying cycles. Demand remains healthy, but platform differentiation now depends on reliability, cost control, and measurable adoption.",
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
