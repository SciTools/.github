# Accessibility Statement for the SciTools GitHub Organisation

This accessibility statement applies to the content hosted on the repositories
of the **SciTools** GitHub organisation.

The **SciTools** GitHub organisation is run by the 'AVD' team ('Analysis and
Visualisation of Data') at the UK [Met Office](https://www.metoffice.gov.uk/).

**SciTools** development presents particularly exciting opportunities around
inclusivity. Climate science affects all of us, and people from all walks of
life should be able to engage with it. Working with a popular language - 
Python - and hosting on a widely-used platform - GitHub - opens us to an 
enormous population of potential users and collaborators, and our open-source
model means anyone can contribute regardless of their skill-set or available
resources. We are committed to making our content as accessible as possible, to
maximise these opportunities.

By hosting on GitHub, we benefit from their own excellent accessibility efforts:

- [GitHub accessibility settings](https://docs.github.com/en/get-started/accessibility)
- [GitHub accessibility statement](https://accessibility.github.com/)
- [Accessibility Conformance Report for GitHub.com](https://accessibility.github.com/conformance/github-com/)

For the content that we host on GitHub, we want to ensure as many people as
possible can understand it, by maximising clarity of metadata, directory 
structure, text structure, and language. In all of these areas we align to
existing conventions as much as possible, to maximise familiarity.

Across the **SciTools** repositories, you should be able to:

- Benefit from 
[GitHub's built-in accessibility features](https://docs.github.com/en/get-started/accessibility)
when navigating and viewing our content.
- Navigate the structure of our text using just a keyboard (e.g. using headings).
- Listen to our text using a screen reader.
- Understand our text, which is written in plain English with
explanations or links for any technical terms.
- Follow our source code, which uses descriptive variable names, comments,
docstrings, adopts a 'self-describing' structure where possible, and adheres to
existing style conventions ('linting').
- Learn about our repositories via standard GitHub 'community health files' such
as `README.md`, `LICENSE`, `CITATION.cff`.
- Know where to find standard files and directories through their conventional
names and paths; e.g. documentation, source code, `pyproject.toml`.
- Navigate our issues, pull requests, discussions; via their descriptive titles
and labels, including standard GitHub labels such as `good first issue`.

## How accessible this content is

While we are spinning up our accessibility testing, caution is needed when
using screen readers on repository `README` files. Two specific issues are
expected and are as-yet untested:

1. Emojis used as punctuation in headings and lists.
2. Repository health communicated via SVG 'badges', which are images of text.

The meaning of the `README` files is still expected to be clear, as the main
text bodies are free from the above issues.

## Feedback and contact information

[//]: # (TODO: in future, is there any way we can provide a public-facing phone number?)

If you find any problems not listed on this page or think we’re not meeting 
accessibility requirements, contact the **SciTools** development team, who are
responsible for both communication and actioning on accessibility issues.

If you need any information from the **SciTools** GitHub organisation in a 
different format like accessible PDF, large print, easy read, audio recording or
braille, the correct point of contact is also the **SciTools** development team.
However, it is important to note that **SciTools** activity is conducted 
primarily via GitHub, so continued collaboration/communication with **SciTools**
will be challenging if the native GitHub format is inaccessible to you.

Available contact methods:

- Preferred method:
[raise a GitHub issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/about-issues)
against the appropriate **SciTools** repository, or against
[`SciTools/.github`](https://github.com/SciTools/.github) for generic matters.
**Please attach the `Accessibility` Type to the issue.**
- Email: scitools.pub@gmail.com

The **SciTools** development team review all communications weekly (part of the
[SciTools Peloton meetings](https://github.com/orgs/SciTools/projects/13?pane=info)),
at which point we will respond to discuss possible actions with you.

[w3.org have shared some tips on contacting organisations about accessibility](http://www.w3.org/WAI/users/inaccessible).

## Enforcement procedure

The Equality and Human Rights Commission (EHRC) is responsible for enforcing the
Public Sector Bodies (Websites and Mobile Applications) (No. 2) Accessibility 
Regulations 2018 (the ‘accessibility regulations’). If you’re not happy with how
we respond to your complaint, 
[contact the Equality Advisory and Support Service (EASS)](https://www.equalityadvisoryservice.com/).

## Technical information about this content's accessibility

The Met Office is committed to making its content accessible, in accordance with
the Public Sector Bodies (Websites and Mobile Applications) (No. 2) Accessibility
Regulations 2018.

### Compliance status

This GitHub organisation is partially compliant with the
[Web Content Accessibility Guidelines version 2.2](https://www.w3.org/TR/WCAG22/)
AA standard, due to the non-compliances and exemptions listed below.

## Non-accessible content

The content listed below is non-accessible for the following reasons.

### Non-compliance with the accessibility regulations

- Emojis are used as punctuation in headings and lists within many `README`
files. Emojis can disrupt flow when using a screen reader, and they should
typically be limited to the _end_ of a sentence or paragraph - see
[WCAG 1.1.1 Non-text Content](https://www.w3.org/TR/WCAG22/#non-text-content).
The text remains understandable if you are aware of this potential disruption.
We will be improving our understanding of correct emoji usage during our
manual testing routine
([SciTools/.github#213](https://github.com/SciTools/.github/issues/213)).
- SVG 'badges' are used within many `README` files to communicate repository
health/status. These are images of text, which would be more accessible as
plain text. See
[WCAG 1.4.5 Images of Text](https://www.w3.org/TR/WCAG22/#images-of-text).
It is not necessary to understand this section of the `README` files to
understand the overall meaning. We will be reviewing what can be done to
maximise accessibility in this space, since in some cases badges are the only
viable option; see 
[SciTools/.github#216](https://github.com/SciTools/.github/issues/216).

#### Unassessed content

We are at an early stage of assessing the accessibility of the content hosted 
across the **SciTools** GitHub organisation, and therefore do not yet have a 
full account of non-accessible content. Actions we are taking to address this 
include:

- Creation of the [`Accessibility`](https://github.com/search?q=org%3ASciTools+type%3AAccessibility&type=issues)
issue Type across **SciTools** repositories, to raise the profile of
accessibility work and to aid in tracking outstanding issues.
- Implementing automated accessibility testing in the continuous integration (CI)
of **SciTools** repositories; see 
[SciTools/.github#214](https://github.com/SciTools/.github/issues/214)
- Planning a manual accessibility testing routine for **SciTools** 
repositories; see 
[SciTools/.github#213](https://github.com/SciTools/.github/issues/213)

In the meantime, we welcome reports of any accessibility issues you encounter
while using the **SciTools** GitHub organisation; see the
[Feedback and contact information](#feedback-and-contact-information)
section for details.

### Content that is not within the scope of the accessibility regulations

#### Third-party platform limitations

This content is hosted on GitHub, a third-party platform. As such, we do not
control accessibility of GitHub's interface elements, such as its colours, 
navigation, type-facing. These aspects are managed by GitHub and fall outside
the scope of our accessibility responsibilities. For more information about
GitHub accessibility, see 
[GitHub's accessibility pages](https://accessibility.github.com/), including
GitHub's published 
[accessibility conformance reports](https://accessibility.github.com/conformance/github-com/).

#### Third-party content

The **SciTools** GitHub organisation includes third party content which we have
no control over - comments left on issues, pull requests, discussions by members
of the public. The accessibility regulations do not require us to manage these
kinds of content, but if you have a problem with any of the content hosted on
this GitHub organisation, please contact us using the methods above and we will
try to help.

#### Archive content

Some of the content in issues, pull requests, discussions across the
**SciTools** GitHub organisation is classified as archive content. Specifically:
these are made up of conversational posts which are inappropriate to edit or
remove. This kind of historically recorded content is exempt from meeting the 
digital accessibility regulations. If you require a specific piece of archive 
conversation and it is not accessible, please contact us using the methods above
and we will provide an accessible version of the content on request.

We will always consider accessibility at the time of making new posts on
issues, pull requests, discussions.

#### Source code

Source code is not typical text and does not support typical accessibility
features such as semantic markup or keyboard navigation. The accessibility
regulations do not require us to make source code accessible. However, we are
keen to make our source code as clear and understandable as possible, within the
constraints of programming languages and their conventions. If you have any
problems or suggestions regarding the accessibility of our source code, please
contact us using the methods above.

## Preparation of this accessibility statement

This statement was prepared on 17th October 2025. It was last reviewed on 17th 
October 2025.

The **SciTools** GitHub organisation was last tested on 11th September 2024. The
test was carried out by the 'AVD' team ('Analysis and Visualisation of Data') 
at the UK Met Office. The test included
parsing the **SciTools** organisational `README` file using the
[NVDA screen reader](https://www.nvaccess.org/) on Windows 11, and the
`Read aloud` function in Microsoft Edge on Windows 11.

A more thorough range of testing - manual AND automated - is planned for the 
future; see the [Non-assessed content](#unassessed-content) section for details.
