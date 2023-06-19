from Card_Library import Deck, Fusion
class DeckLibrary:
    def __init__(self, decks_or_fusions):
        self.library = {
            'Deck': {},
            'Fusion': {}
        }

        self.update(decks_or_fusions)

    def make_fusions(self):
        for deck1 in self.library['Deck'].values():
            for deck2 in self.library['Deck'].values():
                if deck1 is not deck2:
                    fusion_name = f"{deck1.name}_{deck2.name}"
                    if fusion_name not in self.library['Fusion']:
                        fusion = Fusion(fusion_name, [deck1, deck2])
                        if fusion.fused is not None:
                            self.library['Fusion'][fusion_name] = fusion

    def update(self, objects):
        print(f"Updating Library...")
        for obj in objects:
            obj_type = type(obj).__name__
            container = self.library[obj_type]
            if obj.name not in container:
                container[obj.name] = obj

        self.make_fusions()


    def to_json(self):
        return {
            'decks': [deck.to_json() for deck in self.library['Deck'].values()],
            'fusions': [fusion.to_json() for fusion in self.library['Fusion'].values()]         
        }


