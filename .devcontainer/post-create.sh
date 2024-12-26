#!/bin/sh  
  
# Enable debugging  
set -x  
  
# Create the directory and set permissions  
mkdir -p /workspaces/mongodb/data/db  
chown -R mongodb:mongodb /workspaces/mongodb/data/db  
chmod -R 755 /workspaces/mongodb/data/db  

mkdir -p /workspaces/mongodb/logs
chown -R mongodb:mongodb /workspaces/mongodb/logs
chmod -R 755 /workspaces/mongodb/logs
  
# Install Conda dependencies from environment.yml  
conda env update -f /workspaces/SolMDb/binder/environment.yml  
  
# Initialize Conda for bash shell  
conda init bash  
  
# Activate the Conda environment in the current shell  
source ~/.bashrc  
conda activate SolDB-Conda  
  
# Install ipykernel in the Conda environment  
conda install -y -n SolDB-Conda ipykernel  
  
# Register the Conda environment as a Jupyter kernel  
python -m ipykernel install --user --name SolDB-Conda --display-name "SolDB-Conda"  
  
# Start MongoDB with a log file
nohup mongod --dbpath /workspaces/mongodb/data/db \
       --logpath /workspaces/mongodb/logs/mongod.log &