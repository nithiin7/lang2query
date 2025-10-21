# Text2Query Makefile
# Run commands for the Text2Query application

.PHONY: help run embeddings download install venv clean run-api run-api-ollama dev run-frontend

# Default target
help:
	@echo "Available commands:"
	@echo "  run        - Run the main Text2Query application"
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
	python3 src/retriever/create_sql_kb_embeddings.py \
		--md-dir "src/retriever/input" \
		--chroma-dir "src/kb" \
		--collection-name "sql_generation_kb" \
		--batch-size 1 \
		--output-dir "src/retriever/output" \
		--chunked-json-dir "src/retriever/output"

# Run the main application
run:
	@echo "🚀 Starting Text2Query application..."
	python3 src/main.py

# Run the frontend
run-app:
	@echo "🚀 Starting Text2Query Frontend..."
	cd app && npm run dev

# Run the Flask API
run-api:
	@echo "🔌 Starting Flask API..."
	cd src && python3 -m api.app

# Run API and frontend together
dev:
	@echo "🔧 Starting API and Frontend..."
	( cd app && npm run dev ) & \
	cd src && python3 -m api.app

# Run the download script
download:
	@echo "📥 Running model download script..."
	python3 src/download.py

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

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