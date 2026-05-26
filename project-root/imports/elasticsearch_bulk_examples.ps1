# Example Elasticsearch bulk prep commands for TechTrends datasets
# Convert CSVs to NDJSON first if you want full bulk indexing at scale.
# Example curl commands:
# curl -X PUT http://localhost:9200/techtrends-twitter
# curl -H "Content-Type: application/x-ndjson" -X POST http://localhost:9200/techtrends-twitter/_bulk --data-binary "@samples\json\twitter_stream.bulk.ndjson"
