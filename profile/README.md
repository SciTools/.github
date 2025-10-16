**Links:**&nbsp;&nbsp; [Privacy Policy](privacy_policy.md)
&nbsp;,&nbsp;
[Accessibility Statement](../ACCESSIBILITY.md)

# SciTools

## Open tools for the analysis and visualisation of Earth science data

SciTools is a collaborative effort to produce powerful Python-based open-source tools for Earth scientists. Initially started at the UK [Met Office](https://www.metoffice.gov.uk/) in 2010, SciTools has grown into a diverse community of partners and collaborators from around the world. SciTools is responsible for the maintenance of a number of key packages such as Iris and Cartopy, and continues to develop new and innovative tools for the Earth scientist's toolkit.

## Contents

- [List of SciTools packages](#packages-package)
- [More about SciTools](#more-about-scitools-information_source)

## Packages :package:

### Cartopy

<img src="https://raw.githubusercontent.com/SciTools/cartopy/main/docs/source/_static/cartopy.png" height="100" alt="cartopy logo">

Cartopy is a Python package designed for geospatial data processing in order to produce maps and other geospatial data analyses.

Key features of cartopy are its object oriented projection definitions, and its ability to transform points, lines, vectors, polygons and images between those projections.

You will find Cartopy especially useful for large area / small scale data, where Cartesian assumptions of spherical data traditionally break down.

**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools/cartopy)
&nbsp;,&nbsp;
[Documentation](https://cartopy.readthedocs.io/stable/)
&nbsp;,&nbsp;
[Gallery](https://cartopy.readthedocs.io/stable/gallery/index.html)

### Iris

<img src="https://raw.githubusercontent.com/SciTools/iris/main/docs/src/_static/iris-logo.svg" height="100" alt="iris logo">

The Iris package implements a data model to create a data abstraction layer which isolates analysis and visualisation code from data format specifics. The data model we have chosen is the [CF (Climate & Forecast) Data Model](https://cfconventions.org/). The implementation of this model we have called an Iris Cube.

Iris currently supports read/write access to a range of data formats, including (CF-)[NetCDF](https://github.com/Unidata/netcdf-c), [GRIB](https://confluence.ecmwf.int/display/CKB/What+are+GRIB+files+and+how+can+I+read+them), and [PP](https://artefacts.ceda.ac.uk/badc_datadocs/um/umdp_F3-UMDPF3.pdf); fundamental data manipulation operations, such as arithmetic, interpolation, and statistics; and a range of integrated plotting options.

**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools/iris)
&nbsp;,&nbsp;
[Documentation](https://scitools-iris.readthedocs.io/en/stable/)
&nbsp;,&nbsp;
[Gallery](https://scitools-iris.readthedocs.io/en/stable/generated/gallery/index.html)

### Other highlights

| Package | Description & Links |
| - | - |
| **iris-esmf-regrid** | A collection of structured and unstructured ESMF regridding schemes for Iris.<br>**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools-incubator/iris-esmf-regrid) &nbsp;,&nbsp; [Documentation](https://iris-esmf-regrid.readthedocs.io/en/stable/) &nbsp;,&nbsp; ([ESMF](https://earthsystemmodeling.org/)) |
| **cf-units** | Units of measure as required by the Climate and Forecast (CF) Metadata Conventions.<br>**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools/cf-units) &nbsp;,&nbsp; [Documentation](https://cf-units.readthedocs.io/en/stable/) |
| **nc-time-axis** | Provides support for a cftime axis in Matplotlib.<br>**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools/nc-time-axis) &nbsp;,&nbsp; [Documentation](https://nc-time-axis.readthedocs.io/en/stable/) &nbsp;,&nbsp; ([cftime](https://github.com/Unidata/cftime)) &nbsp;,&nbsp; ([Matplotlib](https://matplotlib.org/)) |
| **tephi** | Tephigram plotting in Python.<br>**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools/tephi) &nbsp;,&nbsp; [Documentation](http://tephi.readthedocs.org/) &nbsp;,&nbsp; ([tephigrams](https://en.wikipedia.org/wiki/Tephigram)) |
| **python-stratify** | Vectorized interpolators for Nd atmospheric and oceanographic data.<br>**Links:**&nbsp;&nbsp; [GitHub](https://github.com/SciTools/python-stratify) |

### See more

- [Pinned repositories](https://github.com/SciTools#:~:text=Pinned)
- [Full repository list](https://github.com/SciTools#org-profile-repositories)
- [SciTools-incubator](https://github.com/SciTools-incubator) organization - experimental SciTools projects
- [SciTools-classroom](https://github.com/SciTools-classroom) organization - explore the power of SciTools through our collection of dedicated learning material and presentations

## More about SciTools :information_source:

### Software Licensing :inbox_tray:

The rules/agreements for **using** the software. All SciTools software is distributed under the terms of the [**BSD-3-Clause**](https://spdx.org/licenses/BSD-3-Clause.html) licence.

### Contributor Licence Agreement (CLA) :pencil:

The rules/agreements for **contributing** to the software. Contributions to any SciTools repository are subject to the [**SciTools Contributor Licence Agreement**](https://cla-assistant.io/SciTools/).

### Development :pencil2:

The Met Office remains the driving force behind SciTools and most of our packages; however, all the packages are fundamentally developed in the open. The direction of SciTools packages is decided by the community of developers; who are always eager for more people from different areas to contribute towards Iris, Cartopy and the wider SciTools ecosystem. All types of contribution are encouraged:

<!--- The list below has slightly odd formatting around the emojis to help it behave better with screen readers (keeping the page more accessible). -->

- 1 :speech_balloon: : Participating in conversations on existing repository [discussions](https://docs.github.com/en/discussions/collaborating-with-your-community-using-discussions/about-discussions) / [issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/about-issues) / [pull requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
- 2 :bell: : Starting new repository [discussions](https://docs.github.com/en/discussions/collaborating-with-your-community-using-discussions/about-discussions) / [issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/about-issues)
- 3 :bulb: : Proposing changes via repository [pull requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
- 4 :pencil2: : Developing your own software that uses or augments SciTools software package(s)

Every SciTools repository has a team of _maintainers_ - developers with GitHub permissions to make changes to the codebase (typically via approving and merging pull requests). Maintainers do their best to respond to discussions / issues / pull requests and generally keep the repositories healthy. [Many of the SciTools repositories are discussed by maintainers at regular Peloton meetings](https://github.com/orgs/SciTools/projects/13?pane=info).

### Contact :telephone_receiver:

Please raise a [discussion](https://docs.github.com/en/discussions/collaborating-with-your-community-using-discussions/about-discussions) / [issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/about-issues) / [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) on the appropriate SciTools repository. If your contact is not linked to a specific repository then you can use the [SciTools/.github](https://github.com/SciTools/.github) repository. The conversation can also continue in private, feel free to request this. While we prefer talking on GitHub, you can also email scitools.pub@gmail.com if necessary.
