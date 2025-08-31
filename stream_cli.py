#!/usr/bin/env python3
"""
Simple streaming CLI for Contextual AI - streams responses as they come.
Usage: python stream_cli.py
"""

import asyncio
import httpx
import json
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table

from config import settings
from validation import GeminiValidator

console = Console()

class StreamingContextualCLI:
    """Streaming client for Contextual AI."""
    
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
    
    async def stream_query(self, text: str):
        """
        Stream query response from Contextual.
        Yields events with type and data.
        """
        url = f"{self.base_url}/agents/{self.agent_id}/query"
        
        # Add query parameter for retrieval text
        url += "?include_retrieval_content_text=true"
        
        # Payload with streaming enabled
        payload = {
            "messages": [{"role": "user", "content": text}],
            "stream": True  # Enable streaming
        }
        
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id
        
        full_response = ""
        groundedness_scores = []
        retrievals = []
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=self.headers, json=payload) as response:
                    response.raise_for_status()
                    
                    # Process server-sent events
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            
                            # Check for end of stream
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                
                                # Handle different event types
                                event_type = data.get("event", "")
                                event_data = data.get("data", {})
                                
                                # Save conversation ID from metadata
                                if event_type == "metadata" and "conversation_id" in event_data:
                                    self.conversation_id = event_data["conversation_id"]
                                
                                # Collect message deltas
                                if event_type == "message_delta" and "delta" in event_data:
                                    full_response += event_data["delta"]
                                    yield ("delta", event_data["delta"])
                                
                                # Capture groundedness scores
                                if event_type == "groundedness_scores" and "scores" in event_data:
                                    groundedness_scores = event_data["scores"]
                                    yield ("groundedness", groundedness_scores)
                                
                                # Capture retrieval contents
                                if event_type == "retrievals" and "contents" in event_data:
                                    retrievals = event_data["contents"]
                                    yield ("retrievals", retrievals)
                                        
                            except json.JSONDecodeError:
                                # Skip invalid JSON chunks
                                continue
                                
        except httpx.HTTPStatusError as e:
            yield ("error", f"API Error: {e.response.status_code}")
        except Exception as e:
            yield ("error", f"Error: {str(e)}")

async def main():
    """Main loop with streaming responses."""
    console.print(Panel.fit(
        "[bold cyan]Streaming Contextual Query CLI with Validation[/bold cyan]\n"
        "Type 'exit' to quit, 'reset' for new conversation, 'validate off' to disable validation",
        border_style="cyan"
    ))
    
    cli = StreamingContextualCLI()
    validator = GeminiValidator()
    validate_responses = True  # Validation enabled by default
    
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
        
        if query.lower() == 'validate off':
            validate_responses = False
            console.print("[yellow]Validation disabled[/yellow]")
            continue
        
        if query.lower() == 'validate on':
            validate_responses = True
            console.print("[green]Validation enabled[/green]")
            continue
        
        # Stream response with live display
        console.print("\n[bold green]Response:[/bold green]")
        full_response = ""
        retrievals = []
        
        with Live("", console=console, refresh_per_second=4) as live:
            async for event_type, data in cli.stream_query(query):
                if event_type == "delta":
                    # Accumulate response text
                    full_response += data
                    # Update display with markdown formatting
                    live.update(Markdown(full_response))
                elif event_type == "retrievals":
                    # Store retrieval sources
                    retrievals = data
        
        # Display citations/sources
        if retrievals:
            console.print("\n[bold cyan]📚 Sources/Citations:[/bold cyan]")
            for i, ret in enumerate(retrievals[:5], 1):  # Show top 5 sources
                doc_name = ret.get('doc_name', 'Unknown document')
                page = ret.get('page', 'N/A')
                score = ret.get('score', 0)
                
                # Truncate long document names
                if len(doc_name) > 50:
                    doc_name = doc_name[:47] + "..."
                
                console.print(f"  [{i}] [yellow]{doc_name}[/yellow]")
                console.print(f"      Page: {page} | Relevance: {score:.2%}")
            
            if len(retrievals) > 5:
                console.print(f"  [dim]... and {len(retrievals) - 5} more sources[/dim]")
        else:
            console.print("\n[dim]No source citations available[/dim]")
        
        # Run Gemini validation if enabled
        if validate_responses and full_response:
            console.print("\n[yellow]🔍 Validating response with Gemini...[/yellow]")
            
            # Prepare sources for validation
            sources = []
            if retrievals:
                for ret in retrievals[:3]:  # Use top 3 sources for validation
                    sources.append({
                        "doc_name": ret.get('doc_name', 'Unknown'),
                        "page": ret.get('page', 'N/A'),
                        "content": ret.get('content_text', '')[:500] if 'content_text' in ret else ''
                    })
            
            # Stream validation with thinking visible
            console.print("\n[dim italic]💭 Gemini's Thinking Process:[/dim italic]")
            thinking_text = ""
            validation_result = None
            
            with Live("", console=console, refresh_per_second=4) as live:
                for event_type, content in validator.validate_response_stream(query, full_response, sources):
                    if event_type == "thought":
                        # Stream thinking process
                        thinking_text += content
                        live.update(Markdown(thinking_text))
                    elif event_type == "answer":
                        # JSON is being streamed but we'll wait for the final result
                        pass
                    elif event_type == "result":
                        # Got the final parsed result
                        validation_result = content
                    elif event_type == "error":
                        console.print(f"\n[red]Validation error: {content}[/red]")
            
            # Display validation results if we got them
            if validation_result:
                console.print("\n[bold magenta]✅ Validation Results:[/bold magenta]")
                
                # Query answered?
                query_answered = validation_result.get('query_answered', False)
                if query_answered:
                    console.print(f"  [green]✅ Query Answered: YES[/green]")
                else:
                    console.print(f"  [red]❌ Query Answered: NO[/red]")
                
                # Fact-by-fact checking
                facts = validation_result.get('facts_checked', [])
                if facts:
                    console.print(f"\n[bold cyan]Fact Checking ({validation_result.get('verified_facts', 0)}/{validation_result.get('total_facts', 0)} verified):[/bold cyan]")
                    
                    for fact in facts:
                        fact_text = fact.get('fact', '')
                        verified = fact.get('verified', False)
                        page = fact.get('page_found', '')
                        
                        if verified:
                            icon = "✅"
                            color = "green"
                        else:
                            icon = "❌"
                            color = "red"
                        
                        # Truncate long facts for display
                        if len(fact_text) > 80:
                            fact_text = fact_text[:77] + "..."
                        
                        console.print(f"  {icon} [{color}]{fact_text}[/{color}]")
                        if page:
                            console.print(f"     [dim](Found on page {page})[/dim]")
                
                # Overall accuracy
                accuracy = validation_result.get('accuracy_score', 0)
                if accuracy >= 90:
                    accuracy_color = "green"
                elif accuracy >= 70:
                    accuracy_color = "yellow"
                else:
                    accuracy_color = "red"
                
                console.print(f"\n[bold]Overall Accuracy: [{accuracy_color}]{accuracy}%[/{accuracy_color}][/bold]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")