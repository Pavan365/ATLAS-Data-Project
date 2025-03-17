# Echo start message.
echo status: start

# Build images.
echo status: building images
docker build -t higgs-manager:latest -f manager/Dockerfile .
docker build -t higgs-worker:latest -f worker/Dockerfile .

# Docker compose up.
echo status: starting containers
docker compose up -d

# Wait for manager to finish.
echo status: waiting for manager to finish
MANAGER=$(docker wait src-manager-1)

# If the manager was successful.
if [ "$MANAGER" -eq 0 ]
then
    # Echo success message.
    echo success: manager exited with code "$MANAGER"
    STATE="success"
    # Save figure.
    echo status: saving figure
    docker cp src-manager-1:/app/output/higgs_zz.png ./output/
    # Stop containers.
    echo status: stopping containers
    docker compose stop
else
    # Echo error message.
    echo error: manager exited with code "$MANAGER"
    STATE="failed"
    # Stop containers.
    echo status: stopping containers
    docker compose stop 
fi

# Echo end message.
echo status: end "("$STATE")"
