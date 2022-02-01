import os
import docker
import subprocess
import time
import kubernetes
import shutil

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
chartLocation = "helm\\pizza"


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
            process.communicate(timeout=10000)
    except Exception as e:
        errorMessage = "***** Failed to run cli command using subprocess maybe timeout!\n ErrorMessage: [" + str(
            e) + "]"
        raise Exception("Error: " + str(errorMessage))
    if process.returncode != 0:
        errorMessage = "***** Failed to run command!\n\n*** Error Meassage: [" + str(
            error) + "]***\n\n*** Comannd Run: [" + command + "]***\n\n"
        raise Exception("Error: " + str(errorMessage))
    return output


def deployNewImageToCluster():
    cmd = runCliCmd("kubectl apply -f deployment.yaml")
    print(cmd)


def executeApiRequest(port):
    apiRequestReuslt = runCliCmd("curl -i 127.0.0.1:" + str(port))
    if "HTTP/1.1 200 OK" not in apiRequestReuslt:
        raise Exception("Api request failed\n request result: " + str(apiRequestReuslt))
    print("Api request completed successfully!")


def runUnitTests():
    os.chdir('app')
    os.system("npm install")
    exitCode = os.system("npm test")
    if exitCode != 0:
        raise Exception("Unit test failed!!")
    shutil.rmtree("node_modules")
    os.remove("package-lock.json")
    os.chdir("..")
    print("Unit tests passed successfully!")


def buildDockerImage(repository, imageTag):
    print("Building docker image...")
    client.images.build(path=".", tag=repository + "/" + imageTag)
    print("Docker image was built successfully!")


def pushDockerImage(repository, imageTag):
    print("Pushing docker image...")
    client.images.push(repository=repository, tag=imageTag)
    print("Docker image was pushed successfully!")


def tagDockerImage(repository, imageTag, newTag):
    cmd = runCliCmd("docker tag " + repository + ":" + imageTag + " " + repository + ":" + newTag)
    print(cmd)


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
    isDeploymentReady = False
    retries = 12
    count = 0
    while not isDeploymentReady and count < retries:
        deployment = getDeployment(namespace, deploymentName)
        readyReplicas = deployment.status.ready_replicas
        if readyReplicas is not None and readyReplicas == replicas:
            isDeploymentReady = True
        else:
            print("deployment is not ready - sleeping 5 seconds and checking again")
            count += 1
            time.sleep(5)


def helmUninstall(chartName):
    print("uninstalling existing helm chart")
    uninstallResult = None
    try:
        uninstallResult = runCliCmd("helm uninstall " + chartName)
    except Exception as e:
        if "release: not found" in str(e):
            print("chart is not installed - nothing to remove")
        else:
            raise Exception("Failed uninstalling chart: [" + str(chartName) + "]\nError: [" + str(e) + "]")

    if uninstallResult is not None and "release \"" + chartName + "\" uninstalled" not in uninstallResult:
        raise Exception("Failed uninstalling chart: [" + str(chartName) + "]\nError: [" + str(uninstallResult) + "]")

    # isNamespaceRemoved = False
    # retries = 12
    # count = 0
    # while not isNamespaceRemoved and count < retries:
    #     namespaces = kubernetes.client.CoreV1Api().list_namespace()
    #     for namespace in namespaces.items:
    #         if namespace.metadata.name == namespace:
    #             print("namespace is not deleted yet - waiting...")
    #             time.sleep(5)
    #             count += 1
    #             break
    #         else:
    #             isNamespaceRemoved = True
    #
    # if not isNamespaceRemoved:
    #     raise Exception("namespace wasnt removed - helm uninstall failed!!")
    time.sleep(60)


def helmInstall(chartName, chartLocation, imageTag, replicas, namespace, name, port):
    print("installing helm chart")
    cmd = runCliCmd("helm install " + chartName + " " + chartLocation +
                    " --set deployment.tag=" + imageTag +
                    " --set deployment.replicas=" + str(replicas) +
                    " --set namespace.name=" + namespace +
                    " --set deployment.name=" + name +
                    " --set general.port=" + str(port))
    print(cmd)


if __name__ == '__main__':
    runUnitTests()
    buildDockerImage(repository, imageTag)
    pushDockerImage(repository, imageTag)
    os.system("kind create cluster --name " + clusterName + " --config kindClusterConfig.yaml")
    os.system("kubectl config set-cluster " + clusterName)
    kubernetes.config.load_config()
    helmUninstall(chartName)
    helmInstall(chartName, chartLocation, imageTag, replicas, namespace, name, port)
    checkDeploymentIsReady(namespace, name, replicas)
    executeApiRequest(port)
    tagDockerImage(repository, imageTag, imageTagTested)
    pushDockerImage(repository, imageTagTested)
    os.system("kind delete cluster --name " + clusterName)
