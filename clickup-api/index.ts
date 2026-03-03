import type { AnyAgentTool, OpenClawPluginApi } from "../../src/plugins/types.js";
import { createClickUpApiTool } from "./src/clickup-api-tool.js";

export default function register(api: OpenClawPluginApi) {
  const tool = createClickUpApiTool(api);
  if (tool) {
    api.registerTool(tool as unknown as AnyAgentTool);
  }
}
