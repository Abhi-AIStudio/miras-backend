#!/usr/bin/env python3
"""
Simple CLI for querying Contextual AI - no extra features, just query and response.
Usage: python simple_cli.py
"""

import asyncio
import httpx
import json
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

from config import settings

console = Console()

class SimpleContextualCLI:
    """Simple client for Contextual AI queries."""
    
    def __init__(self):
        """Initialize with API credentials."""
        self.api_key = settings.CONTEXTUAL_API_KEY
        self.agent_id = settings.CONTEXTUAL_AGENT_ID
        self.base_url = settings.CONTEXTUAL_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.conversation_id = None
    
    async def query(self, text: str) -> str:
        """
        Send query to Contextual and get response.
        Simple, no streaming, just request/response.
        """
        url = f"{self.base_url}/agents/{self.agent_id}/query"
        
        # Simple payload - just the message
        payload = {
            "messages": [{"role": "user", "content": text}],
            "stream": False
        }
        
        # Include conversation ID if we have one
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Save conversation ID for context
                if "conversation_id" in data:
                    self.conversation_id = data["conversation_id"]
                
                # Extract and return the response
                if "message" in data and "content" in data["message"]:
                    return data["message"]["content"]
                else:
                    return "No response content"
                    
        except httpx.HTTPStatusError as e:
            return f"API Error: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error: {str(e)}"

async def main():
    """Main loop - just query and display response."""
    console.print(Panel.fit(
        "[bold cyan]Simple Contextual Query CLI[/bold cyan]\n"
        "Type 'exit' to quit, 'reset' for new conversation",
        border_style="cyan"
    ))
    
    cli = SimpleContextualCLI()
    
    while True:
        # Get query
        query = Prompt.ask("\n[bold cyan]Query[/bold cyan]")
        
        if query.lower() == 'exit':
            console.print("[yellow]Goodbye![/yellow]")
            break
        
        if query.lower() == 'reset':
            cli.conversation_id = None
            console.print("[yellow]Conversation reset[/yellow]")
            continue
        
        # Send query and get response
        console.print("\n[dim]Querying...[/dim]")
        response = await cli.query(query)
        
        # Display response
        console.print("\n[bold green]Response:[/bold green]")
        console.print(Markdown(response))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")