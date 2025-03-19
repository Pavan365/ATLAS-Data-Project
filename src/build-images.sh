# Set message colours.
CYAN="\e[36m"
NORMAL="\e[0m"
WHITE="\e[37m"

# Echo start message.
echo -e ""$CYAN"status"$WHITE": start"$NORMAL""

# Build images.
echo -e ""$CYAN"status"$WHITE": building images"$NORMAL""
docker build -t higgs-manager:latest -f manager/Dockerfile .
docker build -t higgs-worker:latest -f worker/Dockerfile .

# Echo end message.
echo -e ""$CYAN"status"$WHITE": end"$NORMAL""
