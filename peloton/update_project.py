#!/usr/bin/env python3
"""
Script for populating the Peloton GitHub project with Issues and Discussions.

https://github.com/orgs/SciTools/projects/13?pane=info

Achieved by running GraphQL queries and mutations against GitHub - the
recommended way to work with GitHub data.
https://docs.github.com/en/graphql

The GraphQL syntax is difficult to work with directly, so we use sgqlc to
provide a pythonic interface. `github_schema.py` helps enumerate what
operations are possible. (For advance use, consider using a GraphQL IDE or IDE
plugin, and parse the schema directly - code completion and syntax highlighting
works well, and sgqlc-codegen can also convert GraphQL into Python code).

"""

import abc
from argparse import ArgumentParser
from dataclasses import dataclass, asdict, fields
from datetime import date, datetime, timedelta
from enum import StrEnum
import logging
from string import printable
from time import sleep
from sys import stdout

import numpy as np
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

PELOTON_PROJECT_ID = "PVT_kwDOABU7f84ALhAI"

# Set an interval to avoid update loops over-stressing the GraphQL server.
SECONDS_BETWEEN_UPDATES = 60


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
# Required by run_operation(), set during main() argparsing.
ENDPOINT: HTTPEndpoint = None

# All logging is recorded in the log file.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s \n",
    filename="latest_peloton_update.log",
    filemode="w",
)


def datetime_str_to_date_str(datetimes: str | pd.Series) -> str:
    """
    Get just the date string from an ISO datetime string.

    Can also operate on an entire :class:`pandas.Series` of strings.
    """
    if hasattr(datetimes, "str"):
        object_to_index = datetimes.str
    else:
        assert isinstance(datetimes, str)
        object_to_index = datetimes
    return object_to_index[:10]


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


class SelectionIds(StrEnum):
    """
    Ids to use for project fields that accept `singleSelectOptionId` inputs.

    Use ProjectFieldsQuery to get the latest info on this.
    """

    AUTHOR_PELOTON = "389ebec0"
    AUTHOR_EXTERNAL = "d961b9b7"
    AUTHOR_BOT = "8fbf3584"
    COMMENTER_PELOTON = "98462be7"
    COMMENTER_EXTERNAL = "235b3d90"
    COMMENTER_BOT = "54adc7eb"
    DISCUSSION_WANTED = "e17f4b18"


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
    """Query the Peloton GitHub project to get the items it contains."""
    @dataclass(frozen=True)
    class ColNames(PaginatedQuery.ColNames):
        id_in_project: str
        linked_id: str
        date_updated: str
        final_comment_time: str
        num_comments: str

    @staticmethod
    def _make_selector(
        operation: sgqlc.operation.Operation
    ) -> sgqlc.operation.Selector:
        project = operation.node(id=PELOTON_PROJECT_ID)
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

        linked_id_field = nodes.field_value_by_name(
            name="_linked_id",
            __alias__="linked_id",
        )
        linked_id_value = linked_id_field.__as__(
            github_schema.ProjectV2ItemFieldTextValue
        )
        linked_id = linked_id_value.text()

        date_updated_field = nodes.field_value_by_name(
            name="Date Updated",
            __alias__="date_updated",
        )
        date_updated_value = date_updated_field.__as__(
            github_schema.ProjectV2ItemFieldDateValue
        )
        date_updated = date_updated_value.date()

        final_comment_field = nodes.field_value_by_name(
            name="Final Comment Time",
            # Avoid a name clash with IssuesQuery.
            __alias__="final_comment_time_project",
        )
        final_comment_time_value = final_comment_field.__as__(
            github_schema.ProjectV2ItemFieldDateValue
        )
        final_comment_time = final_comment_time_value.date()

        num_comments_field = nodes.field_value_by_name(
            name="Num Comments",
            __alias__="num_comments",
        )
        num_comments_value = num_comments_field.__as__(
            github_schema.ProjectV2ItemFieldNumberValue
        )
        num_comments = num_comments_value.number()

        if self.cols is None:
            # This is run in a loop, but we only need to get the column names
            #  once.
            self.cols = self.ColNames.from_sgqlc_trees(
                id_in_project=[id_in_project],
                linked_id=[linked_id_field, linked_id],
                date_updated=[date_updated_field, date_updated],
                final_comment_time=[final_comment_field, final_comment_time],
                num_comments=[num_comments_field, num_comments]
            )

    def _post_process(self) -> None:
        super()._post_process()
        self.data_frame.set_index(self.cols.id_in_project, inplace=True)


class ProjectFieldsQuery(PaginatedQuery):
    """
    Query the Peloton GitHub project to get the fields it has.

    https://docs.github.com/en/issues/planning-and-tracking-with-projects
    /automating-your-project/
    using-the-api-to-manage-projects#finding-the-node-id-of-a-field
    """
    @dataclass(frozen=True)
    class ColNames(PaginatedQuery.ColNames):
        id_: str
        name_: str
        data_type: str
        config_data: str
        options_data: str

    @staticmethod
    def _make_selector(
        operation: sgqlc.operation.Operation
    ) -> sgqlc.operation.Selector:
        project = operation.node(id=PELOTON_PROJECT_ID)
        return project.__as__(github_schema.ProjectV2).fields

    @staticmethod
    def _extract_page(result: github_schema.Query) -> sgqlc.types.relay.Connection:
        return result.node.fields

    @staticmethod
    def _extract_page_items(page: sgqlc.types.relay.Connection) -> list:
        return page.nodes

    def _add_query_fields(self, page: sgqlc.operation.Selection) -> None:
        nodes = page.nodes()

        for field_type in (
                github_schema.ProjectV2Field,
                github_schema.ProjectV2IterationField,
                github_schema.ProjectV2SingleSelectField
        ):
            field = nodes.__as__(field_type)

            id_ = field.id()
            name_ = field.name()
            data_type = field.data_type()

            # In-fill with string to make column naming work in absence of
            #  actual field.
            config_data = "config_data"
            if field_type is github_schema.ProjectV2IterationField:
                config_data = field.configuration()
                iters = config_data.iterations()
                iters.start_date()
                iters.id()

            options_data = "options_data"
            if field_type is github_schema.ProjectV2SingleSelectField:
                options_data = field.options()
                options_data.id()
                options_data.name()

        if self.cols is None:
            # This is run in a loop, but we only need to get the column names
            #  once.
            self.cols = self.ColNames.from_sgqlc_trees(
                id_=[id_],
                name_=[name_],
                data_type=[data_type],
                config_data=[config_data],
                options_data=[options_data],
            )

    def _post_process(self) -> None:
        super()._post_process()
        self.data_frame.set_index(self.cols.id_, inplace=True)

        type_mapping = dict(
            DATE=github_schema.ProjectV2FieldValue.date,
            NUMBER=github_schema.ProjectV2FieldValue.number,
            SINGLE_SELECT=github_schema.ProjectV2FieldValue.single_select_option_id,
            TEXT=github_schema.ProjectV2FieldValue.text,
        )

        data_types = [
            type_mapping[dt]
            if dt in type_mapping else None
            for dt in self.data_frame[self.cols.data_type]
        ]
        self.data_frame[self.cols.data_type] = data_types


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
        total_comments: str
        final_comment_data: str
        created_at: str
        updated_at: str
        closed_at: str
        author_login: str
        author_bot_id: str
        votes: str
        labels_data: str

        # Columns not populated directly by the query, but used downstream.
        discussion_wanted: str = "discussion_wanted"
        author_membership: str = "author_type"
        commenter_membership: str = "commenter_type"

        final_comment_login: str = "final_comment_login"
        final_comment_bot_id: str = "final_comment_bot_id"
        final_comment_time: str = "final_comment_time"

        # Marks whether we are forced to use a Project draft object for this
        #  item since it cannot be officially linked. Issues/PRs can be linked,
        #  Discussions cannot be linked.
        use_draft: str = "use_draft"

        @property
        def project_field_map(self) -> dict:
            """
            The corresponding IDs of the Peloton GitHub project fields.

            Run ProjectFieldsQuery to get the latest info on this.
            """
            return {
                "PVTF_lADOABU7f84ALhAIzgHV-jI": self.created_at,
                "PVTF_lADOABU7f84ALhAIzgHV_kc": self.final_comment_login,
                "PVTF_lADOABU7f84ALhAIzgHV_lI": self.final_comment_time,
                "PVTF_lADOABU7f84ALhAIzgLbMPM": self.total_comments,
                "PVTF_lADOABU7f84ALhAIzgLbMRM": self.updated_at,
                "PVTF_lADOABU7f84ALhAIzgLbMTQ": self.closed_at,
                "PVTF_lADOABU7f84ALhAIzgLbMn8": self.author_login,
                "PVTF_lADOABU7f84ALhAIzgLbM0k": self.votes,
                "PVTSSF_lADOABU7f84ALhAIzgLbNmc": self.author_membership,
                "PVTSSF_lADOABU7f84ALhAIzgLbNsM": self.commenter_membership,
                "PVTSSF_lADOABU7f84ALhAIzgLlAMk": self.discussion_wanted,
            }

    def __init__(self, github_query_conditions: str, peloton_logins: list[str]):
        # Specific query conditions can be passed by the caller, and then
        #  are combined with the fixed query kwargs.

        # Copy mutable object before modifying.
        self._selector_kwargs = dict(self.__class__._selector_kwargs)
        self._selector_kwargs["query"] = github_query_conditions

        self._peloton_logins = list(peloton_logins)

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
            # Type for Discussion to help check this also works when sub-classed.
            item: github_schema.Issue | github_schema.PullRequest | github_schema.Discussion = (
                nodes.__as__(item_type)
            )

            id_ = item.id()
            url_ = item.url()
            number_ = item.number()
            title = item.title()
            created_at = item.created_at()
            updated_at = item.updated_at()
            closed_at = item.closed_at()
            author = item.author()
            author_login = author.login()

            votes = item.reactions(
                content=github_schema.ReactionContent("THUMBS_UP"),
                __alias__="votes"
            )
            total_votes = votes.total_count()

            labels = item.labels(first=100)
            labels_nodes = labels.nodes()
            # No assignment as this just adds data to labels_nodes.
            labels_nodes.name()

            comments = item.comments()
            total_comments = comments.total_count()
            final_comment: sgqlc.operation.Selection = item.comments(
                last=1,
                __alias__="final_comment"
            )
            final_comment_nodes = final_comment.nodes()
            # No assignment as this just adds data to final_comment_nodes.
            final_comment_nodes.author().login()
            final_comment_nodes.created_at()

            # Work out if logins are Bot accounts.
            #  More awkward to use __as__() (rather than __typename__()), but
            #  if GitHub change something we can actually get a failure (rather
            #  than text matching, which would fail silently).
            author_bot = author.__as__(github_schema.Bot)
            author_bot_id = author_bot.id(__alias__="bot_id")
            # No assignment as this just adds data to final_comment_nodes.
            final_comment_nodes.author().__as__(github_schema.Bot).id(__alias__="bot_id")

            if self.cols is None:
                # This is run in a loop, but we only need to get the column
                #  names once.
                self.cols = self.ColNames.from_sgqlc_trees(
                    id_=[nodes, id_],
                    url=[nodes, url_],
                    number_=[nodes, number_],
                    title=[nodes, title],
                    total_comments=[nodes, comments, total_comments],
                    final_comment_data=[nodes, final_comment, final_comment_nodes],
                    created_at=[nodes, created_at],
                    updated_at=[nodes, updated_at],
                    closed_at=[nodes, closed_at],
                    author_login=([nodes, author, author_login]),
                    votes=[nodes, votes, total_votes],
                    labels_data=[nodes, labels, labels_nodes],
                    author_bot_id=[nodes, author, author_bot_id]
                )

    def _get_final_comment_details(self, issue: pd.Series) -> tuple[str, str, str]:
        """Use author info to back-fill if no final comment exists."""
        final_comment = issue[self.cols.final_comment_data]
        if not final_comment:
            final_comment_login = issue[self.cols.author_login]
            final_comment_bot_id = issue[self.cols.author_bot_id]
            final_comment_time = issue[self.cols.created_at]
        else:
            final_comment = final_comment[0]
            final_comment_login = final_comment["author"]["login"]
            final_comment_bot_id = final_comment["author"].get("bot_id", None)
            final_comment_time = final_comment["createdAt"]
        return final_comment_login, final_comment_bot_id, final_comment_time

    def _categorise_logins(self) -> None:
        """Apply the Peloton project's login categories to this data."""
        def categorise_column(column: pd.Series):
            if column.name == self.cols.author_login:
                bot_column = self.data_frame[self.cols.author_bot_id]
                is_peloton = SelectionIds.AUTHOR_PELOTON
                is_bot = SelectionIds.AUTHOR_BOT
                is_external = SelectionIds.AUTHOR_EXTERNAL
            elif column.name == self.cols.final_comment_login:
                bot_column = self.data_frame[self.cols.final_comment_bot_id]
                is_peloton = SelectionIds.COMMENTER_PELOTON
                is_bot = SelectionIds.COMMENTER_BOT
                is_external = SelectionIds.COMMENTER_EXTERNAL
            else:
                raise NotImplementedError

            # We always categorise these users as bots, regardless of GitHub
            #  labelling.
            bot_override_users = ["CLAassistant", "codecov-commenter"]

            return np.select(
                condlist=[
                    column.isin(self._peloton_logins),
                    ~bot_column.isnull() | column.isin(bot_override_users),
                ],
                choicelist=[
                    is_peloton,
                    is_bot,
                ],
                default=is_external
            )

        if not self.data_frame.empty:
            self.data_frame[self.cols.author_membership] = (
                categorise_column(self.data_frame[self.cols.author_login])
            )
            self.data_frame[self.cols.commenter_membership] = (
                categorise_column(self.data_frame[self.cols.final_comment_login])
            )

    def _post_process(self) -> None:
        super()._post_process()

        self.data_frame.set_index(self.cols.id_, inplace=True)

        if not self.data_frame.empty:
            self.data_frame[self.cols.use_draft] = False

            final_comment_logins, final_comment_bots, final_comment_times = zip(
                *[
                    self._get_final_comment_details(issue)
                    for _, issue in self.data_frame.iterrows()
                ])
            self.data_frame[self.cols.final_comment_login] = final_comment_logins
            self.data_frame[self.cols.final_comment_bot_id] = final_comment_bots
            self.data_frame[self.cols.final_comment_time] = final_comment_times

            labels = self.data_frame[self.cols.labels_data]
            discuss_regex = r"decision|help|discussion"
            self.data_frame.loc[
                labels.astype(str).str.contains(discuss_regex, case=False),
                self.cols.discussion_wanted
            ] = SelectionIds.DISCUSSION_WANTED

            self._categorise_logins()


class DiscussionsQuery(IssuesQuery):
    """
    Query GitHub using the GH search syntax to get discussions.

    Discussions share a lot of properties with Issues, so we can reuse
    much of the parent class.
    """
    _selector_kwargs = IssuesQuery._selector_kwargs | dict(type="DISCUSSION")
    _item_types = (github_schema.Discussion,)

    @dataclass(frozen=True)
    class ColNames(IssuesQuery.ColNames):
        # Need default values so that parent can create self.cols first -
        #  setting most of the values upstream.
        comments_data: str = NotImplemented
        total_replies: str = NotImplemented
        final_reply_data: str = NotImplemented

    def _add_query_fields(self, page) -> None:
        super()._add_query_fields(page)
        nodes = page.edges().node()
        discussion: github_schema.Discussion = nodes.__as__(github_schema.Discussion)

        comments = discussion.comments(
            first=100,
            __alias__="discussion_comments",
        )
        comments_edges = comments.edges()
        comments_nodes = comments_edges.node()
        replies = comments_nodes.replies()

        total_replies = replies.total_count()
        final_reply = comments_nodes.replies(
            last=1,
            __alias__="comment_final_reply",
        )
        final_reply_nodes = final_reply.nodes()
        # Add data to final_reply_nodes.
        final_reply_nodes.author().login()
        final_reply_nodes.created_at()

        self.cols: DiscussionsQuery.ColNames
        if self.cols.comments_data is NotImplemented:
            # This is run in a loop, but we only need to get the column names
            #  once.
            cols_original = {
                f.name: getattr(self.cols, f.name)
                for f in fields(self.cols)
                if f in fields(IssuesQuery.ColNames)
            }
            cols_extra = self.ColNames.from_sgqlc_trees(
                comments_data=[nodes, comments, comments_edges],
                total_replies=[comments_nodes, replies, total_replies],
                final_reply_data=[comments_nodes, final_reply, final_reply_nodes],
                # Need to specify the original fields to create a valid
                #  dataclass, but we are not using their values.
                **{k: [] for k in cols_original.keys()},
            )
            self.cols = self.ColNames(**asdict(cols_extra) | cols_original)

    def _post_process(self) -> None:
        super()._post_process()

        if not self.data_frame.empty:
            # Data on Discussion comments and replies is very nested.
            #  Drill-down to derive data on the latest comment/reply.
            self.data_frame[self.cols.discussion_wanted] = SelectionIds.DISCUSSION_WANTED
            self.data_frame[self.cols.use_draft] = True

            for ix, row in self.data_frame.iterrows():
                reply_thread = row[self.cols.comments_data]
                reply_thread_df = pd.json_normalize(reply_thread)
                if reply_thread_df.empty:
                    continue
                else:
                    self.data_frame.loc[ix, self.cols.total_comments] += (
                        reply_thread_df[self.cols.total_replies].sum()
                    )

                    final_reply_data = reply_thread_df[self.cols.final_reply_data]
                    final_reply_df = pd.json_normalize(
                        [row[0] for row in final_reply_data if len(row) > 0]
                    )
                    if final_reply_df.empty:
                        continue
                    else:
                        final_reply_row = (
                            final_reply_df.sort_values("createdAt").iloc[-1]
                        )
                        final_reply_time = final_reply_row["createdAt"]
                        final_reply_login = final_reply_row["author.login"]
                        # GitHub GraphQL is not prepared for bots to reply
                        #  on discussions.
                        final_reply_bot_id = None

                        if final_reply_time > row[self.cols.final_comment_time]:
                            self.data_frame.loc[ix, self.cols.final_comment_time] = (
                                final_reply_time
                            )
                            self.data_frame.loc[ix, self.cols.final_comment_login] = (
                                final_reply_login
                            )
                            self.data_frame.loc[ix, self.cols.final_comment_bot_id] = (
                                final_reply_bot_id
                            )

            self._categorise_logins()


class PelotonTeamQuery(PaginatedQuery):
    """Query the Peloton GitHub team to get its members."""
    @dataclass(frozen=True)
    class ColNames(PaginatedQuery.ColNames):
        login: str

    @staticmethod
    def _make_selector(
        operation: sgqlc.operation.Operation
    ) -> sgqlc.operation.Selector:
        organization = operation.organization(login="SciTools")
        team = organization.team(slug="Peloton")
        return team.members

    @staticmethod
    def _extract_page(result: github_schema.Query) -> sgqlc.types.relay.Connection:
        return result.organization.team.members

    @staticmethod
    def _extract_page_items(page: sgqlc.types.relay.Connection) -> list:
        return page.nodes

    def _add_query_fields(self, page) -> None:
        nodes = page.nodes()
        login = nodes.login()

        if self.cols is None:
            # This is run in a loop, but we only need to get the column names
            #  once.
            self.cols = self.ColNames.from_sgqlc_trees(
                login=[login],
            )

    def _post_process(self) -> None:
        super()._post_process()
        # @rcomer has asked not to receive notifications for the
        #  SciTools/peloton GitHub team, so is not a member and instead is
        #  added here.
        self.data_frame.loc[len(self.data_frame)] = (
            {self.cols.login: "rcomer"}
        )


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
    # All mutation fields include an `inputs` argument. The contents vary but
    #  will always refer to the Peloton project.
    _inputs_default = dict(project_id=PELOTON_PROJECT_ID)

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
    Mutation to add Issues to the Peloton GitHub project.

    Added via the IDs of the issues itself, and records (self.results) the
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


class AddDraftsMutation(PaginatedMutation):
    """
    Mutation to add Discussions to the Peloton GitHub project.

    Added by adding project 'drafts' - via a given title and body text - and
    records (self.results) the IDs of the corresponding items in the project.
    """
    def _make_inputs(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issue_cols: IssuesQuery.ColNames,
    ) -> list[dict]:
        inputs = []
        for _, row in data_frame.iterrows():
            title = row[issue_cols.title]
            # TODO: how to avoid bad unicode escape sequence with emojis?
            #  sgqlc uses bytes(op).decode('utf-8') on its queries which
            #  might be the
            #  source of the problem.
            title = "".join(filter(lambda t: t in set(printable), title))
            inputs.append((
                self._inputs_default
                |
                dict(title=title, body=row[issue_cols.url])
            ))
        return inputs

    def _add_selector(
        self,
        mutation: sgqlc.operation.Operation,
        index: int
    ) -> None:
        add = mutation.add_project_v2_draft_issue(
            input=self._inputs[index], __alias__=self._aliases[index]
        )
        add.project_item().id()

    def _get_data_from_sub_mutations(
        self,
        payloads: list[list[github_schema.AddProjectV2DraftIssuePayload]]
    ) -> list[str]:
        result = []
        for sub_list in payloads:
            ids_in_project = [p.project_item.id for p in sub_list]
            result.extend(ids_in_project)
        return result


class ClearPelotonDateMutation(PaginatedMutation):
    """
    Mutation clearing next-peloton-date field from items in the Peloton project.

    Used when there has been an update to the issue/discussion in question,
    meriting that it be revisited in an upcoming Peloton meeting.
    """
    NEXT_PELOTON_DATE_FIELD = "PVTF_lADOABU7f84ALhAIzgP3vFs"
    _inputs_default = (
        PaginatedMutation._inputs_default
        |
        dict(field_id=NEXT_PELOTON_DATE_FIELD)
    )

    def _make_inputs(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issue_cols: IssuesQuery.ColNames,
    ) -> list[dict]:
        return [
            (self._inputs_default | dict(item_id=row[project_cols.id_in_project]))
            for _, row in data_frame.iterrows()
        ]

    def _add_selector(
        self,
        mutation: sgqlc.operation.Operation,
        index: int
    ) -> None:
        mutation.clear_project_v2_item_field_value(
            input=self._inputs[index], __alias__=self._aliases[index]
        ).client_mutation_id()


class RemoveItemsMutation(PaginatedMutation):
    """Mutation to remove items from the Peloton GitHub project."""
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


class UpdateItemsMutation(PaginatedMutation):
    """
    Mutation to update the fields of items in the Peloton project.

    More complex than the other subclasses, which each did one 'thing' to one
    issue/item/discussion. Here we need to update each field of each project
    item.
    """
    # The field in the project that contains the ID of the linked item.
    LINK_FIELD = "PVTF_lADOABU7f84ALhAIzgPKqWg"

    def _make_inputs(
        self,
        data_frame: pd.DataFrame,
        project_cols: ProjectItemsQuery.ColNames,
        issue_cols: IssuesQuery.ColNames,
    ) -> list[dict]:
        inputs = []

        if data_frame.empty:
            # The loop below is not going to run, so we don't need a query to
            #  populate field_types.
            field_types = None
        else:
            project_fields = ProjectFieldsQuery()
            field_types = project_fields.data_frame[project_fields.cols.data_type]

        def value_kwarg(field_id_: str, value) -> dict:
            """
            Use the data types in the GH schema to cast each value correctly.
            """
            if field_types is not None:
                field_type_ = field_types.loc[field_id_]
                if field_type_ is github_schema.ProjectV2FieldValue.date:
                    value = datetime_str_to_date_str(value)
                return {field_type_.name: field_type_.type(value)}
            else:
                message = (
                    "Problem with updating project item fields: "
                    "cannot access information on field data types."
                )
                raise ValueError(message)

        for _, row in data_frame.iterrows():
            kwargs = (
                self._inputs_default
                |
                dict(item_id=row[project_cols.id_in_project])
            )

            # Do the special link field first.
            link_kwargs = dict(
                field_id=self.LINK_FIELD,
                value=value_kwarg(self.LINK_FIELD, row.name),
            )
            inputs.append((kwargs | link_kwargs))

            # Now do the rest of the fields.
            for field_id, col_name in issue_cols.project_field_map.items():
                extra_kwargs = dict(field_id=field_id)
                if col_name in row.index:
                    if not pd.isnull(row[col_name]):
                        # Create a `value` input argument if there is a value
                        #  available.
                        extra_kwargs["value"] = (
                            value_kwarg(field_id, row[col_name])
                        )
                    inputs.append((kwargs | extra_kwargs))

        return inputs

    def _add_selector(
        self,
        mutation: sgqlc.operation.Operation,
        index: int
    ) -> None:
        inputs = self._inputs[index]
        if "value" in inputs:
            op = mutation.update_project_v2_item_field_value
        else:
            # No value found, so clear the field instead.
            op = mutation.clear_project_v2_item_field_value

        op(input=inputs, __alias__=self._aliases[index]).client_mutation_id()


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
        prog="PelotonUpdate",
        description="Update the Peloton GitHub Project with issues and discussions",
    )
    parser.add_argument(
        "--bearer_token",
        help=(
            "GitHub personal access token with these scopes: project, repo, "
            "read:org, read:discussion ."
        ),
        type=str
    )
    parser.add_argument(
        "--update_loop_minutes",
        help=(
            "Number of minutes that the script will loop for, updating any "
            "issues/discussions that have changed since the last loop. "
            "Intended for use during meetings - for live updating."
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

    update_loop_finish_time = datetime.now() + timedelta(minutes=update_loop_minutes)
    last_update_loop_time = None
    updates_only = False

    peloton_team = PelotonTeamQuery()
    peloton_logins = peloton_team.data_frame[peloton_team.cols.login].tolist()
    logging.debug("Peloton team logins: " + ", ".join(peloton_logins))

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
        issues = IssuesQuery(query_string, peloton_logins)
        discussions = DiscussionsQuery(query_string, peloton_logins)
        logging.debug(
            f"    Query returned {len(issues.data_frame)} issues and "
            f"{len(discussions.data_frame)} discussions."
        )

        issues_discussions = pd.concat(
            [issues.data_frame, discussions.data_frame]
        )

        logging.info("    Data fetch complete.")

        if not updates_only:
            # Removes all remaining project items that do not correspond with issues
            #  or discussions returned in the query. E.g. an issue closed so long ago
            #  that today's query no longer includes it.

            # This is only run once, during the initial loop that gets everything
            #  we want to be in the project. Subsequent loops being limited to
            #  recent updates would mark almost every project item for removal.

            no_linked_id = project.data_frame[project.cols.linked_id].isnull()
            orphaned_linked_ids = ~project.data_frame[project.cols.linked_id].isin(
                issues_discussions.index
            )
            items_to_remove = project.data_frame[no_linked_id | orphaned_linked_ids]
            log_data_frame_items(items_to_remove, "    Removing from project")
            RemoveItemsMutation(items_to_remove, project.cols, issues.cols)

        # Link via a custom linked_id field to allow shared logic between issues
        #  and discussions (as opposed to using GitHub Projects' native linking
        #  that is only available for issues).
        # Not passing rsuffix or lsuffix means we know our column names (`.cols`)
        #  are unique with no overlaps between DataFrames - we can keep using them.
        # We reset_index() for this since we want to have the id_in_project in our
        #  resulting DataFrame.
        joined = project.data_frame.reset_index().join(
            issues_discussions,
            on=project.cols.linked_id,
            how="right",
        ).set_index(project.cols.linked_id)

        # Indicates that no associated project item was found during Pandas joining.
        not_in_project = joined[project.cols.id_in_project].isnull()

        have_new_comments = ~not_in_project & (
            # Check two conditions to account for possibly deleted comments.
            (
                joined[issues.cols.total_comments] !=
                joined[project.cols.num_comments]
            )
            |
            (
                # Forced to do date comparison (not datetime) because that is the
                #  max precision of project.cols.final_comment_time .
                datetime_str_to_date_str(joined[issues.cols.final_comment_time])
                !=
                joined[project.cols.final_comment_time]
            )
        )
        comments_to_clear = joined[have_new_comments]
        log_data_frame_items(
            comments_to_clear,
            "    Clearing next-peloton-date",
            issues.cols.url
        )
        ClearPelotonDateMutation(comments_to_clear, project.cols, issues.cols)

        issues_to_add = joined[not_in_project & ~joined[issues.cols.use_draft]]
        log_data_frame_items(
            issues_to_add,
            "    Adding issues to project",
            issues.cols.url
        )
        joined.loc[issues_to_add.index, project.cols.id_in_project] = (
            AddIssuesMutation(issues_to_add, project.cols, issues.cols).result
        )

        drafts_to_add = joined[not_in_project & joined[issues.cols.use_draft]]
        log_data_frame_items(
            drafts_to_add,
            "    Adding discussions to project",
            issues.cols.url
        )
        joined.loc[drafts_to_add.index, project.cols.id_in_project] = (
            AddDraftsMutation(drafts_to_add, project.cols, issues.cols).result
        )

        if updates_only:
            items_to_update = joined
        else:
            updated_since_last = (
                # Forced to do date comparison (not datetime) because that is the
                #  max precision of project.cols.date_updated .
                datetime_str_to_date_str(joined[issues.cols.updated_at]) !=
                joined[project.cols.date_updated]
            )
            items_to_update = (
                joined[updated_since_last | have_new_comments | not_in_project]
            )

        log_data_frame_items(
            items_to_update,
            "    Updating project fields",
            issues.cols.url
        )
        UpdateItemsMutation(items_to_update, project.cols, issues.cols)

        if not updates_only:
            logging.info(
                "Full refresh complete. Incremental updates will loop until "
                f"{update_loop_finish_time.strftime('%H:%M:%S')} , "
                f"with {SECONDS_BETWEEN_UPDATES} second gaps."
            )
        else:
            logging.info("Incremental update loop complete.")
        # Subsequent loops (if any) will be limited to issues/discussions
        #  updated since the last loop.
        updates_only = True
        sleep(SECONDS_BETWEEN_UPDATES)


if __name__ == "__main__":
    main()
