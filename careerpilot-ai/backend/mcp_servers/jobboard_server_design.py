"""
MCP Server: Job Board Server (design stub)

This module documents the intended MCP server that would expose job-search
capabilities as MCP tools, callable by any MCP-compatible client/agent.

In production this would be a standalone process implementing the MCP
server protocol (stdio or SSE transport) using the `mcp` Python SDK:

    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    server = Server("careerpilot-jobboard")

    @server.tool()
    async def search_jobs(query: str, location: str = "", source: str = "linkedin") -> list[dict]:
        '''Search jobs across configured job boards.'''
        ...

    @server.tool()
    async def get_company_info(company_name: str) -> dict:
        '''Fetch company size, glassdoor rating, tech stack, culture notes.'''
        ...

    if __name__ == "__main__":
        stdio_server(server)

Tools exposed by this server:
  - search_jobs(query, location, source) -> list[Job]
  - get_company_info(company_name) -> dict
  - get_job_details(job_url) -> dict

CareerPilot's LangGraph agents would connect to this server via an MCP
client and invoke these tools as part of the Job Scout Agent's toolset.

For local development without a running MCP server, agents call the
equivalent functions directly from `backend.mcp_servers.client_helpers`,
which mirror these exact signatures - making the swap to real MCP a
drop-in change.
"""
