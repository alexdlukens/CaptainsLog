import docker
from docker.models.containers import Container
from typing import List
import logging

logger = logging.getLogger(__file__)

docker_client = docker.from_env()

def list_containers() -> List[Container]:
    
    containers = []
    try:
        containers = docker_client.containers.list(all=True)
    except:
        logger.exception("Failed to retrieve docker container list from daemon")
        pass
    return containers