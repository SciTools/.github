# Copyright REPONAME contributors
#
# This file is part of REPONAME and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""REPONAME-specific adaptation of :mod:`asv_delegated`."""

from pathlib import Path
import sys

from asv_delegated import Delegated


class DelegatedRepoName(Delegated):
    """Specialism of :class:`Delegated` for benchmarking REPONAME."""

    tool_name = "delegated-REPONAME"

    def _prep_env_override(self, env_parent_dir: Path) -> Path:
        """REPONAME-specific environment preparation.

        See the Iris repo for a working example of this override in action.

        Parameters
        ----------
        env_parent_dir : Path
            The directory that the prepared environment should be placed in.

        Returns
        -------
        Path
            The path to the prepared environment.
        """
        # MINIMAL EXAMPLE:
        example = env_parent_dir / "environment"
        executable = Path(sys.executable).resolve()
        assert executable.parent.name == "bin"
        example.symlink_to(executable.parents[1], target_is_directory=True)
        return example
