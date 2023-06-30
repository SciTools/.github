"""
Populate https://github.com/orgs/SciTools/projects/13 from the results of query.py.
"""

from enum import Enum
import json
import random
from string import ascii_lowercase
from subprocess import run
import sys
from typing import List, NamedTuple

import numpy as np
import pandas as pd

from common import csv_path, peloton_logins


# https://docs.github.com/en/issues/planning-and-tracking-with-projects/
#  automating-your-project/
#  using-the-api-to-manage-projects#finding-the-node-id-of-a-user-project
PROJECT_ID = "PVT_kwDOABU7f84ALhAI"

# Number of commands to include in a single GraphQL query - avoids time-outs.
PAGINATION = 20


class MutationTypes(Enum):
    # https://docs.github.com/en/graphql/reference/mutations
    ADD = "addProjectV2ItemById"
    DELETE = "deleteProjectV2Item"
    UPDATE = "updateProjectV2ItemFieldValue"
    CLEAR = "clearProjectV2ItemFieldValue"


class DataTypes(Enum):
    # https://docs.github.com/en/graphql/reference/
    #  input-objects#projectv2fieldvalue
    DATE = "date"
    NUMBER = "number"
    SELECT = "singleSelectOptionId"
    TEXT = "text"


class FieldInfo(NamedTuple):
    """Key information on a project field to enable population."""
    github_id: str
    data_type: DataTypes
    table_column: str


class Fields(Enum):
    """The project fields to populate."""
    # https://docs.github.com/en/issues/planning-and-tracking-with-projects/
    #  automating-your-project/
    #  using-the-api-to-manage-projects#finding-the-node-id-of-a-field
    DATE_CREATED = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgHV-jI", DataTypes.DATE, "created_at"
    )
    FINAL_COMMENT_LOGIN = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgHV_kc", DataTypes.TEXT, "final_comment_login"
    )
    FINAL_COMMENT_TIME = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgHV_lI", DataTypes.DATE, "final_comment_time"
    )
    NUM_COMMENTS = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgLbMPM", DataTypes.NUMBER, "comments"
    )
    DATE_UPDATED = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgLbMRM", DataTypes.DATE, "updated_at"
    )
    DATE_CLOSED = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgLbMTQ", DataTypes.DATE, "closed_at"
    )
    AUTHOR_LOGIN = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgLbMn8", DataTypes.TEXT, "user_login"
    )
    NUM_VOTES = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgLbM0k", DataTypes.NUMBER, "votes"
    )
    AUTHOR_MEMBERSHIP = FieldInfo(
        "PVTSSF_lADOABU7f84ALhAIzgLbNmc", DataTypes.SELECT, "user_login"
    )
    COMMENTER_MEMBERSHIP = FieldInfo(
        "PVTSSF_lADOABU7f84ALhAIzgLbNsM", DataTypes.SELECT, "final_comment_login"
    )
    DISCUSSION_WANTED = FieldInfo(
        "PVTSSF_lADOABU7f84ALhAIzgLlAMk", DataTypes.SELECT, "discussion_wanted"
    )
    ASSIGNEE_COUNT = FieldInfo(
        "PVTF_lADOABU7f84ALhAIzgLlEqo", DataTypes.TEXT, "assignee_count"
    )


class SelectionIds(Enum):
    """Ids to use for project fields that accept `singleSelectOptionId` inputs."""
    # https://docs.github.com/en/issues/planning-and-tracking-with-projects
    #  /automating-your-project/
    #  using-the-api-to-manage-projects#finding-the-node-id-of-a-field
    AUTHOR_PELOTON = "389ebec0"
    AUTHOR_EXTERNAL = "d961b9b7"
    COMMENTER_PELOTON = "98462be7"
    COMMENTER_EXTERNAL = "235b3d90"
    DISCUSSION_WANTED = "e17f4b18"


def get_unique_letter_string() -> str:
    return ''.join(random.choice(ascii_lowercase) for _ in range(16))


def run_mutation(lines: List[str], return_ids: bool = False) -> List[str]:
    """
    Construct and execute a GH GraphQL mutation query from individual lines.

    Optionally return the IDs that were mutated, enabling further mutations.
    """
    ids_in_project = []
    for i in range(0, len(lines), PAGINATION):
        block_slice = slice(i, i + PAGINATION)
        query = "mutation {\n%s\n}" % "\n".join(lines[block_slice])

        # Useful for reading GHA logs.
        print(query)
        output = run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True,
            text=True,
        )

        if output.stderr:
            print(output.stderr, file=sys.stderr)

        if return_ids:
            data = json.loads(output.stdout)["data"]
            ids_in_project.extend([v["item"]["id"] for v in data.values()])

    return ids_in_project


def build_query_line(
    mutation_type: MutationTypes,
    input_dict: dict,
) -> str:
    """Construct a GH GraphQL mutation line of the desired type and inputs."""
    mutation_id = get_unique_letter_string()

    for key, value in input_dict.items():
        if key != "value":
            input_dict[key] = f'"{value}"'
    input_str = "input: {"
    input_str += " ".join(f'{k}: {v}' for k, v in input_dict.items())
    input_str += "}"

    # Returning information is mandatory. Just get the item ID.
    if mutation_type is MutationTypes.ADD:
        item_suffix = "{item {id} }"
    elif mutation_type is MutationTypes.DELETE:
        item_suffix = "{deletedItemId}"
    else:
        item_suffix = "{projectV2Item {id} }"

    graphql_str = f"{mutation_id}: {mutation_type.value}(\n"
    graphql_str += input_str
    graphql_str += f"\n) {item_suffix}"

    return graphql_str


class ProjectItem:
    """Tracks an item ID in the Peloton project, with query conveniences."""
    @classmethod
    def items_from_table(cls, table: pd.DataFrame) -> List:
        """Generate 1 instance for each row in the query table."""
        table_rows = []
        addition_lines = []
        for _, row in table.iterrows():
            table_rows.append(row)
            addition_lines.append(
                build_query_line(
                    MutationTypes.ADD,
                    dict(projectId=PROJECT_ID, contentId=row["node_id"])
                )
            )
        ids_in_project = run_mutation(addition_lines, return_ids=True)

        return [
            cls(item_id, table_rows[ix])
            for ix, item_id
            in enumerate(ids_in_project)
        ]

    def __init__(self, item_id: str, table_row: pd.Series):
        """
        Create a :class:`ProjectItem` instance.

        Parameters
        ----------
        item_id : str
            The GH GraphQL ID of the item in the Peloton project.
        table_row : pd.Series
            The row in the query table that this item corresponds to.

        """
        self.input_kwargs = dict(projectId=PROJECT_ID, itemId=item_id)
        self.table_row = table_row

    @property
    def is_closed(self) -> bool:
        """Does this GitHub item have the closed state?"""
        return self.table_row.loc["state"] == "closed"

    def _build_query_line(
        self,
        mutation_type: MutationTypes,
        input_dict: dict = None
    ) -> str:
        """Convenience for calling :func:`build_query_line` for this item."""
        input_dict = input_dict or {}
        input_dict = dict(**input_dict, **self.input_kwargs)
        return build_query_line(mutation_type, input_dict)

    def query_line_delete(self) -> str:
        """Generate a mutation line to delete this item from the Peloton project."""
        return self._build_query_line(MutationTypes.DELETE)

    def _query_line_clear(self, field: Fields) -> str:
        """
        Generate a mutation line to clear a field on this project item.

        Only called by :meth:`_query_line_update`, if the update value is null.

        """
        return self._build_query_line(
            MutationTypes.CLEAR,
            dict(fieldId=field.value.github_id)
        )

    def _query_line_update(self, field: Fields) -> str:
        """
        Generate a mutation line to update a field value on this project item.

        Only called by :meth:`query_lines_update`, iterating through all fields.
        """
        field_info: FieldInfo = field.value
        value = self.table_row.loc[field_info.table_column]

        if field is Fields.AUTHOR_MEMBERSHIP:
            if value in peloton_logins:
                value = SelectionIds.AUTHOR_PELOTON.value
            else:
                value = SelectionIds.AUTHOR_EXTERNAL.value

        if field is Fields.COMMENTER_MEMBERSHIP:
            if value in peloton_logins:
                value = SelectionIds.COMMENTER_PELOTON.value
            else:
                value = SelectionIds.COMMENTER_EXTERNAL.value

        if field is Fields.DISCUSSION_WANTED:
            if value is True:
                value = SelectionIds.DISCUSSION_WANTED.value
            else:
                value = np.nan

        if field is Fields.FINAL_COMMENT_TIME and not pd.isnull(value):
            value = value.replace(" ", "T") + "Z"

        if pd.isnull(value):
            result = self._query_line_clear(field)

        else:
            if field_info.data_type == DataTypes.NUMBER:
                value_str = str(value)
            else:
                value_str = f'"{value}"'

            input_dict = dict(
                fieldId=field_info.github_id,
                value="{" + f"{field_info.data_type.value}: {value_str}" + "}",
            )
            result = self._build_query_line(MutationTypes.UPDATE, input_dict)

        return result

    def query_lines_update(self) -> List[str]:
        """Generate the query lines to update all fields of this project item."""
        return [self._query_line_update(field) for field in Fields]


def main():
    table = pd.read_csv(csv_path)
    # For testing on a smaller number of items:
    # table = table[:40]

    project_items: List[ProjectItem] = ProjectItem.items_from_table(table)
    closed_items = [item for item in project_items if item.is_closed]
    open_items = [item for item in project_items if not item.is_closed]

    deletion_lines = [item.query_line_delete() for item in closed_items]
    run_mutation(deletion_lines)

    update_lines = []
    for item in open_items:
        update_lines.extend(item.query_lines_update())
    run_mutation(update_lines)


if __name__ == "__main__":
    main()
