
Synerginary = {
    #        <NAME>          <WEIGHT>  <TRIGGER>                       <output>
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
            "SPELL"       :  [ 1.0,    ["Spell Synergy"            ],[ "Spell"                  ]],
            "HEALING"     :  [ 1.0,    ["Healing Synergy"          ],[ "Healing Source"         ]],
            "MOVEMENT"    :  [ 1.0,    ["Movement Benefit"         ],[ "Movement"               ]],
            "ARMOR"       :  [ 0.5,    ["Armor Synergy"            ],[ "Armor","Armor Giver "   ]],
            "ACTIVATION"  :  [ 1.0,    ["Ready"                    ],[ "Activate"               ]],
            "FREE"        :  [ 2.0,    ["Free"                     ],[ "Free"                   ]],
            "FREE HEALING":  [ 2.0,    ["Free Healing"             ],[ "Healing Source"         ]],
            "FREE DESTROY":  [ 2.0,    ["Free SelfDestruction"     ],[ "Destruction Synergy","Minon"]],                               
            "FREE UPGRADE":  [ 2.0,    ["Free Upgrade"             ],[ "Upgrade"                ]],                               
            "FREE SELFDMG":  [ 2.0,    ["Free Self Damage"         ],[ "Self Damage Activator"  ]],
            "FREE SPELL"  :  [ 2.0,    ["Free Spell"               ],[ "Spell"                  ]],                                               
            "FREE REPLACE":  [ 2.0,    ["Free Replacement"         ],[ "Replace Setup","Minion" ]],                                               
            "FREE MAGE"   :  [ 2.0,    ["Free Mage"                ],[ "Mage"                   ]], 
            "UPGRADE"     :  [ 1.0,    ["Upgrade Synergy"          ],[ "Upgrade"                ]],
            "REPLACE"     :  [ 1.0,    ["Replace Profit"           ],[ "Replace Setup"          ]],

            "DAMAGE"      :  [ 1.0,    ["Decreased Health Synergy" ],[ "Damage"                 ]],                
            "SELFDAMAGE"  :  [ 0.5,    ["Self Damage Payoff"       ],[ "Self Damage Activator"  ]],                
    
            "DESTROY SYN" :  [ 1.0,    ["SelfDestruction Activator"],[ "Destruction Synergy"    ]],                        
            "DESTROY MIN" :  [ 0.5,    ["SelfDestruction Activator"],[ "Minion"                 ]],
            "REDEPLOY"    :  [ 1.0,    ["Reanimate Activator"      ],[ "Deploy"                 ]],
            "REACTIVATE"  :  [ 0.5,    ["Reanimate Activator"      ],[ "Activate"               ]],
            "STEALTH"     :  [ 1.0,    ["Defender Giver"           ],[ "Stealth","Stealth Giver"]],
            "AGGRO"       :  [ 1.0,    ["Aggressive"               ],[ "Replace Setup"          ]],
            "FORGEBORN"   :  [ 2.0,    ["Forgeborn Synergy"        ],[ "Forgeborn Ability"      ]],


            # General Output              
            "DESTROY OPP" :  [ 1.0,    ["Destroy Enemy Creature"   ],[ "Removal"                ]],
            "FACEBURN"    :  [ 1.0,    ["Deal Damage Opponent"     ],[ "Face Burn"              ]],
            "LIFE GAIN"   :  [ 1.0,    ["Gain Life"                ],[ "Healing Source"         ]],
            "DISRUPTION"  :  [ 0.5,    ["Lane Control"             ],[ "Disruption"             ]],
            "SILENCE"     :  [ 0.5,    ["Creature Control"         ],[ "Silence"                ]],

            #STRONG ATTACK / DEFENSE 
            #"AGGRESSIVEATTACK" :  [ 0.5,  ["Stat Buff", "Attack Buff"],["gressive","Aggressive Giver"     ]],    
            #"STEALTHATTACK"    :  [ 0.5,  ["Stealth","Stealth Giver"           ],["Stat Buff", "Attack Buff"]],    
            #"BREAKTHROUGH"     :  [ 0.5,  ["Breakthrough","Breakthrough Giver" ],["Stat Buff", "Attack Buff"]],
            
}


class SynergyTemplate:

    global Synerginary
   
    def __init__(self):
        self.synergies = {}

        for name, synergy_data in Synerginary.items():
            weight, input_tags, output_tags = synergy_data
            self.add_synergy(name, weight, input_tags, output_tags)        

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