# pizza app automation

**prerequisites:**
    - kind (k8s cluster to deploy image and test it)
    - docker 
    - python - modules to install: kubernetes, docker
    - helm
    
**app folder**
 -  contains the pizza app
 
**helm folder**
 -  contains the helm chart -  deploys a service, namespace and a deployment
 
**Dockerfile**
 - builds the docker images
 
**automation.py**
 - runs the automation for the repo:
    1. runs unit tests
    2. builds the image
    3. pushes it to a repository
    4. creates a kind cluster if not exists already
    5. uninstall helm chart if existed on the cluster
    6. deploys the helm chart
    7. checks deployment is ready
    8. sends an api request to the pizza app
    9. tags the image as tested
    10. pushes the image with tested tag to a repository
    11. destroys the kind cluster 
    
**kindClusterConfig.yaml**
    - a config being used when creating the kind cluster    