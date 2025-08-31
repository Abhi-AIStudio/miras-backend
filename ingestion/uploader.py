import httpx
import json
import tempfile
import os
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

from config import settings

console = Console()

class ContextualUploader:
    """Upload processed documents to Contextual AI."""
    
    def __init__(self):
        """Initialize the Contextual uploader."""
        if not settings.CONTEXTUAL_API_KEY:
            raise ValueError("CONTEXTUAL_API_KEY not found in environment variables")
        if not settings.CONTEXTUAL_DATASTORE_ID:
            raise ValueError("CONTEXTUAL_DATASTORE_ID not found in environment variables")
        
        self.api_key = settings.CONTEXTUAL_API_KEY
        self.datastore_id = settings.CONTEXTUAL_DATASTORE_ID
        self.base_url = settings.CONTEXTUAL_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def upload_document(self, 
                       content: str, 
                       metadata: Dict[str, Any],
                       wait_for_completion: bool = True) -> Dict[str, Any]:
        """
        Upload a document to Contextual AI datastore.
        
        Args:
            content: The extracted document content
            metadata: Document metadata
            wait_for_completion: Whether to wait for ingestion to complete
            
        Returns:
            Response from Contextual API
        """
        console.print(f"\n[bold cyan]Uploading to Contextual AI[/bold cyan]")
        console.print(f"[dim]Datastore ID: {self.datastore_id}[/dim]")
        
        # Create a temporary HTML file with the content and metadata
        # Using HTML format as it's supported and preserves formatting better
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{metadata.get("title", "Untitled Document")}</title>
    <meta name="author" content="{metadata.get("Author/Organization", "")}">
    <meta name="date" content="{metadata.get("Date", "")}">
    <meta name="description" content="{metadata.get("Summary", "")}">
</head>
<body>
    <h1>{metadata.get("title", "Untitled Document")}</h1>
    <pre>{content}</pre>
</body>
</html>"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Uploading document...", total=None)
            
            # Upload document
            url = f"{self.base_url}/datastores/{self.datastore_id}/documents"
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(html_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Upload as multipart form data
                with open(tmp_file_path, 'rb') as f:
                    files = {'file': (f'{metadata.get("title", "document")}.html', f, 'text/html')}
                    
                    with httpx.Client(timeout=120.0) as client:
                        response = client.post(
                            url,
                            headers=self.headers,
                            files=files
                        )
                        response.raise_for_status()
                        result = response.json()
                
                document_id = result.get("document_id", result.get("id"))
                progress.update(task, description=f"[green]Upload successful![/green] Document ID: {document_id}")
                
                # Wait for ingestion if requested
                if wait_for_completion and document_id:
                    progress.update(task, description="Waiting for ingestion to complete...")
                    ingestion_status = self._wait_for_ingestion(document_id, progress, task)
                    
                    if ingestion_status == "completed":
                        progress.update(task, description="[green]Document fully ingested![/green]")
                    else:
                        progress.update(task, description=f"[yellow]Ingestion status: {ingestion_status}[/yellow]")
                
                return result
                
            except httpx.HTTPStatusError as e:
                console.print(f"[red]Upload failed:[/red] {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                console.print(f"[red]Upload error:[/red] {str(e)}")
                raise
            finally:
                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
    
    def _wait_for_ingestion(self, 
                           document_id: str, 
                           progress: Progress, 
                           task: int,
                           max_wait: int = 60) -> str:
        """
        Wait for document ingestion to complete.
        
        Args:
            document_id: The document ID to check
            progress: Progress bar instance
            task: Task ID for progress updates
            max_wait: Maximum seconds to wait
            
        Returns:
            Final ingestion status
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check document status
            status = self._check_document_status(document_id)
            
            if status in ["completed", "failed", "error"]:
                return status
            
            # Update progress with current status
            elapsed = int(time.time() - start_time)
            progress.update(task, description=f"Ingestion in progress... ({elapsed}s)")
            
            time.sleep(2)  # Poll every 2 seconds
        
        return "timeout"
    
    def _check_document_status(self, document_id: str) -> str:
        """
        Check the status of a document in Contextual.
        
        Args:
            document_id: The document ID to check
            
        Returns:
            Document status
        """
        url = f"{self.base_url}/datastores/{self.datastore_id}/documents/{document_id}"
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status", "unknown")
                
                return "checking"
        except:
            return "checking"
    
    def list_documents(self, limit: int = 10) -> Dict[str, Any]:
        """
        List documents in the datastore.
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            List of documents
        """
        url = f"{self.base_url}/datastores/{self.datastore_id}/documents"
        params = {"limit": limit}
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            console.print(f"[red]Failed to list documents:[/red] {str(e)}")
            return {"documents": [], "error": str(e)}