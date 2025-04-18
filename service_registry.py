import consul
import os
import socket
import threading
import time
import logging

logger = logging.getLogger("workflow_service")

class ServiceRegistry:
    def __init__(self):
        self.consul_host = os.getenv("CONSUL_HOST", "consul")
        self.consul_port = int(os.getenv("CONSUL_PORT", "8500"))
        self.service_name = os.getenv("SERVICE_NAME", "workflow")
        self.service_port = int(os.getenv("SERVICE_PORT", "8006"))
        # Use the container name as registered in docker-compose
        self.service_id = f"{self.service_name}-{socket.gethostname()}"
        
        # Create Consul client
        self.consul = consul.Consul(host=self.consul_host, port=self.consul_port)
        self.is_registered = False
        self.heartbeat_thread = None
        logger.info(f"Service registry initialized for {self.service_name}")

    def register_service(self):
        """Register service with Consul"""
        try:
            # Get container IP address instead of hostname
            container_ip = socket.gethostbyname(socket.gethostname())
            
            # Register service with IP address, not hostname
            self.consul.agent.service.register(
                name=self.service_name,
                service_id=self.service_id,
                address=container_ip,  # Use IP address instead of hostname
                port=self.service_port,
                check={
                    "http": f"http://{container_ip}:{self.service_port}/health",
                    "interval": "15s",
                    "timeout": "3s"
                }
            )
            self.is_registered = True
            logger.info(f"Service registered with Consul: {self.service_name} at {container_ip}:{self.service_port}")
        except Exception as e:
            logger.error(f"Failed to register service: {str(e)}")

    def deregister_service(self):
        """Deregister service from Consul"""
        try:
            if self.is_registered:
                self.consul.agent.service.deregister(service_id=self.service_id)
                self.is_registered = False
                logger.info(f"Service deregistered from Consul: {self.service_id}")
        except Exception as e:
            logger.error(f"Failed to deregister service: {str(e)}")

    def start_heartbeat(self):
        """Start heartbeat thread"""
        if self.heartbeat_thread is None:
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            logger.info("Heartbeat thread started")

    def _heartbeat_loop(self):
        """Heartbeat loop to keep service registered"""
        while True:
            try:
                if not self.is_registered:
                    self.register_service()
                time.sleep(60)  
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
                time.sleep(10) 