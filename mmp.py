import numpy as np
import pickle
from MemoryMap import MemoryMapManager

class MemoryMapObject:

    def __init__(self, name):
        self.name = name


obj = {}

for i in range(10) :
    obj[i] = MemoryMapObject(f"Object {i}")

MyMemoryMap = MemoryMapManager('mydata.mmap',10)

if "Object 5" in MyMemoryMap.index:
    myobj = MyMemoryMap["Object 5"]
    print(myobj.name) # type: ignore
    
for object in obj.values():    
    MyMemoryMap[object.name] = object

myobj = MyMemoryMap["Object 5"]

print(myobj.name)

del MyMemoryMap