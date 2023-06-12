import csv

class SynergyTemplate:

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.load_synergy_template()
        return cls._instance

    def load_synergy_template(self):
        self.synergies = {}
        self.from_csv('csv/synergies.csv')

    def add_synergy(self, name, weight, input_tags, output_tags):
        synergy = Synergy(name, weight, input_tags, output_tags)
        self.synergies[name] = synergy

    def remove_synergy(self, name):
        if name in self.synergies:
            del self.synergies[name]

    def get_synergies(self):
        return self.synergies

    def get_synergy_by_name(self, name):
        return self.synergies[name]        

    def get_synergies_by_tag(self, tag):
        input_synergies = [synergy for synergy in self.synergies.values() if tag in synergy.input_tags]
        output_synergies = [synergy for synergy in self.synergies.values() if tag in synergy.output_tags]
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
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row["name"]
                weight = float(row["weight"])
                input_tags = [tag.strip() for tag in row["input_tags"].split(",")]
                output_tags = [tag.strip() for tag in row["output_tags"].split(",")]
                self.add_synergy(name, weight, input_tags, output_tags)
   
class Synergy:
    def __init__(self, name, weight, input_tags, output_tags):
        self.name = name
        self.weight = weight
        self.input_tags = input_tags 
        self.output_tags = output_tags 
        self.output_counts = {tag: 0 for tag in output_tags}
        self.input_counts = {tag: 0 for tag in input_tags}

    def add_output_tag(self, tag, value=1):
        set(self.output_tags).update(tag)
        self.output_counts[tag] = value
    
    def add_input_tag(self, tag, value=1):
        set(self.input_tags).update(tag)        
        self.input_counts[tag] = value

    def get_input_tags(self):
        return self.input_tags
    
    def get_output_tags(self):
        return self.output_tags

    def is_output_tag(self,tag):
        return tag in self.output_tags
    
    def is_input_tag(self,tag):
        return tag in self.input_tags
    
    def set_output_count(self, tag, value=1):
        if tag in self.output_counts:
            if self.output_counts[tag] > 0:
                print(f"{tag} > 0 < {value} already! ")
            self.output_counts[tag] = value    

    def set_input_count(self, tag, value=1):
        if tag in self.input_counts:
            if self.input_counts[tag] > 0:
                print(f"{tag} > 0 < {value} already! ")
            self.input_counts[tag] = value
    
    def get_output_counts(self):
        return self.output_counts
    
    def get_input_counts(self):
        return self.input_counts
    
    def is_synergy(self):  
        has_nonzero_output = any(output_val > 0 for output_val in self.output_counts.values())
        has_nonzero_input = any(input_val > 0 for input_val in self.input_counts.values())
        return has_nonzero_output and has_nonzero_input

    def stats(self,stats,type):
        max = max(stats[self.name][type].keys())
        if type == 'input' :
            return self.output_counts / max
        if type == 'output' :
            return self.input_counts / max
        return None

    def __str__(self):
        output_counts_str = ", ".join([f"{tag}: {count}" for tag, count in self.output_counts.items()])
        input_counts_str = ", ".join([f"{tag}: {count}" for tag, count in self.input_counts.items()])
        output_counts_total = sum(self.get_output_counts().values())
        input_counts_total = sum(self.get_input_counts().values())
        return f"{self.name:<17}: {self.weight:<7} - output: {output_counts_str:>40} - input: {input_counts_str:>40} => {output_counts_total:<5.2g}^{input_counts_total:>5.2g}"
