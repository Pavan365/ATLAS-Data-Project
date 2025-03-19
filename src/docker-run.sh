# Set message colours.
CYAN="\e[36m"
GREEN="\e[32m"
NORMAL="\e[0m"
PURPLE="\e[35m"
RED="\e[31m"
WHITE="\e[37m"

# Echo start message.
echo -e ""$CYAN"status"$WHITE": start"$NORMAL""

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
else
    # Echo error message.
    echo -e ""$CYAN"status"$WHITE": "$RED"error"$WHITE" - manager exited with code "$MANAGER""$NORMAL""
    STATE=""$RED"error"
fi

# Stop containers.
echo -e ""$CYAN"status"$WHITE": stopping containers"$NORMAL""
docker compose stop

# Confirm deletion of containers.
read -p "$(echo -e ""$PURPLE"confirm"$WHITE": delete containers? [Y/N]: "$NORMAL"")" DELETE
DELETE=${DELETE^^}

# If the user wants to delete the containers.
if [[ "$DELETE" = "Y" || "$DELETE" = "YES" ]]
then
    # Delete containers.
    echo -e ""$CYAN"status"$WHITE": deleting containers"$NORMAL""
    docker compose down
fi

# Echo end message.
echo -e ""$CYAN"status"$WHITE": end ("$STATE""$WHITE")"$NORMAL""
