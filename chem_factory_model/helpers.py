import pandas as pd
import ast


def transform_timeseries(
    file_path: str, read_sheet_name: str, column_name: str, write_sheet_name: str
):
    """
    Transformiert eine Zeitreihenspalte in ein neues Sheet des Excel-Files
    """
    # Excel-File einlesen
    startcol = 0
    df = pd.read_excel(file_path, sheet_name=read_sheet_name)

    # Zeitreihenspalte in Liste von Tuples umwandeln

    for index, row in df.iterrows():
        time_series = row[column_name]
        # list_of_tuples = ast.literal_eval(time_series[0])
        list_of_tuples = ast.literal_eval(time_series)
        # Liste von Tuples in ein neues DataFrame umwandeln
        new_df = pd.DataFrame(
            list_of_tuples,
            columns=["time[minutes]", f"queue_preparation_length scenario {index}"],
        )

        # Neues DataFrame in ein neues Sheet des Excel-Files schreiben
        with pd.ExcelWriter(
            file_path, engine="openpyxl", mode="a", if_sheet_exists="overlay"
        ) as writer:
            new_df.to_excel(
                writer, sheet_name=write_sheet_name, index=False, startcol=startcol
            )
        startcol += 3


if __name__ == "__main__":
    pass
