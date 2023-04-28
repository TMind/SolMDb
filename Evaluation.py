
class Evaluation:
    def __init__(self, synergy_stats):
        self.synergy_stats = synergy_stats
        self.engine_ratio = 1/3
    
    def calculate_splits(self, sources, targets):
        splits = 0
        remaining_sources = sources
        remaining_targets = targets
        
        while remaining_sources >= 2 and remaining_targets >= 1:
            splits += 1
            remaining_sources -= 2
            remaining_targets -= 1
        
        return (splits, remaining_sources, remaining_targets)


    def evaluate_deck(self, deck):
        # loop through each synergy in the deck
        splits = 0
        remaining_sources = 0
        remaining_targets = 0
        for synergy_name, synergy in deck.synergy_collection.synergies.items():
            # determine the number of sources and targets in the synergy
            source_count = sum(synergy.get_source_counts().values())
            target_count = sum(synergy.get_target_counts().values())

            # Lets define a general ratio for source : targets 
            (new_splits, new_remaining_sources, new_remaining_targets)  = self.calculate_splits(source_count, target_count)
            splits += new_splits
            remaining_sources += new_remaining_sources
            remaining_targets += new_remaining_targets
            print(f"{synergy_name:<15}: {new_splits} , {new_remaining_sources} / {new_remaining_targets}")
            # TODO: match sources against targets and determine score
        print(f"Total splits: {splits} - Remaining Sources : {remaining_sources} / {remaining_targets} : Remaining Targets")
        # TODO: calculate final score for entire deck
        # Note: the score should be higher the more sources and targets are matched, so consider
        # penalizing the score for each unmatched source or target
        return 
