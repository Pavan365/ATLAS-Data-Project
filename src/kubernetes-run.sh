# Set message colours.
CYAN="\e[36m"
GREEN="\e[32m"
NORMAL="\e[0m"
PURPLE="\e[35m"
RED="\e[31m"
WHITE="\e[37m"

# Echo start message.
echo -e ""$CYAN"status"$WHITE": start"$NORMAL""

# Confirm use of KEDA (autoscaler).
read -p "$(echo -e ""$PURPLE"confirm"$WHITE": use KEDA (autoscaler)? [Y/N]: "$NORMAL"")" KEDA
KEDA=${KEDA^^}

# Create the volume claim.
echo -e ""$CYAN"status"$WHITE": creating volume claim"$NORMAL""
kubectl apply -f ./kubernetes/higgs-volume-claim.yaml

# Start the RabbitMQ pod.
echo -e ""$CYAN"status"$WHITE": starting RabbitMQ pod"$NORMAL""
kubectl apply -f ./kubernetes/rabbitmq.yaml
kubectl apply -f ./kubernetes/rabbitmq-service.yaml

# Wait for RabbitMQ to start.
echo -e ""$CYAN"status"$WHITE": waiting for RabbitMQ to start"$NORMAL""
RABBITMQ_STATE="false"

# Wait for RabbitMQ to start.
while [ "$RABBITMQ_STATE" = "false" ]
do
    # Check RabbitMQ state.
    echo -e ""$CYAN"status"$WHITE": checking RabbitMQ state"$NORMAL"" 
    RABBITMQ_STATE=$(kubectl get pod --selector=app=rabbitmq --output=jsonpath="{.items[0].status.containerStatuses[0].ready}")
    sleep 20
done

# Start the manager and worker pods.
echo -e ""$CYAN"status"$WHITE": starting manager and worker pods"$NORMAL""
kubectl apply -f ./kubernetes/higgs-manager.yaml
kubectl apply -f ./kubernetes/higgs-worker.yaml

# If the user wants to use KEDA.
if [[ "$KEDA" = "Y" || "$KEDA" = "YES" ]]
then
    # Wait for the workers to start.
    kubectl wait --for=condition=available deployment/worker --timeout=60s
    # Activate KEDA.
    echo -e ""$CYAN"status"$WHITE": starting KEDA configuration"$NORMAL""
    kubectl apply -f ./keda/keda-secret.yaml
    kubectl apply -f ./keda/keda-auth.yaml
    kubectl apply -f ./keda/keda-scaler.yaml
fi

# Wait for manager to finish.
echo -e ""$CYAN"status"$WHITE": waiting for manager to finish"$NORMAL""
SUCCEEDED=""
FAILED=""

# Wait for manager to finish.
while [[ -z "$SUCCEEDED" && -z "$FAILED" ]]
do
    # Check manager state.
    echo -e ""$CYAN"status"$WHITE": checking manager state"$NORMAL""
    SUCCEEDED=$(kubectl get job manager --output=jsonpath="{.status.succeeded}") 
    FAILED=$(kubectl get job manager --output=jsonpath="{.status.failed}")
    sleep 30
done

# Get the exit code of the manager.
MANAGER_POD=$(kubectl get pods --selector=job-name=manager --output=jsonpath="{.items[0].metadata.name}")
EXIT_CODE=$(kubectl get pod "$MANAGER_POD" --output=jsonpath="{.status.containerStatuses[0].state.terminated.exitCode}")

# If the manager was successful.
if [[ -n "$SUCCEEDED" && "$SUCCEEDED" -eq 1 ]]
then
    # Echo success message.
    echo -e ""$CYAN"status"$WHITE": "$GREEN"success"$WHITE" - manager exited with code "$EXIT_CODE""$NORMAL""
    STATE=""$GREEN"success"
    # Save figure.
    echo -e ""$CYAN"status"$WHITE": saving figure"$NORMAL""
    # Start BusyBox pod.
    echo -e ""$CYAN"status"$WHITE": starting BusyBox pod"$NORMAL""
    kubectl apply -f ./kubernetes/busybox-higgs-plot.yaml
    # Wait for the BusyBox pod to start.
    kubectl wait --for=condition=ready=true pod busybox-higgs-plot
    # Save figure.
    kubectl cp busybox-higgs-plot:/output/higgs_zz.png ./output/higgs_zz_kubernetes.png
    echo -e ""$CYAN"status"$WHITE": saved figure"$NORMAL""
# If the manager was unsuccessful.
elif [[ -n "$FAILED" && "$FAILED" -eq 1 ]]
then
    # Echo error message.
    echo -e ""$CYAN"status"$WHITE": "$RED"error"$WHITE" - manager exited with code "$EXIT_CODE""$NORMAL""
    STATE=""$RED"error"
fi

# Confirm deletion of pods.
read -p "$(echo -e ""$PURPLE"confirm"$WHITE": delete pods? [Y/N]: "$NORMAL"")" DELETE
DELETE=${DELETE^^}

# If the user wants to delete the pods.
if [[ "$DELETE" = "Y" || "$DELETE" = "YES" ]]
then
    # Deactivate KEDA.
    if [[ "$KEDA" = "Y" || "$KEDA" = "YES" ]]
    then
        # Activate KEDA.
        echo -e ""$CYAN"status"$WHITE": deleting KEDA configuration"$NORMAL""
        kubectl delete -f ./keda/keda-scaler.yaml
        kubectl delete -f ./keda/keda-auth.yaml
        kubectl delete -f ./keda/keda-secret.yaml
    fi

    # Delete pods.
    echo -e ""$CYAN"status"$WHITE": deleting pods"$NORMAL""
    kubectl delete -f ./kubernetes/rabbitmq.yaml
    kubectl delete -f ./kubernetes/rabbitmq-service.yaml
    kubectl delete -f ./kubernetes/higgs-manager.yaml
    kubectl delete -f ./kubernetes/higgs-worker.yaml

    # Delete BusyBox pod.
    if [[ -n "$SUCCEEDED" && "$SUCCEEDED" -eq 1 ]]
    then
        kubectl delete -f ./kubernetes/busybox-higgs-plot.yaml
    fi
fi

# Echo end message.
echo -e ""$CYAN"status"$WHITE": end ("$STATE""$WHITE")"$NORMAL""
