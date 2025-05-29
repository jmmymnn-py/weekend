#combine.py

import pandas as pd

def combine(*dfs):
    """
    Accepts multiple DataFrames, concatenates them, and returns a single
    DataFrame sorted by 'Start DateTime'.
    
    Parameters:
        *dfs: Variable number of pandas DataFrames to merge and sort
    
    Returns:
        pandas.DataFrame: Combined and sorted DataFrame
    """
    combined_df = pd.concat(dfs, ignore_index=True)
    sorted_combined_df = combined_df.sort_values(by='Start DateTime').reset_index(drop=True)
    return sorted_combined_df

