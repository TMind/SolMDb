from dataclasses import dataclass, asdict
from MongoDB.DatabaseManager import DatabaseObject
from dataclasses import field
import csv

@dataclass
class SynergyTemplateData:
    synergies: dict  # Assuming `synergies` is a list of Synergy objects

class SynergyTemplate(DatabaseObject):

    _instance = None

    def __new__(cls, csvfilename=None):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.load_synergy_template(csvfilename)
        return cls._instance

    def to_data(self):
        synergy_data_list = {synergy.name : synergy for synergy in self.synergies.values()}
        return SynergyTemplateData(synergies=synergy_data_list)

    @classmethod
    def from_data(cls, data):
        instance = cls()
        for synergyName, synergy_data in data.synergies:
            synergy = Synergy.from_data(synergy_data)
            instance.synergies[synergyName] = synergy
        return instance

    def save(self):
        for name, synergy in self.synergies.items():
            synergy.save(name, collection_name='SynergyTemplate')

    def load_synergy_template(self, csvfilename=None):
        self.synergies = {}        
        csvpathname = f"csv/{csvfilename or 'synergies'}.csv"
        self.from_csv(csvpathname)

    def add_synergy(self, name, weight, input_tags, output_tags, children_data={}):
        synergy_data = SynergyData(name, weight, input_tags, output_tags, children_data)
        synergy = Synergy(synergy_data)
        self.synergies[name] = synergy

    def remove_synergy(self, name):
        if name in self.synergies:
            del self.synergies[name]

    def get_synergies(self):
        return self.synergies

    def get_synergy_by_name(self, name):
        return self.synergies[name]        

    def get_synergies_by_tag(self, tag, input_or_output="IO"):
        input_synergies = [synergy for synergy in self.synergies.values() if tag in synergy.input_tags]
        output_synergies = [synergy for synergy in self.synergies.values() if tag in synergy.output_tags]
        
        if input_or_output == "I":
            return input_synergies
        elif input_or_output == "O":
            return output_synergies
        else:
            return input_synergies + output_synergies

    def get_output_tags_by_synergy(self, synergyname):
        synergy = self.get_synergy_by_name(synergyname)
        return synergy.output_tags

    def get_input_tags_by_synergy(self, synergyname):
        synergy = self.get_synergy_by_name(synergyname)
        return synergy.input_tags

    def get_output_tags(self):
        output_tags = set()
        for synergy in self.synergies.values():
            output_tags.update(synergy.output_tags)
        return output_tags

    def get_input_tags(self):
        input_tags = set()
        for synergy in self.synergies.values():
            input_tags.update(synergy.input_tags)
        return input_tags
    
    def set_synergy_rows(self, rows):
        
        syn_keys = list(self.synergies.keys())
        for key in syn_keys:
            if key not in rows:        
                self.remove_synergy(key)

    def __str__(self):
        output = "Synergies:\n"
        for name, synergy in self.synergies.items():
            output += f"{synergy}\n"
        return output
    
    def to_csv(self, filename):
        fieldnames = ["name", "weight", "input_tags", "output_tags"]
        rows = []
        for synergy in self.synergies.values():
            rows.append({
                "name": synergy.name,
                "weight": synergy.weight,
                "input_tags": ", ".join(synergy.input_tags),
                "output_tags": ", ".join(synergy.output_tags)
            })

        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def from_csv(self, filename):
        
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                name = row["name"]
                weight = float(row["weight"])
                input_tags = [tag.strip() for tag in row["input_tags"].split(",")]
                output_tags = [tag.strip() for tag in row["output_tags"].split(",")]
                children_data = {}
                children_data.update({input_tag : 'Input' for input_tag in input_tags})
                children_data.update({output_tag : 'Output' for output_tag in output_tags})
                self.add_synergy(name, weight, input_tags, output_tags, children_data)
        for synergy in self.synergies.values():
            synergy.save()
        

    def get_collection_names(self):
        return self.synergies


@dataclass
class SynergyData:
    name: str   = ''
    weight: float   = 0.0
    input_tags: list    = field(default_factory=list)
    output_tags: list   = field(default_factory=list)    
    children_data: dict = field(default_factory=dict)

class Synergy(DatabaseObject):

    def __init__(self, data: SynergyData):
        super().__init__(data)

    def get_input_tags(self):
        return self.data.input_tags
    
    def get_output_tags(self):
        return self.data.output_tags

    def __str__(self):
        return f"{self.data}"
    
    def to_data(self):
        # Convert the SynergyData dataclass to a dictionary
        return self.data

    @classmethod
    def from_data(cls, data):
        # Create a new Synergy instance using the unpacked data
        return cls(data['name'], data['weight'], data['input_tags'], data['output_tags'])
    
    def get_collection_names(self):
        return self
    