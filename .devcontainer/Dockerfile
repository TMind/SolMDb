# Use the universal base image
FROM mcr.microsoft.com/devcontainers/universal:2

# Install MongoDB
RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list \
    && apt-get update \
    && apt-get install -y mongodb-org

# Install Python packages using pip  
COPY binder/requirements.txt /tmp/requirements.txt  
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Hold packages to prevent unintended upgrades
RUN echo "mongodb-org hold" | dpkg --set-selections \
    && echo "mongodb-org-server hold" | dpkg --set-selections \
    && echo "mongodb-org-shell hold" | dpkg --set-selections \
    && echo "mongodb-org-mongos hold" | dpkg --set-selections \
    && echo "mongodb-org-tools hold" | dpkg --set-selections

# Create a custom entrypoint script
RUN echo '#!/bin/bash' > /usr/local/bin/start-mongo.sh \
    && echo 'mongod --logpath /var/log/mongod.log --config /etc/mongod.conf' >> /usr/local/bin/start-mongo.sh >> /usr/local/bin/start-mongo.sh \
    && chmod +x /usr/local/bin/start-mongo.sh

# Set the container to run the MongoDB starter script as the entrypoint  
ENTRYPOINT ["/usr/local/bin/start-mongo.sh"] 
