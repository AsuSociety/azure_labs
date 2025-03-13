#!/bin/bash -ex

# Load configuration from config.env
source config.env

# parameters
export PERSONAL_ACCESS_TOKEN=$(cat ~/.azure_devops_token) # Read the personal access token from the file
export ACR_NAME="omeracrregistry$RANDOM"

# Install Azure CLI if not already installed
if ! command -v az &> /dev/null; then
    brew update && brew install azure-cli
fi

# Login to Azure
# az login

# Configure Azure DevOps defaults
az devops configure --defaults organization="https://dev.azure.com/${ORGANIZATION}" project="${PROJECT}"

# Create Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic
az acr update -n $ACR_NAME --admin-enabled true

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Create repository if it doesn't exist
EXISTING_REPO=$(az repos list --query "[?name=='${REPO_NAME}'].name" -o tsv)
if [ -z "${EXISTING_REPO}" ]
then
    echo "Creating repository ${REPO_NAME}"
    az repos create --name "${REPO_NAME}" > /dev/null
else
    echo "Repository [${REPO_NAME}] already exists."
fi

# Set up repository
REPO_URL="https://${PERSONAL_ACCESS_TOKEN}@dev.azure.com/markveltzer/training/_git/${REPO_NAME}"

cd project
rm -rf .git
git init
git remote add origin "${REPO_URL}"
git add .
git commit -m "first commit of all files"
git push -u origin master



# Create the configuration file with proper variable substitution
cat > endpoint-config.json << EOF
{
  "name": "omer-connect",
  "type": "dockerregistry",
  "url": "https://${ACR_NAME}.azurecr.io",
  "authorization": {
    "parameters": {
      "registry": "https://${ACR_NAME}.azurecr.io",
      "username": "$ACR_USERNAME",
      "password": "$ACR_PASSWORD",
      "email": "user@example.com"
    },
    "scheme": "UsernamePassword"
  },
  "isShared": true,
  "isReady": true,
  "owner": "Library"
}
EOF

# Create the service endpoint using the configuration file
az devops service-endpoint create \
    --service-endpoint-configuration endpoint-config.json \
    --project "$PROJECT" \
    --organization "https://dev.azure.com/${ORGANIZATION}"



# Replace placeholders in the JSON file with actual values
# sed -i '' "s/\${ACR_NAME}/$ACR_NAME/g" endpoint-config.json
# sed -i '' "s/\${ACR_USERNAME}/$ACR_USERNAME/g" endpoint-config.json
# sed -i '' "s/\${ACR_PASSWORD}/$ACR_PASSWORD/g" endpoint-config.json

# Create a generic service connection
# az devops service-endpoint create \
# 	 --service-endpoint-configuration ./endpoint-config.json

# Verify the connection was created
if [ $? -eq 0 ]; then
    echo "Service connection created successfully"
else
    echo "Failed to create service connection"
    exit 1
fi

# Create and run pipeline
az pipelines create \
    --name "omerPipeline" \
    --repository "$REPO_NAME" \
    --repository-type tfsgit \
    --branch master \
    --yml-path azure-pipelines.yml \
    --project "$PROJECT" \
    --organization "https://dev.azure.com/${ORGANIZATION}" \

# Verify the pipeline was created
if [ $? -eq 0 ]; then
	echo "Pipeline created successfully"
else
	echo "Failed to create pipeline"
	exit 1
fi


cd ..