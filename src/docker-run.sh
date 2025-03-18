# Set message colours.
CYAN="\e[36m"
GREEN="\e[32m"
RED="\e[31m"
WHITE="\e[37m"
NORMAL="\e[0m"

# Echo start message.
echo -e ""$CYAN"status"$WHITE": start"$NORMAL""

# Build images.
echo -e ""$CYAN"status"$WHITE": building images"$NORMAL""
docker build -t higgs-manager:latest -f manager/Dockerfile .
docker build -t higgs-worker:latest -f worker/Dockerfile .

# Docker compose up.
echo -e ""$CYAN"status"$WHITE": starting containers"$NORMAL""
docker compose up -d

# Wait for manager to finish.
echo -e ""$CYAN"status"$WHITE": waiting for manager to finish"$NORMAL""
MANAGER=$(docker wait src-manager-1)

# If the manager was successful.
if [ "$MANAGER" -eq 0 ]
then
    # Echo success message.
    echo -e ""$CYAN"status"$WHITE": "$GREEN"success"$WHITE" - manager exited with code "$MANAGER""$NORMAL""
    STATE=""$GREEN"success"
    # Save figure.
    echo -e ""$CYAN"status"$WHITE": saving figure"$NORMAL""
    docker cp src-manager-1:/app/output/higgs_zz.png ./output/higgs_zz_docker.png
    # Stop containers.
    echo -e ""$CYAN"status"$WHITE": stopping containers"$NORMAL""
    docker compose stop
else
    # Echo error message.
    echo -e ""$CYAN"status"$WHITE": "$RED"error"$WHITE" - manager exited with code "$MANAGER""$NORMAL""
    STATE=""$RED"error"
    # Stop containers.
    echo -e ""$CYAN"status"$WHITE": stopping containers"$NORMAL""
    docker compose stop 
fi

# Echo end message.
echo -e ""$CYAN"status"$WHITE": end ("$STATE""$WHITE")"$NORMAL""
