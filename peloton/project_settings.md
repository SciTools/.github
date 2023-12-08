The settings of the Peloton GitHub Project are not under source control, so are
recorded here in case they get corrupted/lost.

📅 Last updated: `2023-12-08`

# Short description

Using team spirit to keep our open source projects at race-fitness!

# README

Cycling pelotons work together to achieve things no rider can do alone. They share workload, support each other, and prioritise when/where to spend their energy. All this while constantly moving forward. Let's channel that spirit to keep our open source projects at race-fitness!

Each of the Views here are focussed on something key to project health. They include various ideas for issues/PR's to focus on. 

- 👁 read the notes at the top of each View to understand what they are for.
- 🔀 try sorting a View by the various columns provided.
- 📅 use the `🚴 Next Peloton Date` field to hide an item until a future date

The pages and views shown here are very much open to improvement; visit [SciTools/.github](https://github.com/SciTools/.github) to discuss improvements and edit the queries.

![Image](https://user-images.githubusercontent.com/40734014/216654352-164fb911-b594-475c-a962-9780f42e9c0f.png)

# Views

## 🎉 Celebrate!/Commiserate!

`-no:date-closed -note:"This view shows recently closed items, so we can celebrate success and generally be aware."`

## ❤ Community

`no:date-closed commenter-membership:"External commenter" -🚴-next-peloton-date:>@today -note:"This view prioritises responding to comments from external collaborators - see SciTools/.github/peloton for the user list"`

## ✋ To be assigned

`no:date-closed no:assignee no:milestone -🚴-next-peloton-date:>@today -note:"This view is for assigning items for progression/review this week. Grouped to show non-peloton authors first"`

## 💬 Discussion

`no:date-closed discussion-wanted?:True -🚴-next-peloton-date:>@today -note:"This view lists all Discussions, and issues/PR's with specific discussion labels - see SciTools/.github/peloton for details"`

## 📈 Progress report

`no:date-closed -no:assignee -note:"This view is for reviewing the progress of assigned items. It's OK to unassign!"`

## 📅 For release?

`no:date-closed -no:milestone -note:"This view uses milestones to prompt discussion about upcoming releases"`

## _everything

` `