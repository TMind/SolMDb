#!/bin/sh  
  
# Enable debugging  
set -x  
  
# Create the directory and set permissions  
mkdir -p /workspaces/mongodb/data/db  
chown -R mongodb:mongodb /workspaces/mongodb/data/db  
chmod -R 755 /workspaces/mongodb/data/db  
  
# Install Conda dependencies from environment.yml  
conda env update -f binder/environment.yml  
  
# Initialize Conda for bash shell  
conda init bash  
  
# Activate the Conda environment in the current shell  
source ~/.bashrc  
conda activate SolDB-Conda  
  
# Install ipykernel in the Conda environment  
conda install -y -n SolDB-Conda ipykernel  
  
# Register the Conda environment as a Jupyter kernel  
python -m ipykernel install --user --name SolDB-Conda --display-name "SolDB-Conda"  
  
# Start MongoDB service  
sudo service mongod start  
  
# Optional: Verify MongoDB is running  
sudo service mongod status  