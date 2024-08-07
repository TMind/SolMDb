#!/bin/sh  
  
# Debug-Ausgaben hinzufügen  
set -x  
  
# Erstelle das Verzeichnis und setze die Berechtigungen  
mkdir -p /workspaces/mongodb/data/db  
chown -R mongodb:mongodb /workspaces/mongodb/data/db  
chmod -R 755 /workspaces/mongodb/data/db  
  
# Installiere Python-Abhängigkeiten  
pip install --user -r binder/requirements.txt  
