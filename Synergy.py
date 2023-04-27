import math
import collections

Synerginary = {
    #        <NAME>          <WEIGHT>  <TRIGGER>                       <SOURCE>
            "BEAST"       :  [ 1.0,    ["Beast Synergy"            ],[ "Beast"                  ]],     
            "DINOSAUR"    :  [ 1.0,    ["Dinosaur Synergy"         ],[ "Dinosaur"               ]],
            "MAGE"        :  [ 1.0,    ["Mage Synergy"             ],[ "Mage"                   ]],
            "ROBOT"       :  [ 1.0,    ["Robot Synergy"            ],[ "Robot"                  ]],
            "SCIENTIST"   :  [ 1.0,    ["Scientist Synergy"        ],[ "Scientist"              ]],
            "SPIRIT"      :  [ 1.0,    ["Spirit Synergy"           ],[ "Spirit"                 ]],
            "WARRIOR"     :  [ 1.0,    ["Warrior Synergy"          ],[ "Warrior"                ]],
            "ZOMBIE"      :  [ 1.0,    ["Zombie Synergy"           ],[ "Zombie"                 ]],                
            "MINION"      :  [ 1.0,    ["Minion Synergy"           ],[ "Minion"                 ]],
            "DRAGON"      :  [ 1.0,    ["Dragon Synergy"           ],[ "Dragon"                 ]],
            "ELEMENTAL"   :  [ 1.0,    ["Elemental Synergy"        ],[ "Elemental"              ]],                
            "PLANT"       :  [ 1.0,    ["Plant Synergy"            ],[ "Plant"                  ]],

            "SPELL"       :  [ 0.5,    ["Spell Synergy"            ],[ "Spell"                  ]],
            "HEALING"     :  [ 1.0,    ["Healing Synergy"          ],[ "Healing Source"         ]],
            "MOVEMENT"    :  [ 1.0,    ["Movement Benefit"         ],[ "Movement"               ]],
            "ARMOR"       :  [ 1.0,    ["Armor Synergy"            ],[ "Armor","Armor Giver "   ]],
            "ACTIVATION"  :  [ 1.0,    ["Ready"                    ],[ "Activate"               ]],
            "FREE"        :  [ 0.6,    ["Free"                     ],[ "Free"                   ]],
            "UPGRADE"     :  [ 1.0,    ["Upgrade Synergy"          ],[ "Upgrade"                ]],
            "REPLACE"     :  [ 1.0,    ["Replace Profit"           ],[ "Replace Setup"          ]],

            "DAMAGE"      :  [ 1.0,    ["Decreased Health Synergy" ],[ "Damage"                 ]],                
            "SELFDAMAGE"  :  [ 0.5,    ["Self Damage Payoff"       ],[ "Self Damage Activator"  ]],                
            "DESTRUCTION" :  [ 1.0,    ["Destruction Synergy"      ],[ "Destruction Activator"  ]],
            "REANIMATE"   :  [ 1.0,    ["Reanimate Activator"      ],[ "Deploy","Activate"      ]],
            "REANIMATOR"  :  [ 0.75,   ["Destruction Activator"    ],[ "Reanimate"              ]],
            #"AGGRESSIVEATTACK" :  [ 0.5,  ["Stat Buff", "Attack Buff"],["Aggressive","Aggressive Giver"     ]],    
            #"STEALTHATTACK"    :  [ 0.5,  ["Stealth","Stealth Giver"           ],["Stat Buff", "Attack Buff"]],    
            #"BREAKTHROUGH"     :  [ 0.5,  ["Breakthrough","Breakthrough Giver" ],["Stat Buff", "Attack Buff"]],
            
}


class SynergyTemplate:

    global Synerginary
   
    def __init__(self):
        self.synergies = {}

        for name, synergy_data in Synerginary.items():
            weight, target_tags, source_tags = synergy_data
            self.add_synergy(name, weight, target_tags, source_tags)        

    def add_synergy(self, name, weight, target_tags, source_tags):
        synergy = Synergy(name, weight, target_tags, source_tags)
        self.synergies[name] = synergy

    def get_synergies(self):
        return self.synergies

    def get_synergy_by_name(self, name):
        return self.synergies[name]        

    def get_synergies_by_target_tag(self, tag):
        return [synergy for synergy in self.synergies.values() if tag in synergy.target_tags]

    def get_synergies_by_source_tag(self, tag):
        return [synergy for synergy in self.synergies.values() if tag in synergy.source_tags]
    
    def get_source_tags(self):
        source_tags = set()
        for synergy in self.synergies.values():
            source_tags.update(synergy.source_tags)
        return source_tags

    def get_target_tags(self):
        target_tags = set()
        for synergy in self.synergies.values():
            target_tags.update(synergy.target_tags)
        return target_tags

    def __str__(self):
        output = "Synergies:\n"
        for name, synergy in self.synergies.items():
            output += f"{synergy}\n"
        return output

class Synergy:
    def __init__(self, name, weight, target_tags, source_tags):
        self.name = name
        self.weight = weight
        self.target_tags = target_tags 
        self.source_tags = source_tags 
        self.source_counts = {tag: 0 for tag in source_tags}
        self.target_counts = {tag: 0 for tag in target_tags}

    def add_source_tag(self, tag, value=1):
        set(self.source_tags).update(tag)
        self.source_counts[tag] = value
    
    def add_target_tag(self, tag, value=1):
        set(self.target_tags).update(tag)        
        self.target_counts[tag] = value

    def get_target_tags(self):
        return self.target_tags
    
    def get_source_tags(self):
        return self.source_tags

    def is_tag_in_source(self,tag):
        return tag in self.source_tags
    
    def is_tag_in_target(self,tag):
        return tag in self.target_tags
    
    def set_source_count(self, tag, value=1):
        if tag in self.source_counts:
            if self.source_counts[tag] > 0:
                print(f"{tag} > 0 < {value} already! ")
            self.source_counts[tag] = value    

    def set_target_count(self, tag, value=1):
        if tag in self.target_counts:
            if self.target_counts[tag] > 0:
                print(f"{tag} > 0 < {value} already! ")
            self.target_counts[tag] = value
    
    def get_source_counts(self):
        return self.source_counts
    
    def get_target_counts(self):
        return self.target_counts
    
    def is_synergy(self):  
        has_nonzero_sources = any(source_val > 0 for source_val in self.source_counts.values())
        has_nonzero_targets = any(target_val > 0 for target_val in self.target_counts.values())
        return has_nonzero_sources and has_nonzero_targets

    def stats(self,stats,type):
        max = max(stats[self.name][type].keys())
        if type == 'target' :
            return self.source_counts / max
        if type == 'source' :
            return self.target_counts / max
        return None

    def __str__(self):
        source_counts_str = ", ".join([f"{tag}: {count}" for tag, count in self.source_counts.items()])
        target_counts_str = ", ".join([f"{tag}: {count}" for tag, count in self.target_counts.items()])
        source_counts_total = sum(self.get_source_counts().values())
        target_counts_total = sum(self.get_target_counts().values())
        return f"{self.name:<17}: {self.weight:<7} - Sources: {source_counts_str:>40} - Targets: {target_counts_str:>40} => {source_counts_total:<5.2g}^{target_counts_total:>5.2g}"

class SynergyCollection:

    def __init__(self, sources=None, targets=None, synergy_template=None):
        self.sources = sources or {}
        self.targets = targets or {}
        self.synergies = {}
        self.synergy_template = synergy_template or SynergyTemplate()

        if self.sources and self.targets:
            self.find_synergy_pairs()
            
    @classmethod
    def from_entities(cls, entities, synergy_template=None):
        sources = {}
        targets = {}

        for entity in entities:                
            for source_name in entity.sources:
                sources[source_name] = sources.get(source_name, 0) + 1
            for target_name in entity.targets:
                targets[target_name] = targets.get(target_name, 0) + 1

        return cls(sources,targets, synergy_template=synergy_template)


    @classmethod
    def from_deck(cls, deck, synergy_template=None):       
        entities = [ entity for card in deck.cards.values() for entity in card.entities ]
        return cls.from_entities(entities, synergy_template=synergy_template)

    @classmethod
    def from_forgeborn(cls, forgeborn, synergy_template=None):
        entities = [ability for ability in forgeborn.abilities.values()]
        return cls.from_entities(entities, synergy_template=synergy_template)


    def __add__(self, other):
        
        sources1 = collections.Counter(self.sources)
        sources2 = collections.Counter(other.sources)
        new_sources = sources1 + sources2

        targets1 = collections.Counter(self.targets)
        targets2 = collections.Counter(other.targets)
        new_targets = targets1 + targets2

        return SynergyCollection(new_sources, new_targets)
    
    def __mul__(self, other):

        if isinstance(other, (int, float)):
            sources = {k: round(v * other, 2) for k, v in self.sources.items()}
            targets = {k: round(v * other, 2) for k, v in self.targets.items()}
            return SynergyCollection(sources, targets)
        else:
            raise ValueError("Can only multiply with a number")
                                                   
    def find_synergy_pairs(self):        
        for template_synergy_name, template_synergy in self.synergy_template.synergies.items():
            synergy = Synergy(template_synergy_name, template_synergy.weight, [], [])
            for source_tag in template_synergy.source_tags:
                if source_tag in self.sources:                  
                    synergy.add_source_tag(source_tag, self.sources[source_tag])

            for target_tag in template_synergy.target_tags:
                if target_tag in self.targets:                  
                    synergy.add_target_tag(target_tag, self.targets[target_tag])

            if synergy.is_synergy():                    
                self.synergies[synergy.name] = synergy                
                        
    def evaluate_synergy(self, synergy, stats=None):
        score = 0
        if stats is None:
            targets = sum(synergy.get_target_counts().values()) * synergy.weight
            sources = sum(synergy.get_source_counts().values()) * synergy.weight
            score = sources ** (math.log(targets) + math.exp(-1)) 
        else:
            source_score = synergy.stats(stats,'source')
            target_score = synergy.stats(stats,'target')
            score = (1 + source_score) ** (1 + target_score) 

        return score

    def calculate_scores(self, stats=None):
        scores = 0
        for syn in self.synergies.values():
            score = self.evaluate_synergy(syn,stats=None)
            print(f"{syn} -> {score:.2g}")
            scores += score
        return scores

    def calculate_percentage(self):            
        percentage_used = len(self.synergies) / len(self.targets) 
        #print(f"Paired / Total : {len(self.synergies)}/{len(self.targets)}")
        return percentage_used
    
    def calculate_average(self, scores):
        if len(self.synergies) == 0: 
            return 0             
        score_avg  = scores / len(self.synergies)
        return score_avg

    def __str__(self):
        sources_str = f"Sources: {self.sources}\n" if isinstance(self.sources, dict) else ""
        targets_str = f"Targets: {self.targets}\n" if isinstance(self.targets, dict) else ""
        synergies_str = "Synergies:\n"
        for synergy in self.synergies.values():                        
            synergies_str += f"{str(synergy)} => {self.evaluate_synergy(synergy):.2g}\n"
        return synergies_str # + sources_str + targets_str




