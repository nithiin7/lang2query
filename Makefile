# Text2Query Makefile
# Run commands for the Text2Query application

.PHONY: help embeddings download install venv clean run-api run-api-ollama dev run-frontend

# Default target
help:
	@echo "Available commands:"
	@echo "  embeddings - Create/update knowledge base embeddings"
	@echo "  run-app - Run the app frontend"
	@echo "  run-api   - Run the Flask API""
	@echo "  dev       - Run API and frontend together"
	@echo "  download   - Run the model download script"
	@echo "  install    - Install Python dependencies"
	@echo "  venv       - Create and activate virtual environment"
	@echo "  clean      - Clean up temporary files"
	@echo "  help       - Show this help message"

# Create/update knowledge base embeddings
embeddings:
	@echo "🔧 Creating knowledge base embeddings..."
	cd backend/app && python3 workers/document_ingestion.py \
		--md-dir "ai/input" \
		--chroma-dir "ai/kb" \
		--collection-name "sql_generation_kb" \
		--batch-size 1 \
		--output-dir "ai/output" \
		--chunked-json-dir "ai/output"

# Run the frontend
run-app:
	@echo "🚀 Starting Text2Query Frontend..."
	cd frontend && npm run dev

# Run the Flask API
run-api:
	@echo "🔌 Starting Flask API..."
	cd backend/app && python3 -m main

# Run API and frontend together
dev:
	@echo "🔧 Starting API and Frontend..."
	( cd frontend && npm run dev ) & \
	cd backend/app && python3 -m main

# Run the download script
download:
	@echo "📥 Running model download script..."
	python3 backend/app/download.py

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install ./backend

# Setup virtual environment
venv:
	@echo "🐍 Setting up virtual environment..."
	python3 -m venv venv
	@echo "✅ Virtual environment created. Run 'source venv/bin/activate' to activate it."

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +