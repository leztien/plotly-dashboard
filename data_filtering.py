

"""
Filtering / Subsetting functions for pandas dataframes
- based on dates
- based on selectors
"""

from numpy import logical_and
from pandas import Series
from constants import ERR_PREFIX, MEALS_MAPPING, A, B, C, D
from constants import COLUMN_MEAL, COLUMN_SYMPTOM_SAME_DAY, COLUMN_SYMPTOM_NEXT_DAY, COLUMN_AVG_GRADE



def subset_data_by_dates(df, start_date, end_date):
    """TODO"""
    
    start_date, end_date = str(start_date), str(end_date)
    
    # Determine the name of the Date column: Date or Datum?
    COLUMN_DATE = ([col for col in df.columns if col.lower() in ("date", "datum")] + ['date'])[0]
    return df.query(f"'{start_date}' <= {COLUMN_DATE} <= '{end_date}'")



def subset_data_by_selector_values(df, meals_selector=None, 
                                       symptom_selector=None,
                                       grade_selector=None):
    """
    TODO: docs

    Care must be taken either to match the indices (df vs masks)
    or strip all boolean masks of their indices (if any)
    """

    # Assert just in case
    assert meals_selector in (None, A,B,C,D), f"{ERR_PREFIX}bad meals_selector: {meals_selector}"
    assert symptom_selector in (None,A,B,C,D), f"{ERR_PREFIX}bad symptom_selector: {symptom_selector}"
    assert grade_selector in (None, *range(11)), f"{ERR_PREFIX}bad grade_selector: {grade_selector}"

    # Make default boolean mask (filled with all True's)
    mask_meals  = Series([True]*len(df), index=df.index)
    mask_symptoms = Series([True]*len(df), index=df.index)
    mask_grade = Series([True]*len(df), index=df.index)
    ... # add more as you add more selectors

    # CASE: boolean mask for meal (Mahlzeiten): selector1
    if meals_selector:
        all_values = list(MEALS_MAPPING.keys())   # ["BREAKFAST", "LUNCH", "DINNER"]
        meal_values_list = { A: all_values, 
                             B: all_values[0:1], 
                             C: all_values[1:2], 
                             D: all_values[2:3]}[meals_selector]  # will raise error if not in
        mask_meals = df[COLUMN_MEAL].isin(meal_values_list)

    # CASE: boolean mask for symptoms: selector2
    if symptom_selector:
        if symptom_selector == D:
            mask_symptoms = df[COLUMN_SYMPTOM_NEXT_DAY] == True
        else:
            all_values = [False, True]  # days without / with complaint
            symptom_values_list = { A: all_values, 
                                    B: all_values[0:1], 
                                    C: all_values[1:2]}[symptom_selector] # will raise error if not in
            mask_symptoms = df[COLUMN_SYMPTOM_SAME_DAY].isin(symptom_values_list)
    
    # CASE: selector is the grade slider
    if grade_selector:
        if type(grade_selector) is int and 1 <= grade_selector <= 10:
            mask_grade = df[COLUMN_AVG_GRADE] >= grade_selector
        elif grade_selector in (A,B,C):  # case: grade_selector is a dropdown-menu (future)
            mask_grade = ...  #extend the functionality as necessary

    # Encapsulate all the masks into one iterable object (array)
    masks = [
        mask_meals,
        mask_symptoms,
        mask_grade,
        # append more as you add more selectors / as necessary
        ]
    
    # Unite all the masks with logical AND after having stripped them of their indices (if any)
    mask = logical_and.reduce([list(mask) for mask in masks])

    # Subset the df_subset with the universal boolean mask
    return df[mask]

