
"""
helper functions for data processing
"""

import re
from pandas import to_datetime, Timedelta
from data_access import make_sqlalchemy_engine, fetch_eating_data, fetch_symptoms_data
from constants import DEBUG, ERR_PREFIX, MEALS_MAPPING
from constants import (COLUMN_ACCOUNT_ID, COLUMN_DATE, COLUMN_MEAL_ID, COLUMN_MEAL, 
                       COLUMN_NAME, COLUMN_TIMING, COLUMN_SYMPTOM, COLUMN_GRADE, COLUMN_NAME,
                       COLUMN_WEEKDAY, COLUMN_SYMPTOMS, COLUMN_AVG_GRADE, COLUMN_NAME_REGEX,
                       COLUMN_SYMPTOM_SAME_DAY, COLUMN_SYMPTOM_NEXT_DAY)


def get_dataframes(account_id, engine=None):
    """
    TODO: docs

    Two queries to make and retrieve two tables from the SQL database.
    Both are LONG tables, i.e. no aggregating is done.
    The necessary aggregation will be done by an individual plotting function.
    
    Returns:
        two df's: pandas.DataFrame object otherwise (empty or not)
    """

    # Start an sqlalchemy engine
    engine = engine or make_sqlalchemy_engine()

    # Fetch data
    df_eating = fetch_eating_data(account_id, engine)     # in data_access.py
    df_symptoms = fetch_symptoms_data(account_id, engine) # in data_access.py
    del engine    # not really necessary (according to sqlalchemy docs)

    # Clean data
    df_eating = clean_eating_data(df_eating)
    df_symptoms = clean_symptoms_data(df_symptoms)

    # Add "engineered features" (i.e. columns)
    df_eating = add_columns_to_eating_data(df_eating, df_symptoms)
    df_symptoms = add_columns_to_symptoms_data(df_eating, df_symptoms)  # no cols are added - just for visual consistency

    # Return two df's
    return (df_eating, df_symptoms)



def clean_eating_data(df):
    """
    note: name will not be cleaned here
    but a new column 'name_regex' will be added
    """

    # Clean
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    df[COLUMN_DATE] = to_datetime(df[COLUMN_DATE])   # pandas.to_datetime

    # Drop duplicated rows (based on the subset of cols)
    columns = [COLUMN_ACCOUNT_ID, COLUMN_DATE, COLUMN_MEAL_ID, COLUMN_MEAL, COLUMN_NAME]
    mask_duplicated = df.duplicated(subset=columns, keep='first')
    return df[~mask_duplicated]



def clean_symptoms_data(df):
    """TODO"""
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    df[COLUMN_DATE] = to_datetime(df[COLUMN_DATE])   # pandas.to_datetime
    return df



def add_columns_to_eating_data(df_eating, df_symptoms):
    """TODO
    These columns will be added:
    weekday
    name_regex
    symptom_same_day
    symptom_next_day
    symptoms 
    avg_grade
    """
    
    # Add Weekday (Monday=0, Sunday=6)
    df_eating[COLUMN_WEEKDAY] = df_eating[COLUMN_DATE].dt.weekday

    # Add regex'ed name -> "name_regex" (keep the original)
    df_eating[COLUMN_NAME_REGEX] = regex_foodstuff_name(df_eating[COLUMN_NAME])

    # rearrange columns for visual appeal (in debug mode only)
    if DEBUG:
        columns = df_eating.columns.to_list()
        columns.insert(5, columns.pop())   # 2 = the index, where to put the new columns
        columns.insert(2, columns.pop())
        df_eating = df_eating.reindex(columns=columns)

    # Add columns (with data from df_symptoms)
    df_eating[COLUMN_SYMPTOM_SAME_DAY] = df_eating[COLUMN_DATE].isin(df_symptoms[COLUMN_DATE])
    df_eating[COLUMN_SYMPTOM_NEXT_DAY] = (df_eating[COLUMN_DATE] + Timedelta(1, unit='D')).isin(df_symptoms[COLUMN_DATE])
    
    unique_values = tuple(df_symptoms[COLUMN_TIMING].unique())
    meal_names = sorted(MEALS_MAPPING.keys())

    try: # dynamicaly
        mapping = {[unique_values[i] for i,v in enumerate(unique_values) if e.lower() in v.lower()][0]:e for e in meal_names}
    except: # fallback
        mapping = {'AFTER_BREAKFAST': 'BREAKFAST', 'AFTER_DINNER': 'DINNER', 'AFTER_LUNCH': 'LUNCH'}

    df_symptoms[COLUMN_MEAL] = df_symptoms[COLUMN_TIMING].map(mapping)  # by ref
    df_symptoms_agg = (df_symptoms[[COLUMN_DATE, COLUMN_MEAL, COLUMN_SYMPTOM, COLUMN_GRADE]].groupby([COLUMN_DATE, COLUMN_MEAL])
                       .agg({COLUMN_SYMPTOM: ", ".join, COLUMN_GRADE: 'mean'}).reset_index())
    
    # 'symptoms' is concatenated
    df_symptoms_agg.columns = [COLUMN_DATE, COLUMN_MEAL, COLUMN_SYMPTOMS, COLUMN_AVG_GRADE]
    
    # 5 new columns appended
    return df_eating.merge(df_symptoms_agg, how='left', on=[COLUMN_DATE, COLUMN_MEAL])



def add_columns_to_symptoms_data(df_eating, df_symptoms):
    return df_symptoms  # no columns are added - just for consistency



def regex_foodstuff_name(sr):
    """
    Regex for the foodstuff name column

    Arguments:
        sr: pandas.Series
    Returns:
        pandas.Series
    """

    measure_words = (r"((Tasse|Scheibe|Flasche|Dose|Kanne|Prise|Kugel|Tüte)n?)|((Packung|Verpackung|Portion)(en)?)|"
                     r"Glass|Glas|Gläser|Becher|Teller|Esslöffel|Teelöffel|Stück|Stücke|Schluck|Schlücke|Handvoll|Hand|"
                     r"Kilogramm|Kilogram|Milligramm|Milligram|Miligramm|Miligram|Gramm|Gram|Kilo|Liter|Litre")
    p = r"^"
    p += r"(-)"
    p += r"|(\d{1,2}:\d\d(\s?Uhr)?)"
    p += r"|(^mit\s)"
    p += r"|(\d+(\s?\d*[,/.]\d*)?(\s?(EL|TL|St|stk|gr|ml|m|l|g|x)\.?)?\s)"
    p += r"|((halb|klein|groß)(es|er|en|e)\s)"
    p += r"|(%s)" % measure_words
    
    precompiled_pattern = re.compile(p, re.IGNORECASE)
    return sr.str.strip().str.replace(precompiled_pattern, '', regex=True).str.strip().str.lower().str.title()
