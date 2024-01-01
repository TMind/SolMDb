from Synergy import SynergyTemplate, Synergy
from Interface import Interface, InterfaceCollection
from Card_Library import Entity, Card
from UniversalLibrary import UniversalLibrary
import GlobalVariables
import os

GlobalVariables.username = 'tmind'
ucl_paths = [os.path.join('csv', 'sff.csv'), os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]

#Read Entities and Forgeborns from Files into Database
myUCL = UniversalLibrary(GlobalVariables.username, *ucl_paths)
myEntity = Entity.load('Entities', 'Adept')




myTemplate = SynergyTemplate()
myTemplate.save()
mySynergy = myTemplate.synergies['MAGE']
mySynergy.save('MAGE')
print(myTemplate)

myInterface = Interface('MAGE','Mage',1,'')
myInterface.save('MAGE')

print(myInterface)
