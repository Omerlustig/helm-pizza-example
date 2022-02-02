import os
import docker
import subprocess
import time
import kubernetes
import shutil
import logging

# install pycurl
client = docker.from_env()
imageTag = "ready4test"
repository = "omerlustig/pizza"
replicas = 1
chartName = "pizza"
clusterName = "pizza"
namespace = "example"
name = "big-pizza"
imageTagTested = "tested"
port = 3000
chartLocation = os.path.join("helm", "pizza")


def getLogger(name):
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log = logging.getLogger(name=name)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log


logger = getLogger("pizza-automation")


def runCliCmd(command):
    output = ""
    error = ""
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                              universal_newlines=True) as process:
            for b in process.stdout:
                output += b
            for c in process.stderr:
                error += c
    except Exception as e:
        errorMessage = "***** Failed to run cli command using subprocess maybe timeout!\n ErrorMessage: [" + str(
            e) + "]"
        raise Exception("Error: " + str(errorMessage))
    if process.returncode != 0:
        errorMessage = "***** Failed to run command!\n\n*** Error Meassage: [" + str(
            error) + "]***\n\n*** Comannd Run: [" + command + "]***\n\n"
        raise Exception("Error: " + str(errorMessage))
    return output


def executeApiRequest(port):
    logger.info("Executing api request...")
    apiRequestReuslt = runCliCmd("curl -i 127.0.0.1:" + str(port))
    if "HTTP/1.1 200 OK" not in apiRequestReuslt:
        raise Exception("Api request failed\n request result: " + str(apiRequestReuslt))
    logger.info("Api request completed successfully!")


def runUnitTests():
    logger.info("Running unit tests...")
    os.chdir('pizza-express-master')
    os.system("npm install")
    exitCode = os.system("npm test")
    if exitCode != 0:
        raise Exception("Unit test failed!!")
    shutil.rmtree("node_modules")
    os.remove("package-lock.json")
    os.chdir("..")
    logger.info("Unit tests passed successfully!")


def buildDockerImage(repository, imageTag):
    logger.info("Building docker image...")
    client.images.build(path=".", tag=repository + ":" + imageTag)
    logger.info("Docker image was built successfully!")


def pushDockerImage(repository, imageTag):
    logger.info("Pushing docker image...")
    client.images.push(repository=repository, tag=imageTag)
    logger.info("Docker image was pushed successfully!")


def tagDockerImage(repository, imageTag, newTag):
    logger.info("Tagging docker image...")
    runCliCmd("docker tag " + repository + ":" + imageTag + " " + repository + ":" + newTag)
    logger.info("Docker image wat tagged successfully!")


def getDeployment(namespace, deploymentName):
    kubeApi = kubernetes.client.AppsV1Api()
    isDeploymentFound = False
    deploymentToReturn = None
    deployments = kubeApi.list_namespaced_deployment(namespace=namespace)
    retries = 12
    count = 0
    while not isDeploymentFound and count < retries:
        for deployment in deployments.items:
            if deployment.metadata.name == deploymentName:
                isDeploymentFound = True
                deploymentToReturn = deployment
                break
        count += 1
        time.sleep(5)

    if isDeploymentFound:
        return deploymentToReturn
    else:
        raise Exception(
            "Could not find deployment: [" + str(deploymentName) + "] in namespace [" + str(namespace) + "]")


def checkDeploymentIsReady(namespace, deploymentName, replicas):
    logger.info("Checking deployment is ready...")
    isDeploymentReady = False
    retries = 12
    count = 0
    while not isDeploymentReady and count < retries:
        deployment = getDeployment(namespace, deploymentName)
        readyReplicas = deployment.status.ready_replicas
        if readyReplicas is not None and readyReplicas == replicas:
            isDeploymentReady = True
        else:
            logger.info("deployment is not ready - sleeping 5 seconds and checking again")
            count += 1
            time.sleep(5)


def helmUninstall(chartName):
    logger.info("uninstalling existing helm chart")
    uninstallResult = None
    isChartAlreadyInstalled = True
    try:
        uninstallResult = runCliCmd("helm uninstall " + chartName)
    except Exception as e:
        if "release: not found" in str(e):
            logger.info("chart is not installed - nothing to remove")
            isChartAlreadyInstalled = False
        else:
            raise Exception("Failed uninstalling chart: [" + str(chartName) + "]\nError: [" + str(e) + "]")

    if uninstallResult is not None and "release \"" + chartName + "\" uninstalled" not in uninstallResult:
        raise Exception("Failed uninstalling chart: [" + str(chartName) + "]\nError: [" + str(uninstallResult) + "]")

    if isChartAlreadyInstalled:
        time.sleep(60)


def helmInstall(chartName, chartLocation, imageTag, replicas, namespace, name, port):
    logger.info("Installing helm chart...")
    cmd = runCliCmd("helm install " + chartName + " " + chartLocation +
                    " --set deployment.tag=" + imageTag +
                    " --set deployment.replicas=" + str(replicas) +
                    " --set namespace.name=" + namespace +
                    " --set deployment.name=" + name +
                    " --set general.port=" + str(port))
    logger.info("Helm chart was installed successfully!")


def createKindCluster(clusterName):
    logger.info("Creating kind cluster")
    os.system("kind create cluster --name " + clusterName + " --config kindClusterConfig.yaml")
    os.system("kubectl config set-cluster " + clusterName)
    kubernetes.config.load_config()
    logger.info("Kind cluster was created successfully")


def deleteKindCluster(clusterName):
    logger.info("Deleting kind cluster")
    runCliCmd("kind delete cluster --name " + clusterName)
    logger.info("Kind cluster was deleted successfully")


if __name__ == '__main__':
    runUnitTests()
    buildDockerImage(repository, imageTag)
    pushDockerImage(repository, imageTag)
    createKindCluster(clusterName)
    helmUninstall(chartName)
    helmInstall(chartName, chartLocation, imageTag, replicas, namespace, name, port)
    checkDeploymentIsReady(namespace, name, replicas)
    executeApiRequest(port)
    tagDockerImage(repository, imageTag, imageTagTested)
    pushDockerImage(repository, imageTagTested)
    deleteKindCluster(clusterName)
