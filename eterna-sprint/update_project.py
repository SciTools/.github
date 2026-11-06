#!/usr/bin/env python3
"""
Script for populating the Eterna Sprint GitHub project with Issues and PRs.

Achieved by running GraphQL queries and mutations against GitHub - the
recommended way to work with GitHub data.
https://docs.github.com/en/graphql

The GraphQL syntax is difficult to work with directly, so we use sgqlc to
provide a pythonic interface. `github_schema.py` helps enumerate what
operations are possible. (For advance use, consider using a GraphQL IDE or IDE
plugin, and parse the schema directly - code completion and syntax highlighting
works well, and sgqlc-codegen can also convert GraphQL into Python code).

Unlike SciTools/.github/peloton, this board tracks Issues and Pull Requests
ONLY (no Discussions), and it NEVER writes the project's Status field - that
is a manually-assigned "sprint board" field that the team drags cards around
on. This script is therefore limited to adding newly-matching issues/PRs to
the project, and removing items that no longer match (e.g. closed long ago).

"""

import abc
from argparse import ArgumentParser
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta
import logging
from time import sleep
from sys import stdout

import pandas as pd

from sgqlc.endpoint.http import HTTPEndpoint
import sgqlc.types
import sgqlc.types.relay
import sgqlc.operation
import github_schema

github_schema = github_schema
github_schema_root = github_schema.github_schema


GITHUB_QUERY_CONDITIONS = (
    "org:SciTools org:SciTools-incubator org:SciTools-classroom "
    # Note `-` negates the condition that follows it.
    "-repo:SciTools/cartopy "
    "repo:bjlittle/geovista repo:pp-mo/ncdata repo:pp-mo/ugrid-checks "
)
"""
https://github.com/search?q=org%3ASciTools+org%3ASciTools-incubator
+org%3ASciTools-classroom+-repo%3ASciTools%2Fcartopy
+repo%3Abjlittle%2Fgeovista+repo%3App-mo%2Fncdata+repo%3App-mo%2Fugrid-checks
"""
CLOSED_THRESHOLD = date.today() - timedelta(days=28)
# Using the negating syntax returns everything that is NOT closed AND
#  everything that was closed after CLOSED_THRESHOLD.
GITHUB_QUERY_CONDITIONS += f" -closed:<{CLOSED_THRESHOLD}"

# The project's number is the last part of its URL, e.g.
#  https://github.com/orgs/SciTools/projects/63 -> 63 . This avoids needing
#  to look up the project's GraphQL node ID by hand.
# TEMPORARY TESTING CONFIG: pointed at @ESadek-MO's personal test project
#  instead of SciTools, to dry-run the script somewhere low-stakes first.
#  Before deploying for real: set back to owner="SciTools", number=63, and
#  swap resolve_project_id() back to operation.organization(...) below.
ETERNA_SPRINT_PROJECT_OWNER = "ESadek-MO"
ETERNA_SPRINT_PROJECT_NUMBER = 5

# Resolved from the above via resolve_project_id(), once ENDPOINT is set up in
#  main(). Module-level since every query/mutation class needs it.
ETERNA_SPRINT_PROJECT_ID: str = None

# Set an interval to avoid update loops over-stressing the GraphQL server.
SECONDS_BETWEEN_UPDATES = 60


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
# Required by run_operation(), set during main() argparsing.
ENDPOINT: HTTPEndpoint = None

# All logging is recorded in the log file.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s \n",
    filename="latest_eterna_sprint_update.log",
    filemode="w",
)


def run_operation(op: sgqlc.operation.Operation) -> github_schema.Query:
    """Execute a GraphQL operation and return the results."""
    result = None
    if hasattr(ENDPOINT, "base_headers"):
        # ENDPOINT has been set.
        if op:
            # Note: sgqlc already logs its queries to logging.DEBUG, so we
            #  get to capture those without our own logging call.
            data = ENDPOINT(op)
            result = op + data
    else:
        message = "ENDPOINT has not been set. Cannot run query."
        raise ValueError(message)

    return result


def resolve_project_id(owner: str, number: int) -> str:
    """
    Look up a GitHub Projects v2 node ID from its owner login + number.

    TEMPORARY TESTING CONFIG: uses `user(login:)` for @ESadek-MO's personal
    test project. SciTools is an org, so switch this to
    `operation.organization(login=owner)` / `result.organization.project_v2.id`
    before deploying for real.
    """
    operation = sgqlc.operation.Operation(github_schema_root.query_type)
    project = operation.user(login=owner).project_v2(number=number)
    project.id()
    result = run_operation(operation)
    return result.user.project_v2.id


###############################################################################
# QUERIES.


class PaginatedQuery(abc.ABC):
    """
    Base class for sgqlc queries that return paginated lists of items.

    Takes care of the heavy lifting for defining pages and detecting the number
    of pages to be returned.
    """

    # GraphQL insists that returned lists are broken into defined pages.
    #  Use _PAGINATION to set the page size (max 100).
    _PAGINATION = 100
    # The 'selector' is the level of the query that is paginated. Different
    #  selectors can accept different arguments (e.g. `search` in the GitHub
    #  schema includes the same search query string used on the website).
    _selector_kwargs: dict = {}

    @dataclass(frozen=True)
    class ColNames:
        """
        Used to access columns in self.data_frame

        The DataFrame is produced from normalised JSON so can have quite a
        long 'path'. This class provides a convenience for extracting the names
        from sqglc objects and storing the resulting column names for
        downstream use.
        """
        @staticmethod
        def _get_element_names(*elements: str | sgqlc.operation.Selection) -> str:
            """
            Extract the names of GraphQL elements, or use strings in place.

            Used to predict a column name resulting from applying
            :meth:`pandas.json_normalize` to the JSON returned by a GraphQL
            query.
            """
            def get_element_name(element):
                if hasattr(element, "__field__"):
                    element_name = (
                        element.__alias__ or element.__field__.graphql_name
                    )
                else:
                    assert isinstance(element, str)
                    element_name = element
                return element_name

            return ".".join([get_element_name(element) for element in elements])

        @classmethod
        def from_sgqlc_trees(cls, **trees: list[str | sgqlc.operation.Selection]):
            """
            Create a ColNames object from a dict of sequences of sgqlc objects.

            Strings can be used at any point in these sequences to hard code
            an expected element name.
            """
            cls_kwargs: dict[str, str] = {
                k: cls._get_element_names(*v)
                for k, v in trees.items()
            }
            return cls(**cls_kwargs)

    def __init__(self):
        """
        Execute the query as defined using the class methods.

        Caller interaction with this instance is limited to accessing
        self.data_frame and self.cols.
        """
        self.cols = None
        self.data_frame = pd.json_normalize(
            [item.__json_data__ for item in self._run_query()]
        )
        assert self.cols is not None
        self._post_process()

    @staticmethod
    @abc.abstractmethod
    def _make_selector(
            operation: sgqlc.operation.Operation
    ) -> sgqlc.operation.Selector:
        """Create the element of the GraphQL query that will be paginated."""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def _extract_page(result: github_schema.Query) -> sgqlc.types.relay.Connection:
        """
        Get the page of results from the JSON returned by a GraphQL query.
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def _extract_page_items(page: sgqlc.types.relay.Connection) -> list:
        """Get the list of results from a page of results."""
        raise NotImplementedError

    @abc.abstractmethod
    def _add_query_fields(self, page: sgqlc.operation.Selection) -> None:
        """Use sgqlc to populate a query page with the required fields."""
        raise NotImplementedError

    def _build_query(self, after: str = None) -> sgqlc.operation.Operation:
        """
        Use sgqlc to build a GraphQL query for a page of results.

        :meth:`_make_selector` and :meth:`_add_query_fields` are used to
        specialise this pattern for different queries - need different
        sequences of sgqlc attributes depending on the structure.
        """
        operation = sgqlc.operation.Operation(github_schema_root.query_type)
        selector = self._make_selector(operation)
        page = selector(first=self._PAGINATION, after=after, **self._selector_kwargs)
        self._add_query_fields(page)
        page.page_info.__fields__(has_next_page=True, end_cursor=True)
        return operation

    def _run_query(self) -> list:
        """
        Execute a built query, looping to produce pages, return combined results.

        :meth:`_build_query`, :meth:`_extract_page` and
        :meth:`_extract_page_items` are used to specialise this pattern for
        different queries - need different sequences of sgqlc attributes
        depending on the structure.
        """
        all_items = []
        has_next_page = True
        end_cursor = None

        while has_next_page:
            query = self._build_query(after=end_cursor)
            result = run_operation(query)
            page = self._extract_page(result)

            page_info = page.page_info
            has_next_page = page_info.has_next_page
            end_cursor = page_info.end_cursor

            page_items = self._extract_page_items(page)
            all_items.extend(page_items)

        return all_items

    def _post_process(self) -> None:
        """
        Modify self.data_frame (having populating with results from the query).
        """
        cols: PaginatedQuery.ColNames = getattr(self, "cols")
        for field in fields(cols):
            # GraphQL will not return an element with the expected 'path' if
            #  the project field is fully unpopulated.
            col_name = getattr(cols, field.name)
            if col_name not in self.data_frame.columns:
                self.data_frame[col_name] = None


class ProjectItemsQuery(PaginatedQuery):
    """
    Query the Eterna Sprint GitHub project to get the items it contains.

    Unlike Peloton, every item here is a linked Issue/PR (never a draft), so
    we can read GitHub's native `content` link directly - no custom
    `_linked_id` field is needed.
    """
    @dataclass(frozen=True)
    class ColNames(PaginatedQuery.ColNames):
        id_in_project: str
        linked_id: str

    @staticmethod
    def _make_selector(
        operation: sgqlc.operation.Operation
    ) -> sgqlc.operation.Selector:
        project = operation.node(id=ETERNA_SPRINT_PROJECT_ID)
        return project.__as__(github_schema.ProjectV2).items

    @staticmethod
    def _extract_page(result: github_schema.Query) -> sgqlc.types.relay.Connection:
        return result.node.items

    @staticmethod
    def _extract_page_items(page: sgqlc.types.relay.Connection) -> list:
        return page.nodes

    def _add_query_fields(self, page: sgqlc.operation.Selection) -> None:
        nodes = page.nodes()
        id_in_project = nodes.id(__alias__="id_in_project")

        content = nodes.content()
        linked_id = None
        for item_type in (github_schema.Issue, github_schema.PullRequest):
            typed_content = content.__as__(item_type)
            linked_id = typed_content.id(__alias__="linked_id")

        if self.cols is None:
            # This is run in a loop, but we only need to get the column names
            #  once.
            self.cols = self.ColNames.from_sgqlc_trees(
                id_in_project=[id_in_project],
                linked_id=[content, linked_id],
            )

    def _post_process(self) -> None:
        super()._post_process()
        self.data_frame.set_index(self.cols.id_in_project, inplace=True)


class IssuesQuery(PaginatedQuery):
    """
    Query GitHub using the GH search syntax to get issues and pull requests.
    """
    _selector_kwargs = dict(type="ISSUE")
    _item_types = (github_schema.Issue, github_schema.PullRequest)

    @dataclass(frozen=True)
    class ColNames(PaginatedQuery.ColNames):
        id_: str
        url: str
        number_: str
        title: str
        created_at: str
        updated_at: str
        closed_at: str

    def __init__(self, github_query_conditions: str):
        # Specific query conditions can be passed by the caller, and then
        #  are combined with the fixed query kwargs.

        # Copy mutable object before modifying.
        self._selector_kwargs = dict(self.__class__._selector_kwargs)
        self._selector_kwargs["query"] = github_query_conditions

        super().__init__()

    @staticmethod
    def _make_selector(
        operation: sgqlc.operation.Operation
    ) -> sgqlc.operation.Selector:
        return operation.search

    @staticmethod
    def _extract_page(result: github_schema.Query) -> sgqlc.types.relay.Connection:
        return result.search

    @staticmethod
    def _extract_page_items(page: sgqlc.types.relay.Connection) -> list:
        return page.edges

    def _add_query_fields(self, page) -> None:
        nodes = page.edges().node()
        for item_type in self._item_types:
            item: github_schema.Issue | github_schema.PullRequest = (
                nodes.__as__(item_type)
            )

            id_ = item.id()
            url_ = item.url()
            number_ = item.number()
            title = item.title()
            created_at = item.created_at()
            updated_at = item.updated_at()
            closed_at = item.closed_at()

            if self.cols is None:
                # This is run in a loop, but we only need to get the column
                #  names once.
                self.cols = self.ColNames.from_sgqlc_trees(
                    id_=[nodes, id_],
                    url=[nodes, url_],
                    number_=[nodes, number_],
                    title=[nodes, title],
                    created_at=[nodes, created_at],
                    updated_at=[nodes, updated_at],
                    closed_at=[nodes, closed_at],
                )

    def _post_process(self) -> None:
        super()._post_process()
        self.data_frame.set_index(self.cols.id_, inplace=True)


###############################################################################
# MUTATIONS.


class PaginatedMutation(abc.ABC):
    """
    Base class for sgqlc mutations, including pagination to avoid timeouts.
    """

    # _PAGINATION defines the number of mutation fields to include in one
    #  mutation. If more are needed, the fields will be broken into
    #  multiple pages.
    _PAGINATION = 20

    @property
    def _inputs_default(self) -> dict:
        # A property (not a class attribute) since ETERNA_SPRINT_PROJECT_ID
        #  is only resolved once main() has set up ENDPOINT - after this
        #  class is first defined/imported.
        return dict(project_id=ETERNA_SPRINT_PROJECT_ID)

    def __init__(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issues_cols: IssuesQuery.ColNames,
    ):
        """
        Execute the mutation as defined using the class methods.

        Caller interaction with this instance is limited to accessing
        self.result.
        """
        self._inputs = self._make_inputs(data_frame, project_cols, issues_cols)
        self._indexes = list(range(len(self._inputs)))
        # A mutation can only contain multiple 'fields' if they have different
        #  names from each other.
        self._aliases = [f"op_{ix}" for ix in self._indexes]

        page_slices = [
            slice(i, i + self._PAGINATION)
            for i in range(0, len(self._inputs), self._PAGINATION)
        ]
        result_lists = []
        for page_slice in page_slices:
            result_lists.append(self._run_sub_mutation(page_slice))
            # Avoid rate limiting from GitHub.
            sleep(5)
        self._result = self._get_data_from_sub_mutations(result_lists)

    @abc.abstractmethod
    def _make_inputs(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issue_cols: IssuesQuery.ColNames,
    ) -> list[dict]:
        """
        Create the full sequence of `inputs` args for the mutation.

        Represents the full sequence of fields that will be included in
        the mutation.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _add_selector(
        self,
        mutation: sgqlc.operation.Operation,
        index: int
    ) -> None:
        """
        Populate `mutation` with a field that takes self.inputs[index].

        E.g.
            mutation.add_project_v2_item_by_id(
                input=self._inputs[index], __alias__=self._aliases[index]
            )
        """
        raise NotImplementedError

    @property
    def result(self) -> list | None:
        """The output of the mutation (if any). Read-only"""
        return self._result

    def _run_sub_mutation(self, page_slice: slice) -> list:
        """
        Build, run and return results from a mutation for one page of fields.
        """
        mutation = sgqlc.operation.Operation(github_schema_root.mutation_type)
        for ix in self._indexes[page_slice]:
            self._add_selector(mutation=mutation, index=ix)

        # Handle unpredictable GitHub timeouts.
        result = None
        exception = None
        for attempts in range(5):
            try:
                result = run_operation(mutation)
                break
            except Exception as exc:
                exception = exc

            sleep(5)

        if result is not None:
            # Fields are accessed from mutation results via their keys.
            payloads = [result[a] for a in self._aliases[page_slice]]
            return payloads
        elif exception is not None:
            raise exception
        else:
            message = "Unexpected: mutation returned no result and no exception."
            raise RuntimeError(message)

    def _get_data_from_sub_mutations(self, payloads: list[list]) -> list | None:
        """
        Extract data from the nested results list that a mutation returns.

        Provided for mutations that need to return something e.g. IDs of
        issues newly added to the project. Otherwise: no need to subclass.
        """
        return None


class AddIssuesMutation(PaginatedMutation):
    """
    Mutation to add Issues/PRs to the Eterna Sprint GitHub project.

    Added via the IDs of the issue/PR itself, and records (self.results) the
    IDs of the corresponding items in the project.
    """
    def _make_inputs(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issue_cols: IssuesQuery.ColNames,
    ) -> list[dict]:
        return [
            # Expecting a DataFrame where the required column is the index.
            (self._inputs_default | dict(content_id=row.name))
            for _, row in data_frame.iterrows()
        ]

    def _add_selector(
        self,
        mutation: sgqlc.operation.Operation,
        index: int
    ) -> None:
        add = mutation.add_project_v2_item_by_id(
            input=self._inputs[index], __alias__=self._aliases[index]
        )
        add.item().id()

    def _get_data_from_sub_mutations(
        self,
        payloads: list[list[github_schema.AddProjectV2ItemByIdPayload]]
    ) -> list[str]:
        result = []
        for sub_list in payloads:
            ids_in_project = [p.item.id for p in sub_list]
            result.extend(ids_in_project)
        return result


class RemoveItemsMutation(PaginatedMutation):
    """Mutation to remove items from the Eterna Sprint GitHub project."""
    def _make_inputs(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issue_cols: IssuesQuery.ColNames,
    ) -> list[dict]:
        return [
            # Expecting a DataFrame where the required column is the index.
            (self._inputs_default | dict(item_id=row.name))
            for _, row in data_frame.iterrows()
        ]

    def _add_selector(
        self,
        mutation: sgqlc.operation.Operation,
        index: int
    ) -> None:
        mutation.delete_project_v2_item(
            input=self._inputs[index], __alias__=self._aliases[index]
        ).client_mutation_id()


###############################################################################


def log_data_frame_items(
    data_frame: pd.DataFrame,
    message: str,
    url_col: str = None
) -> None:
    """
    Logging of HOW MANY, and WHAT, items were involved in a script step.
    """
    logging.info(f"{message}: {len(data_frame)} items")
    if url_col is not None and not data_frame.empty:
        url_list = "\n".join(data_frame[url_col].tolist())
        logging.debug(f"{message}:\n{url_list}")


def main():
    parser = ArgumentParser(
        prog="EternaSprintUpdate",
        description="Update the Eterna Sprint GitHub Project with issues and PRs",
    )
    parser.add_argument(
        "--bearer_token",
        help=(
            "GitHub personal access token with these scopes: project, repo, "
            "read:org ."
        ),
        type=str
    )
    parser.add_argument(
        "--update_loop_minutes",
        help=(
            "Number of minutes that the script will loop for, updating any "
            "issues/PRs that have changed since the last loop. Intended for "
            "use during meetings - for live updating."
        ),
        default=0,
        type=int,
    )
    parser.add_argument(
        "--verbose",
        help="Print debug information, including all queries that are run.",
        action="store_true",
    )
    bearer_token = parser.parse_args().bearer_token
    update_loop_minutes = parser.parse_args().update_loop_minutes
    verbose = parser.parse_args().verbose

    # Connect to GitHub GraphQL using provided credentials.
    global ENDPOINT
    ENDPOINT = HTTPEndpoint(
        url=GITHUB_GRAPHQL_URL,
        base_headers=dict(Authorization=f"bearer {bearer_token}")
    )

    # `console` allows a configurable level at which logging is also sent
    #  to STDOUT.
    console = logging.StreamHandler(stdout)
    console.setFormatter(logging.Formatter("%(asctime)s %(message)s",))
    if verbose:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    logging.getLogger("").addHandler(console)

    global ETERNA_SPRINT_PROJECT_ID
    ETERNA_SPRINT_PROJECT_ID = resolve_project_id(
        ETERNA_SPRINT_PROJECT_OWNER, ETERNA_SPRINT_PROJECT_NUMBER
    )
    logging.info(f"Resolved project node ID: {ETERNA_SPRINT_PROJECT_ID}")

    update_loop_finish_time = datetime.now() + timedelta(minutes=update_loop_minutes)
    last_update_loop_time = None
    updates_only = False

    while not updates_only or datetime.now() < update_loop_finish_time:
        if updates_only:
            logging.info("Starting incremental update loop ...")
        else:
            logging.info("Starting full refresh ...")

        logging.info("    Fetching data ...")

        project = ProjectItemsQuery()
        logging.debug(f"    Project has {len(project.data_frame)} items.")

        query_string = GITHUB_QUERY_CONDITIONS
        if updates_only:
            query_string = (
                f"{GITHUB_QUERY_CONDITIONS} updated:>="
                f"{last_update_loop_time.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )
        # Capture the time immediately before running the query.
        #  (And immediately after encoding the previous value in the query
        #  condition, if we're in an updates_only loop).
        last_update_loop_time = datetime.now()
        issues = IssuesQuery(query_string)
        logging.debug(f"    Query returned {len(issues.data_frame)} issues/PRs.")

        logging.info("    Data fetch complete.")

        if not updates_only:
            # Removes all remaining project items that do not correspond with
            #  issues/PRs returned in the query. E.g. an issue closed so long
            #  ago that today's query no longer includes it.

            # This is only run once, during the initial loop that gets
            #  everything we want to be in the project. Subsequent loops
            #  being limited to recent updates would mark almost every
            #  project item for removal.
            no_linked_id = project.data_frame[project.cols.linked_id].isnull()
            orphaned_linked_ids = ~project.data_frame[project.cols.linked_id].isin(
                issues.data_frame.index
            )
            items_to_remove = project.data_frame[no_linked_id | orphaned_linked_ids]
            log_data_frame_items(items_to_remove, "    Removing from project")
            RemoveItemsMutation(items_to_remove, project.cols, issues.cols)

        already_in_project = issues.data_frame.index.isin(
            project.data_frame[project.cols.linked_id]
        )
        issues_to_add = issues.data_frame[~already_in_project]
        log_data_frame_items(
            issues_to_add,
            "    Adding issues/PRs to project",
            issues.cols.url
        )
        AddIssuesMutation(issues_to_add, project.cols, issues.cols)

        if not updates_only:
            logging.info(
                "Full refresh complete. Incremental updates will loop until "
                f"{update_loop_finish_time.strftime('%H:%M:%S')} , "
                f"with {SECONDS_BETWEEN_UPDATES} second gaps."
            )
        else:
            logging.info("Incremental update loop complete.")
        # Subsequent loops (if any) will be limited to issues/PRs updated
        #  since the last loop.
        updates_only = True
        sleep(SECONDS_BETWEEN_UPDATES)


if __name__ == "__main__":
    main()
