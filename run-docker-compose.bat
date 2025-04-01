@echo off
echo Starting Market Assistant services...
REM Rebuild and reload Docker images and containers
docker-compose build --no-cache
docker-compose up -d --force-recreate
echo.
echo Services started successfully!
echo Client: http://localhost:8080
echo Product API: http://localhost:8100
echo Main API: http://localhost:8101
echo whisper-service: -service: http://localhost:8012
echo.
echo To check container status:
echo docker-compose ps
echo.
echo To check network connectivity:
echo docker network inspect market-assistant-network
echo.
echo To view logs:
echo docker-compose logs -f main-api
echo.
echo To restart after fixes:
echo docker-compose restart main-api