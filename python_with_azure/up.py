from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.core.exceptions import ResourceNotFoundError
import os

# Configuration (unchanged)
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")

for var in ["AZURE_SUBSCRIPTION_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID"]:
    if not os.getenv(var):
        raise ValueError(f"Environment variable {var} not set.")
    
PREFIX = "OmerDevops"
LOCATION = "East US"
SSH_PUBLIC_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")

# Initialize credential and clients (unchanged)
credential = ClientSecretCredential(
    tenant_id=TENANT_ID,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)
compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)

# Create Resource Group (unchanged)
try:
    resource_client.resource_groups.get(f"{PREFIX}-rg")
    print(f"Resource group '{PREFIX}-rg' already exists.")
except ResourceNotFoundError:
    print(f"Creating resource group '{PREFIX}-rg'...")
    rg_params = {"location": LOCATION}
    resource_client.resource_groups.create_or_update(f"{PREFIX}-rg", rg_params)
    print(f"Resource group '{PREFIX}-rg' created.")

# Create Virtual Network (unchanged)
vnet_params = {
    "location": LOCATION,
    "address_space": {"address_prefixes": ["10.0.0.0/16"]}
}
try:
    vnet = network_client.virtual_networks.get(f"{PREFIX}-rg", f"{PREFIX}-network")
    print(f"Virtual network '{PREFIX}-network' already exists.")
except ResourceNotFoundError:
    print(f"Creating virtual network '{PREFIX}-network'...")
    vnet_result = network_client.virtual_networks.begin_create_or_update(
        f"{PREFIX}-rg",
        f"{PREFIX}-network",
        vnet_params
    ).result()
    print(f"Virtual network '{PREFIX}-network' created.")

# Create Subnet - store the subnet object regardless of creation
subnet_params = {"address_prefix": "10.0.2.0/24"}
try:
    subnet = network_client.subnets.get(f"{PREFIX}-rg", f"{PREFIX}-network", "internal")
    print(f"Subnet 'internal' already exists.")
except ResourceNotFoundError:
    print(f"Creating subnet 'internal'...")
    subnet = network_client.subnets.begin_create_or_update(
        f"{PREFIX}-rg",
        f"{PREFIX}-network",
        "internal",
        subnet_params
    ).result()
    print(f"Subnet 'internal' created.")

# Create Public IP - store the public_ip object regardless of creation
public_ip_params = {
    "location": LOCATION,
    "sku": {"name": "Basic"},
    "public_ip_allocation_method": "Dynamic"
}
try:
    public_ip = network_client.public_ip_addresses.get(f"{PREFIX}-rg", f"{PREFIX}-public-ip")
    print(f"Public IP '{PREFIX}-public-ip' already exists.")
except ResourceNotFoundError:
    print(f"Creating public IP '{PREFIX}-public-ip'...")
    public_ip = network_client.public_ip_addresses.begin_create_or_update(
        f"{PREFIX}-rg",
        f"{PREFIX}-public-ip",
        public_ip_params
    ).result()
    print(f"Public IP '{PREFIX}-public-ip' created.")

# Create Network Security Group (unchanged)
nsg_params = {
    "location": LOCATION,
    "security_rules": [
        {
            "name": "SSH",
            "properties": {
                "priority": 1001,
                "direction": "Inbound",
                "access": "Allow",
                "protocol": "Tcp",
                "sourcePortRange": "*",
                "destinationPortRange": "22",
                "sourceAddressPrefix": "*",
                "destinationAddressPrefix": "*"
            }
        }
    ]
}
try:
    nsg = network_client.network_security_groups.get(f"{PREFIX}-rg", f"{PREFIX}-nsg")
    print(f"Network Security Group '{PREFIX}-nsg' already exists.")
except ResourceNotFoundError:
    print(f"Creating Network Security Group '{PREFIX}-nsg'...")
    nsg_result = network_client.network_security_groups.begin_create_or_update(
        f"{PREFIX}-rg",
        f"{PREFIX}-nsg",
        nsg_params
    ).result()
    print(f"Network Security Group '{PREFIX}-nsg' created.")

# Create Network Interface - use subnet and public_ip from above
nic_params = {
    "location": LOCATION,
    "ip_configurations": [
        {
            "name": f"{PREFIX}-nic-config",
            "subnet": {"id": subnet.id},  # Use subnet instead of subnet_result
            "public_ip_address": {"id": public_ip.id}  # Use public_ip instead of public_ip_result
        }
    ]
}
try:
    nic = network_client.network_interfaces.get(f"{PREFIX}-rg", f"{PREFIX}-nic")
    print(f"Network Interface '{PREFIX}-nic' already exists.")
except ResourceNotFoundError:
    print(f"Creating Network Interface '{PREFIX}-nic'...")
    nic = network_client.network_interfaces.begin_create_or_update(
        f"{PREFIX}-rg",
        f"{PREFIX}-nic",
        nic_params
    ).result()
    print(f"Network Interface '{PREFIX}-nic' created.")

# Read SSH public key (unchanged)
with open(SSH_PUBLIC_KEY_PATH, "r") as ssh_file:
    ssh_public_key = ssh_file.read().strip()

# Create Virtual Machine - use nic from above
vm_params = {
    "location": LOCATION,
    "hardware_profile": {"vm_size": "Standard_B1s"},
    "storage_profile": {
        "image_reference": {
            "publisher": "Canonical",
            "offer": "UbuntuServer",
            "sku": "18.04-LTS",
            "version": "latest"
        },
        "os_disk": {
            "name": f"{PREFIX}-os-disk",
            "caching": "ReadWrite",
            "create_option": "FromImage",
            "managed_disk": {"storage_account_type": "Standard_LRS"}
        }
    },
    "os_profile": {
        "computer_name": f"{PREFIX}-vm",
        "admin_username": "azureuser",
        "linux_configuration": {
            "disable_password_authentication": True,
            "ssh": {
                "public_keys": [
                    {
                        "path": "/home/azureuser/.ssh/authorized_keys",
                        "key_data": ssh_public_key
                    }
                ]
            }
        }
    },
    "network_profile": {
        "network_interfaces": [{"id": nic.id}]  # Use nic instead of nic_result
    }
}
try:
    vm = compute_client.virtual_machines.get(f"{PREFIX}-rg", f"{PREFIX}-vm")
    print(f"Virtual Machine '{PREFIX}-vm' already exists.")
except ResourceNotFoundError:
    print(f"Creating Virtual Machine '{PREFIX}-vm'...")
    vm = compute_client.virtual_machines.begin_create_or_update(
        f"{PREFIX}-rg",
        f"{PREFIX}-vm",
        vm_params
    ).result()
    print(f"Virtual Machine '{PREFIX}-vm' created.")

print("Infrastructure deployment completed.")