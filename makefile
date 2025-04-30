# Makefile for pyunimus project

IMAGE_NAME = pyunimus
CONTAINER_NAME = pyunimus_container
COMPOSE_FILE = docker-compose.yml

.PHONY: build up down logs shell

build:
	docker build -t $(IMAGE_NAME) .

up:
	docker compose -f $(COMPOSE_FILE) up -d --build

down:
	docker compose -f $(COMPOSE_FILE) down

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

shell:
	docker exec -it $(CONTAINER_NAME) /bin/sh
