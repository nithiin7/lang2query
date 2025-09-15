run:
	poetry run lang2query

run-local:
	L2Q_USE_OLLAMA=0 poetry run lang2query

install:
	poetry install

install-local:
	poetry add torch torchvision torchaudio transformers accelerate bitsandbytes
	poetry install

format:
	poetry run format

lint:
	poetry run lint

lint-fix:
	poetry run lint-fix

test:
	poetry run test

type-check:
	poetry run type-check
