#!/bin/bash

# Script to create an Azure Service Principal and export credentials as environment variables

# Variables
SP_NAME="OmerDevopsSP"
ROLE="Contributor"

# Retrieve SUBSCRIPTION_ID from the environment variable AZURE_SUBSCRIPTION_ID
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"

# Check if SUBSCRIPTION_ID is set
if [ -z "$SUBSCRIPTION_ID" ]; then
    echo "Error: AZURE_SUBSCRIPTION_ID environment variable is not set. Please set it before running the script."
    echo "Example: export AZURE_SUBSCRIPTION_ID='3f79a68d-cf0d-4291-a31f-185897f7fda1'"
    exit 1
fi

SCOPE="/subscriptions/$SUBSCRIPTION_ID"

# Create the Service Principal and capture the output
echo "Creating Service Principal: $SP_NAME..."
SP_OUTPUT=$(az ad sp create-for-rbac --name "$SP_NAME" --role "$ROLE" --scopes "$SCOPE" --output json)

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to create Service Principal. Please check your Azure CLI setup and permissions."
    exit 1
fi

# Extract appId, password, and tenantId from the output
CLIENT_ID=$(echo "$SP_OUTPUT" | jq -r '.appId')
CLIENT_SECRET=$(echo "$SP_OUTPUT" | jq -r '.password')
TENANT_ID=$(echo "$SP_OUTPUT" | jq -r '.tenant')

# Validate extracted values
if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$TENANT_ID" ]; then
    echo "Error: Could not extract appId, password, or tenantId from the output."
    exit 1
fi

# Export the environment variables
export AZURE_CLIENT_ID="$CLIENT_ID"
export AZURE_CLIENT_SECRET="$CLIENT_SECRET"
export AZURE_TENANT_ID="$TENANT_ID"

# Confirm the variables are set
echo "Service Principal created successfully!"
echo "AZURE_CLIENT_ID: $AZURE_CLIENT_ID"
echo "AZURE_CLIENT_SECRET: $AZURE_CLIENT_SECRET"
echo "AZURE_TENANT_ID: $AZURE_TENANT_ID"

# Optional: Add the exports to the current shell session (e.g., ~/.bashrc or ~/.zshrc)
# Uncomment the following lines if you want to persist these variables
# echo "export AZURE_CLIENT_ID=$AZURE_CLIENT_ID" >> ~/.bashrc
# echo "export AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET" >> ~/.bashrc
# echo "export AZURE_TENANT_ID=$AZURE_TENANT_ID" >> ~/.bashrc
# source ~/.bashrc

echo "Done! You can now use these credentials for Azure authentication."