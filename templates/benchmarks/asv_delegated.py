# Copyright SciTools contributors
#
# This file is part of SciTools and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""Repository-specific adaptation of :mod:`_asv_delegated_abc`."""

from pathlib import Path
import sys

from _asv_delegated_abc import _DelegatedABC


class Delegated(_DelegatedABC):
    """Specialism of :class:`_DelegatedABC` for benchmarking this repo."""

    tool_name = "delegated"

    def _prep_env_override(self, env_parent_dir: Path) -> Path:
        """Environment preparation specialised for this repo.

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
