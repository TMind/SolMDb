from scipy.stats import hypergeom



def calc_probability(t, s, N, c, n, m):
    # Calculate probability of drawing n out of t cards and m out of s cards
    pn = hypergeom.cdf(k=n, M=N, n=t, N=c)
    pm = hypergeom.pmf(k=m, M=N, n=s, N=c)
    
    print(f"Drawing at least {n} from {t} in a hand of {c} out of a total {N}")
    print(f"Drawing exactly  {m} from {s} in a hand of {c} out of a total {N}")

    return pn * pm


def calc_synergy_validity(s, t):
    # Calculate probability of meeting condition in a single turn


    p_target_no_source_first_turn  = calc_probability(s, t, 20, 5, 1, 0)
    p_target_no_source_second_turn = calc_probability(s, t, 15, 5, 1, 0)
    p_target_no_source_third_turn  = calc_probability(s, t, 10, 5, 1, 0)

    p_target_first_turn  = 1 - hypergeom.pmf(k=0, M=20, n=t, N=5)
    p_target_second_turn = 1 - hypergeom.pmf(k=0, M=15, n=t, N=5)

    p_target_no_source_three_turns = (                                                          p_target_no_source_first_turn  + 
                                     (1 - p_target_first_turn) *                                p_target_no_source_second_turn + 
                                     (1 - p_target_first_turn) * (1 - p_target_second_turn) *   p_target_no_source_third_turn
    )

    print(f"Target only Turn 1: {p_target_no_source_first_turn}\n "
          f"Target only Turn 2: {p_target_no_source_second_turn}\n"
          f"Target only Turn 3: {p_target_no_source_third_turn}\n "
          f"Target First  Turn: {p_target_first_turn}\n"
          f"Target Second Turn: {p_target_second_turn}\n"
          f"Target only 3 Turns: {p_target_no_source_three_turns}"  )

    # Return True if probability exceeds threshold, False otherwise
    return 1 - p_target_no_source_three_turns



class Evaluation:
    def __init__(self, synergy_stats):
        self.synergy_stats = synergy_stats
  

    def evaluate_deck(self, deck):
        # loop through each synergy in the deck

        for synergy_name, synergy in deck.synergy_collection.synergies.items():
            # determine the number of sources and targets in the synergy
            source_count = sum(synergy.get_source_counts().values())
            target_count = sum(synergy.get_target_counts().values())

            synergy_prob = calc_synergy_validity(source_count, target_count)        

            print(f"{synergy_name:<15}: {source_count} / {target_count} -> {synergy_prob} ")

        return
