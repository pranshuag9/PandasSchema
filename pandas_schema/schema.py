from typing import Iterable, List

import pandas as pd

from .errors import PanSchInvalidSchemaError, PanSchArgumentError
from .validation_warning import ValidationWarning
from .column import Column


class Schema:
    """
    A schema that defines the columns required in the target DataFrame
    """

    def __init__(self, columns: Iterable[Column], ordered: bool = False):
        """
        :param columns: A list of column objects
        :param ordered: True if the Schema should associate its Columns
            with DataFrame columns by position only, ignoring the header names.
            False if the columns should be associated by
            column header names only. Defaults to False
        """
        if not columns:
            raise PanSchInvalidSchemaError(
                'An instance of the schema class must have a columns list'
            )

        if not isinstance(columns, List):
            raise PanSchInvalidSchemaError(
                'The columns field must be a list of Column objects'
            )

        if not isinstance(ordered, bool):
            raise PanSchInvalidSchemaError(
                'The ordered field must be a boolean'
            )

        self.columns = list(columns)
        self.ordered = ordered

    def validate(
            self,
            df: pd.DataFrame,
            columns: List[Column] = None
    ) -> List[ValidationWarning]:
        """
        Runs a full validation of the target DataFrame
        using the internal columns list

        :param df: A pandas DataFrame to validate
        :param columns: A list of columns indicating a subset of the schema
            that we want to validate
        :return: A list of ValidationWarning objects that list the ways
            in which the DataFrame was invalid
        """
        errors = []
        df_cols = len(df.columns)

        # If no columns are passed, validate against every column in the schema.
        # This is the default behaviour
        if columns is None:
            schema_cols = len(self.columns)
            columns_to_pair = self.columns
            if df_cols != schema_cols:
                errors.append(
                    ValidationWarning(
                        message=f'Invalid number of columns. '
                                f'The schema specifies {schema_cols}, '
                                f'but the data frame has {df_cols}'
                    )
                )
                return errors

        # If we did pass in columns, check that they are part of current schema
        else:
            if set(columns).issubset(self.get_column_names()):
                columns_to_pair: list[Column] = [
                    column for column in self.columns if column.name in columns
                ]
            else:
                raise PanSchArgumentError(
                    f'Columns {set(columns).difference(self.columns)} '
                    f'passed in are not part of the schema'
                )

        # We associate the column objects in the schema with data frame series
        # either by name or by position, depending on the value of self.ordered
        if self.ordered:
            series = [x[1] for x in df.iteritems()]
            column_pairs = zip(series, self.columns)
        else:
            column_pairs = []
            for column in columns_to_pair:
                # Throw an error if the schema column isn't in the dataframe
                if column.name not in df:
                    errors.append(
                        ValidationWarning(
                            message=f'The column {column.name} exists in the '
                                    f'schema but not in the data frame',
                            column=column.name
                        )
                    )
                    return errors
                column_pairs.append((df[column.name], column))

        # Iterate over each pair of schema columns
        # and dataframe series and run validations
        for series, column in column_pairs:
            errors += column.validate(series)

        return sorted(errors, key=lambda e: e.row)

    def get_column_names(self):
        """
        Returns the column names contained in the schema
        """
        return [column.name for column in self.columns]
