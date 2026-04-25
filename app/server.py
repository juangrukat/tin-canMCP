from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.tools import register_tools
from app.prompts import register_prompts


mcp = FastMCP(settings.server_name)

register_tools(mcp)
register_prompts(mcp)
