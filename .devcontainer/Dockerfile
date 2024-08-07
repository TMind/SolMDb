# Use the universal base image
FROM mcr.microsoft.com/devcontainers/universal:2

# Install MongoDB
RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list \
    && apt-get update \
    && apt-get install -y mongodb-org

# Install Python packages using pip  
# COPY binder/requirements.txt /workspaces/requirements.txt  
# RUN pip install --no-cache-dir -r /workspaces/requirements.txt

# Hold packages to prevent unintended upgrades
RUN echo "mongodb-org hold" | dpkg --set-selections \
    && echo "mongodb-org-server hold" | dpkg --set-selections \
    && echo "mongodb-org-shell hold" | dpkg --set-selections \
    && echo "mongodb-org-mongos hold" | dpkg --set-selections \
    && echo "mongodb-org-tools hold" | dpkg --set-selections

# Copy post-create.sh to image
COPY .devcontainer/post-create.sh /usr/local/bin/post-create.sh  
RUN chmod +x /usr/local/bin/post-create.sh  
