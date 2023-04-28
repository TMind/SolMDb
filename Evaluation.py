from scipy.stats import hypergeom


def calc_prob(s, t, N, n, m, C ):
    # Calculate probability of drawing at least n target cards and at most m source cards
    p_target_at_least_n = 1 - hypergeom.cdf(k=n-1, M=N, n=t, N=C)
    p_source_at_most_m = hypergeom.cdf(k=m, M=N, n=s, N=C)

    # Calculate probability of meeting condition
    p_meeting_condition = p_target_at_least_n * p_source_at_most_m

    return p_meeting_condition


def calc_synergy_validity(s, t):
    # Calculate probability of meeting condition in a single turn


    p_target_no_source_first_turn  = calc_prob(s, t, 20, 1, 0, 5)
    p_target_no_source_second_turn = calc_prob(s, t, 15, 1, 0, 5)
    p_target_no_source_third_turn  = calc_prob(s, t, 10, 1, 0, 5)

    p_target_first_turn  = 1 - hypergeom.pmf(k=0, M=20, n=t, N=5)
    p_target_second_turn = 1 - hypergeom.pmf(k=0, M=15, n=t, N=5)

    p_target_no_source_three_turns = (                                                          p_target_no_source_first_turn  + 
                                     (1 - p_target_first_turn) *                                p_target_no_source_second_turn + 
                                     (1 - p_target_first_turn) * (1 - p_target_second_turn) *   p_target_no_source_third_turn
    )

#    print(f"Target only Turn 1: {p_target_no_source_first_turn}\n "
#          f"Target only Turn 2: {p_target_no_source_second_turn}\n"
#          f"Target only Turn 3: {p_target_no_source_third_turn}\n "
#          f"Target First  Turn: {p_target_first_turn}\n"
#          f"Target Second Turn: {p_target_second_turn}\n"
#          f"Target only 3 Turns: {p_target_no_source_three_turns}"  )

    # Return True if probability exceeds threshold, False otherwise
    return 1 - p_target_no_source_three_turns



class Evaluation:
    def __init__(self, synergy_stats):
        self.synergy_stats = synergy_stats
  

    def evaluate_deck(self, deck):
        # loop through each synergy in the deck

        synergy_total = 0
        for synergy_name, synergy in deck.synergy_collection.synergies.items():
            # determine the number of sources and targets in the synergy
            source_count = sum(synergy.get_source_counts().values())
            target_count = sum(synergy.get_target_counts().values())

            synergy_prob = calc_synergy_validity(source_count, target_count)   
            target_prob = 0
            total_prob = 0
            
            if synergy_prob >= 0.5 :
                target_prob  = 1 - (hypergeom.pmf(k=0, M=20, n=target_count, N=5) ** 3)
                total_prob   = synergy_prob * target_prob * 100 

            print(f"{synergy_name:<15}: {source_count} / {target_count} -> {synergy_prob:.2f} => {target_prob:.2f} => {total_prob:.2f} ")
            synergy_total += total_prob

        print(f"Total synergy = {synergy_total / len(deck.synergy_collection.synergies.values())}")
