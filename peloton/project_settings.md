The settings of the Peloton GitHub Project are not under source control, so are
recorded here in case they get corrupted/lost.

📅 Last updated: `2023-12-08`

# Short description

Using team spirit to keep our open source projects at race-fitness!

# README

Cycling pelotons work together to achieve things no rider can do alone. They share workload, support each other, and prioritise when/where to spend their energy. All this while constantly moving forward. Let's channel that spirit to keep our open source projects at race-fitness!

Each of the Views here are focussed on something key to project health. They include various ideas for issues/PR's to focus on. 

- 🔁 set the board to repeatedly update for the duration of your meeting using the [**workflow dispatch action**](https://github.com/SciTools/.github/actions/workflows/peloton.yml).
- 👁 read the notes at the top of each View to understand what they are for.
- 🔀 try sorting a View by the various columns provided.
- 📅 use the `🚴 Next Peloton Date` field to hide an item until a future date.

The pages and views shown here are very much open to improvement; visit [SciTools/.github](https://github.com/SciTools/.github) to discuss improvements and edit the queries.

![Image](https://user-images.githubusercontent.com/40734014/216654352-164fb911-b594-475c-a962-9780f42e9c0f.png)

# Views

## 0️⃣ Meeting Admin ❗

- Filter: `note:"Find a volunteer to run next week, and have them book a room right now!"`
- Should contain no items.

## 1️⃣ Recent Changes 📢

- Filter: none
- Grouped by: `Date Updated`
- Sorted by: `Date Updated` descending
- Sliced by: `Author Membership`
- Remember to select/hide the most appropriate columns for this view

## 2️⃣ Community ❤

- Filter: `no:date-closed commenter-membership:"External commenter" -🚴-next-peloton-date:>@today -note:"This view prioritises responding to comments from external collaborators - see SciTools/.github/peloton for the user list"`
- Sorted by: `Final Comment Time` descending
- Remember to select/hide the most appropriate columns for this view

## 3️⃣ Progress report 📈

- Filter: `no:date-closed -no:assignee -note:"This view is for reviewing the progress of assigned items. It's OK to unassign!"`
- Sliced by: `Assignees`
- Remember to select/hide the most appropriate columns for this view

## 4️⃣ Unassigned 📭

- Filter: `no:date-closed no:assignee no:milestone -is:draft -🚴-next-peloton-date:>@today -note:"This view is for assigning items for progression/review this week. Grouped to show non-peloton authors first"`
- Sorted by: `Date Updated` descending
- Sliced by: `Author Membership`
- Remember to select/hide the most appropriate columns for this view

## 💬 Discussion

- Filter: `no:date-closed discussion-wanted?:True -🚴-next-peloton-date:>@today -note:"This view lists all Discussions, and issues/PR's with specific discussion labels - see SciTools/.github/peloton for details"`
- Sorted by: `Date Updated` descending
- Remember to select/hide the most appropriate columns for this view

## 📅 For release?

- Filter: `no:date-closed -no:milestone -note:"This view uses milestones to prompt discussion about upcoming releases"`
- Grouped by `Milestone`
- Sorted by: `Date Created` ascending
- Sliced by: `Repository`
- Remember to select/hide the most appropriate columns for this view

## _everything

- Filter: none (obviously)