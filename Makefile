build:
	docker build --platform linux/arm64 -t mi-api-local .

run:
	docker run -d -p 8000:8000 --name ia-local-container mi-api-local

logs:
	docker logs -f ia-local-container

stop:
	docker stop ia-local-container && docker rm ia-local-container

clean:
	docker stop ia-local-container || true
	docker rm ia-local-container || true
	docker rmi mi-api-local || true