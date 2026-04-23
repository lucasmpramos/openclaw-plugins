import type { AnyAgentTool, OpenClawPluginApi } from "../../src/plugins/types.js";
import { createButleyApiTool } from "./src/butley-api-tool.js";

export default function register(api: OpenClawPluginApi) {
  const tool = createButleyApiTool(api);
  if (tool) {
    api.registerTool(tool as unknown as AnyAgentTool);
  }
}
