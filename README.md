# Cloud Computing - ATLAS Data Processing Project

## Contents
1. [Overview](#overview)
2. [Requirements](#requirements)
    + [Docker Desktop & Kubernetes (K8s)](#docker-desktop--kubernetes-k8s)
    + [Kubernetes Event-Driven Autoscaling (KEDA)](#kubernetes-event-driven-autoscaling-keda)
3. [Usage](#usage)
    + [General](#general)
    + [Docker Workflow](#docker-workflow)
    + [Kubernetes Static Workflow](#kubernetes-static-workflow)
    + [Kubernetes KEDA Workflow](#kubernetes-keda-workflow)
4. [Codebase Structure](#codebase-structure)
5. [References](#references)

## Overview
<p align=justify>
Welcome! This is the codebase for the cloud computing project of creating an 
automated data processing workflow for data from the ATLAS experiment at CERN. 
</p>

<p align=justify>
In particular, this project looks at breaking down and distributing the 
processing of data for the Higgs to 4-lepton process. This involves processing 
data (measured and Monte Carlo simulated) for both the main process and 
background processes. The measured and Monte Carlo simulated data are processed 
through filtering out invalid events based on quantities such as the total 
lepton charge.
</p>

#### Main Process
$$
H \rightarrow Z Z^{*} \rightarrow l^{+} l^{-} l^{+} l^{-} 
$$

#### Background Processes
$$
Z Z^{*} \rightarrow l^{+} l^{-} l^{+} l^{-}
$$
$$
Z \rightarrow l^{+} l^{-}
$$
$$
t \bar{t} \rightarrow l^{+} l^{-} + X
$$

#### Final Figure
<p align=center>
    <image src="original/higgs_zz.png" alt="final figure" width=500>
</p>

### Workflows
<p align=justify>
In essence, this codebase contains 3 different workflows that can be used to 
perform the processing of the ATLAS data using cloud computing techniques. Each 
workflow has been automated with a shell script, allowing users to utilise the 
workflows with minimal effort. Refer to the <strong><i>Usage</i></strong> 
section for more details.
</p>

+ **Docker Workflow**
    + A static workflow using Docker Compose.

+ **Kubernetes Static Workflow**
    + A static workflow using Kubernetes pods.

+ **Kubernetes KEDA Workflow**
    + An elastic workflow using Kubernetes pods with KEDA for autoscaling.

> [!NOTE]
> The format of commits for this codebase take inspiration from https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13 in an attempt to keep things organised and findable.


## Requirements
### Docker Desktop & Kubernetes (K8s)
<p align=justify>
The minimum requirement to utilise the workflows developed in this codebase is 
the installation of <strong><i>Docker Desktop</i></strong>. 
<strong><i>Docker Desktop</i></strong> enables the use of Docker containers 
which is required for all of the workflows in this codebase. It also enables 
the use of <strong><i>Kubernetes (K8s)</i></strong> which can be activated in 
the settings. To install <strong><i>Docker Desktop</i></strong>, follow the 
instructions in the Docker guides, which are linked in the 
<strong><i>References</i></strong> section.
</p>

#### Enables
+ **Docker Workflow**
+ **Kubernetes Static Workflow**

### Kubernetes Event Driven Autoscaling (KEDA)
<p align=justify>
To utilise the <strong><i>Kubernetes KEDA Workflow</i></strong> developed in 
this codebase, <strong><i>KEDA</i></strong> must be installed. The first step 
requires installing <strong><i>Helm</i></strong> which is a package manager for 
Kubernetes. <strong><i>KEDA</i></strong> can then be installed and activated 
using <strong><i>Helm</i></strong>. The guides on both the 
<strong><i>Helm</i></strong> and <strong><i>KEDA</i></strong> websites provide 
clear instructions on how to install them and are linked in the 
<strong><i>References</i></strong> section.
</p>

+ For quick reference, the commands for installing ***Helm*** and ***KEDA*** are also shown below.

#### Helm
```
$ curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
$ chmod 700 get_helm.sh
$ ./get_helm.sh
```

#### KEDA
```
$ helm repo add kedacore https://kedacore.github.io/charts
$ helm repo update
$ helm install keda kedacore/keda --namespace keda --create-namespace
```

#### Enables
+ **Kubernetes KEDA Workflow**


## Usage
### General
+ Clone the codebase and change directories into it.
```
$ git clone git@github.com:Pavan365/ATLAS-Data-Project.git
$ cd ATLAS-Data-Project
```

+ To build the Docker container images, run the following commands.
```
$ cd src
$ ./build-images.sh
```

> [!IMPORTANT]
> The batch size of each batch of data can be set in the ```./src/common/config.py``` file.
> Ensure the Docker container images are rebuilt after changing the batch size.

### Docker Workflow
#### Commands
+ To use the ***Docker Workflow***, run the following commands.
```
$ cd src
$ ./build-images.sh
$ ./docker-run.sh
```

> [!IMPORTANT]
> The number of worker replicas can be set in the ```./src/compose.yaml``` file.

#### Output
+ The output should be as shown below.
<p align=center>
    <image src="docs/docker-workflow.png" alt="docker workflow" width=800>
</p>

### Kubernetes Static Workflow
#### Commands
+ To use the ***Kubernetes Static Workflow***, run the following commands.
```
$ cd src
$ ./build-images.sh
$ ./kubernetes-run.sh
```

+ When prompted to use KEDA enter ***NO*** - ```(n, N, no, NO)```.
```
$ confirm: use KEDA (autoscaling)? [Y/N]: N
```

> [!IMPORTANT]
> The number of worker replicas can be set in the ```./src/kubernetes/higgs-worker.yaml``` file.

#### Output
+ The output should be as shown below.
<p align=center>
    <image src="docs/kubernetes-static-workflow.png" alt="kubernetes static workflow" width=800>
</p>

### Kubernetes KEDA Workflow
#### Commands
+ To use the ***Kubernetes KEDA Workflow***, run the following commands.
```
$ cd src
$ ./build-images.sh
$ ./kubernetes-run.sh
```

+ When prompted to use KEDA enter ***YES*** - ```(y, Y, yes, YES)```.
```
$ confirm: use KEDA (autoscaling)? [Y/N]: Y
```

> [!IMPORTANT]
> KEDA must be installed to use this workflow.

> [!IMPORTANT]
> The starting number of worker replicas can be set in the ```./src/kubernetes/higgs-worker.yaml``` file.
> It is recommended to set the starting number of worker replicas to **1** with this workflow.

#### Output
+ The output should be as shown below.
<p align=center>
    <image src="docs/kubernetes-keda-workflow.png" alt="kubernetes KEDA workflow" width=800>
</p>

+ To view how KEDA scaled the worker pods, run the following command.
```
$ kubectl get events
```
<p align=center>
    <image src="docs/kubernetes-keda-scaling.png" alt="kubernetes KEDA scaling" width=800>
</p>


## Codebase Structure
```
.
├── README.md
├── docs
│   ├── docker-workflow.png
│   ├── kubernetes-keda-scaling.png
│   ├── kubernetes-keda-workflow.png
│   └── kubernetes-static-workflow.png
├── environment.yaml
├── original
│   ├── higgs_zz.png
│   ├── higgs_zz.py
│   └── infofile.py
└── src
    ├── build-images.sh
    ├── common
    │   ├── comms.py
    │   ├── config.py
    │   ├── infofile.py
    │   └── requirements.txt
    ├── compose.yaml
    ├── docker-run.sh
    ├── keda
    │   ├── keda-auth.yaml
    │   ├── keda-scaler.yaml
    │   └── keda-secret.yaml
    ├── kubernetes
    │   ├── busybox-higgs-plot.yaml
    │   ├── higgs-manager.yaml
    │   ├── higgs-volume-claim.yaml
    │   ├── higgs-worker.yaml
    │   ├── rabbitmq-service.yaml
    │   └── rabbitmq.yaml
    ├── kubernetes-run.sh
    ├── manager
    │   ├── Dockerfile
    │   └── higgs_manager.py
    ├── output
    │   ├── higgs_zz_docker.png
    │   └── higgs_zz_kubernetes.png
    └── worker
        ├── Dockerfile
        └── higgs_worker.py
```

#### ```root```
+ ```README.md```: This ***README*** file.
+ ```environment.yaml```: The conda environment used for developing this project.

#### ```root/docs```
+ Contains images for this ***README*** file.

#### ```root/original```
+ Contains the original data processing code from the **ATLAS Open Data** examples.

#### ```root/src```
+ ```build-images.sh```: A shell script for building the manager and worker Docker container images.
+ ```compose.yaml```: A YAML file for configuring Docker Compose.
+ ```docker-run.sh```: A shell script for automating the Docker workflow.
+ ```kubernetes-run.sh```: A shell script for automating the Kubernetes workflows.

#### ```root/src/common```
+ Contains common files that both manager and worker containers use.

#### ```root/src/keda```
+ Contains YAML files for configuring KEDA for autoscaling workers.

#### ```root/src/kubernetes```
+ Contains YAML files for configuring the Kubernetes workflows.

#### ```root/src/manager```
+ Contains files for configuring the manager container.

#### ```root/src/output```
+ Contains the outputted figures from the Docker and Kubernetes workflows.

#### ```root/src/worker```
+ Contains files for configuring the worker container.


## References
#### ATLAS Open Data
+ https://opendata.atlas.cern/
+ https://github.com/atlas-outreach-data-tools/notebooks-collection-opendata

#### Docker
+ https://www.docker.com/products/docker-desktop/
+ https://docs.docker.com/

#### Kubernetes
+ https://kubernetes.io/docs/home/
+ https://docs.docker.com/desktop/features/kubernetes/

#### Helm
+ https://helm.sh/docs/intro/install/
+ https://helm.sh/docs/

#### KEDA
+ https://keda.sh/
+ https://keda.sh/docs/2.16/
+ https://keda.sh/docs/2.16/scalers/rabbitmq-queue/
