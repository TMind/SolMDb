#!/bin/bash
# Start MongoDB
mongod --fork --logpath /var/log/mongod.log --config /etc/mongod.conf
