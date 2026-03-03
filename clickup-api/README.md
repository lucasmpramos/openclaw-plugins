# clickup-api-plugin

OpenClaw plugin for ClickUp API v2. Adds a `clickup_api` tool to your agent.

## Features

- Config-driven — no hardcoded values, works on any OpenClaw instance
- Formatted output — clean summaries, not raw JSON (minimal context burn)
- 16 actions: workspace, spaces, folders, lists, tasks (CRUD), comments, members, time tracking

## Installation

Clone or copy the plugin into your OpenClaw `extensions/` directory:

```bash
git clone https://github.com/butley/clickup-api-plugin.git extensions/clickup-api
```

Then add to `openclaw.json`:

```json
"plugins": {
  "entries": {
    "clickup-api": {
      "config": {
        "apiKey": "pk_...",
        "teamId": "YOUR_TEAM_ID",
        "defaultLimit": 20
      }
    }
  }
}
```

Rebuild and restart:

```bash
npm run build && openclaw gateway restart
```

## Config

| Key | Required | Description |
|-----|----------|-------------|
| `apiKey` | ✅ | ClickUp personal API token (`pk_...`). Settings → Apps → API Token |
| `teamId` | ✅ | ClickUp workspace/team ID. From URL: `app.clickup.com/{team_id}/home` |
| `defaultLimit` | — | Max tasks returned in list/search calls (default: 20) |

## Actions

| Action | Description |
|--------|-------------|
| `getWorkspace` | List spaces in the workspace |
| `getSpaces` | List all spaces |
| `getFolders` | List folders in a space (`spaceId`) |
| `getLists` | List task lists in a folder (`folderId`) |
| `getSpaceLists` | List folderless lists in a space (`spaceId`) |
| `getTasks` | Get tasks from a list (`listId`, optional: `limit`, `page`, `statuses`, `assignees`) |
| `searchTasks` | Search tasks across workspace (`query`) |
| `getTask` | Full task details (`taskId`, optional: `includeComments`) |
| `createTask` | Create a task (`listId`, `name`, optional: `description`, `status`, `priority`, `due_date`, `assignees`) |
| `updateTask` | Update a task (`taskId` + any fields) |
| `addComment` | Add comment to a task (`taskId`, `comment_text`) |
| `getComments` | Get task comments (`taskId`) |
| `getMembers` | Get list members (`listId`) |
| `getTimeEntries` | Get time entries (optional: `start_date`, `end_date`, `assignee`) |
| `createTimeEntry` | Log time (`task_id`, `duration` in ms, `start` timestamp ms) |
