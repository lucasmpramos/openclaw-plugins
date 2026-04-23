import type { OpenClawPluginApi } from "../../../src/plugins/types.js";

interface ButleyApiConfig {
  convexUrl: string;
  installationId: string;
  gatewayToken: string;
}

const ACTIONS: Record<
  string,
  { method: "query" | "mutation"; path: string; requiredArgs?: string[] }
> = {
  // Tasks
  listTasks: { method: "query", path: "agentApi:listTasks" },
  getTask: { method: "query", path: "agentApi:getTask", requiredArgs: ["taskId"] },
  createTask: { method: "mutation", path: "agentApi:createTask", requiredArgs: ["title"] },
  updateTask: { method: "mutation", path: "agentApi:updateTask", requiredArgs: ["taskId"] },
  patchTaskBody: {
    method: "mutation",
    path: "agentApi:patchTaskBody",
    requiredArgs: ["taskId", "ops"],
  },
  deleteTask: { method: "mutation", path: "agentApi:deleteTask", requiredArgs: ["taskId"] },
  // Projects
  listProjects: { method: "query", path: "agentApi:listProjects" },
  createProject: { method: "mutation", path: "agentApi:createProject", requiredArgs: ["name"] },
  updateProject: {
    method: "mutation",
    path: "agentApi:updateProject",
    requiredArgs: ["projectId"],
  },
  deleteProject: {
    method: "mutation",
    path: "agentApi:deleteProject",
    requiredArgs: ["projectId"],
  },
  // Task Comments
  listTaskComments: {
    method: "query",
    path: "agentApi:listTaskComments",
    requiredArgs: ["taskId"],
  },
  addTaskComment: {
    method: "mutation",
    path: "agentApi:addTaskComment",
    requiredArgs: ["taskId", "body"],
  },
  deleteTaskComment: {
    method: "mutation",
    path: "agentApi:deleteTaskComment",
    requiredArgs: ["commentId"],
  },
  // Documents
  listDocs: { method: "query", path: "agentApi:listDocs" },
  getDoc: { method: "query", path: "agentApi:getDoc", requiredArgs: ["docId"] },
  createDoc: { method: "mutation", path: "agentApi:createDoc", requiredArgs: ["title"] },
  updateDoc: { method: "mutation", path: "agentApi:updateDoc", requiredArgs: ["docId"] },
  deleteDoc: { method: "mutation", path: "agentApi:deleteDoc", requiredArgs: ["docId"] },
  shareDoc: { method: "mutation", path: "agentApi:shareDoc", requiredArgs: ["docId"] },
  unshareDoc: { method: "mutation", path: "agentApi:unshareDoc", requiredArgs: ["docId"] },
  // Contacts
  listContacts: { method: "query", path: "agentApi:listContacts" },
  findOrCreateContact: {
    method: "mutation",
    path: "agentApi:findOrCreateContact",
    requiredArgs: ["phone"],
  },
  getContactByPhone: {
    method: "query",
    path: "agentApi:getContactByPhone",
    requiredArgs: ["phone"],
  },
};

export function createButleyApiTool(api: OpenClawPluginApi) {
  const config = (api.pluginConfig ?? {}) as ButleyApiConfig;

  if (!config.convexUrl || !config.installationId || !config.gatewayToken) {
    api.logger?.warn?.(
      "butley-api: missing config (convexUrl, installationId, or gatewayToken). Tool disabled.",
    );
    return null;
  }

  const actionNames = Object.keys(ACTIONS).join(", ");

  return {
    name: "butley_api",
    description: `Access workspace data in Convex Cloud. Actions: ${actionNames}.

Use this tool to manage tasks, projects, comments, and contacts. Data persists across sessions and is visible in the Butley dashboard.

## Tasks
- listTasks: optional filters: status (backlog|todo|doing|done|blocked), projectId, limit
- getTask: taskId (required)
- createTask: title (required), description, body (markdown content), status, priority (low|medium|high|urgent), owner, dueDate (timestamp ms), tags (string[]), notes, category, projectId, position
- updateTask: taskId (required), + any fields above to update
- patchTaskBody: taskId (required), ops (required) — surgical edits to body without sending full text. ops is array of {type, find?, replace?, content?, after?}. Types: "replace" (find→replace, all occurrences), "append" (add to end), "prepend" (add to start), "insert_after" (insert after marker). Use instead of updateTask when body is long. ⚠️ Keep find/after fields SHORT (headings, not content) — long strings in ops also truncate.
- deleteTask: taskId (required)

## Projects
- listProjects: no args
- createProject: name (required), description, status (active|paused|completed|archived), color (hex)
- updateProject: projectId (required), + name, description, status, color
- deleteProject: projectId (required)

## Task Comments
- listTaskComments: taskId (required) — returns comments on a task
- addTaskComment: taskId (required), body (required), author (optional, defaults to "Bob")
- deleteTaskComment: commentId (required)

## Documents
- listDocs: optional filters: projectId, limit
- getDoc: docId (required)
- createDoc: title (required), markdown, projectId, tags, owner
- updateDoc: docId (required), + title, markdown, tags, archived, pinned
- deleteDoc: docId (required)
- shareDoc: docId (required) — makes doc public, returns { slug, url }
- unshareDoc: docId (required) — revokes public access

## Contacts
- listContacts: no args
- findOrCreateContact: phone (required), name, nickname, email, notes, tags
- getContactByPhone: phone (required)`,
    parameters: {
      type: "object" as const,
      properties: {
        action: {
          type: "string" as const,
          enum: Object.keys(ACTIONS),
          description: "The API action to perform",
        },
        args: {
          type: "object" as const,
          description: "Action-specific arguments (do NOT include installationId or gatewayToken)",
          additionalProperties: true,
        },
      },
      required: ["action"] as const,
    },
    async execute(_toolUseId: string, params: { action: string; args?: Record<string, unknown> }) {
      const { action, args: userArgs = {} } = params;

      const actionDef = ACTIONS[action];
      if (!actionDef) {
        return {
          content: [
            { type: "text", text: `Error: Unknown action '${action}'. Available: ${actionNames}` },
          ],
        };
      }

      if (actionDef.requiredArgs) {
        for (const req of actionDef.requiredArgs) {
          if (!(req in userArgs)) {
            return {
              content: [
                {
                  type: "text",
                  text: `Error: Missing required arg '${req}' for action '${action}'`,
                },
              ],
            };
          }
        }
      }

      const endpoint = `${config.convexUrl}/api/${actionDef.method}`;
      const body = {
        path: actionDef.path,
        args: {
          installationId: config.installationId,
          gatewayToken: config.gatewayToken,
          ...userArgs,
        },
        format: "json",
      };

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        const data = await res.json();

        if (data.status === "error") {
          return {
            content: [{ type: "text", text: `Convex error: ${data.errorMessage || "unknown"}` }],
          };
        }

        return { content: [{ type: "text", text: JSON.stringify(data.value, null, 2) }] };
      } catch (err) {
        return {
          content: [
            {
              type: "text",
              text: `Request failed: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
        };
      }
    },
  };
}
