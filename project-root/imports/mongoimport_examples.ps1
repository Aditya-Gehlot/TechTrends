# Example MongoDB import commands for TechTrends datasets
$db = "techtrends_market_intel"
mongoimport --db $db --collection companies --type csv --headerline --file Data\market_intel\companies.csv
mongoimport --db $db --collection linkedin_jobs --type csv --headerline --file Data\linkedin_jobs.csv
mongoimport --db $db --collection twitter_stream --type csv --headerline --file Data\twitter_stream.csv
mongoimport --db $db --collection github_events --type csv --headerline --file Data\github_events.csv
mongoimport --db $db --collection reddit_discussions --type csv --headerline --file Data\market_intel\reddit_discussions.csv
